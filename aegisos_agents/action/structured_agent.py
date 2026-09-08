# date: 2026-07-06
# dev: myf
"""结构化 Agent 基类 —— 封装 openai-agents SDK 的 Agent + Runner + output_type。

本模块提供 :class:`StructuredAgent`，将 SDK 的 ``Agent(output_type=Pydantic)``
+ ``Runner.run_sync()`` 封装为同步调用接口，供 11 个攻防 Agent 复用，彻底删除
各 Agent 中的 ``json.loads + try/except`` 重复代码。

双模式工作原理：
    - Mock 模式：注入 :class:`MockSDKModel`（包装项目 MockProvider），SDK Runner
      走预置 JSON 响应表，``output_type`` 解析为 Pydantic 对象返回。
    - 真实 API 模式：注入 SDK ``OpenAIChatCompletionsModel``（指向火山引擎 ARK /
      OpenAI），SDK Runner 调真实 LLM，``output_type`` 自动结构化。

使用方式（以 ReconAgent 为例）::

    class ReconAgent(StructuredAgent[ReconResult]):
        SYSTEM_PROMPT = "You are a recon agent..."
        def scan(self, target_range: str) -> list[Asset]:
            result = self._run(f"Scan target range: {target_range}")
            return [Asset(**a) for a in result.assets]

收益：
    - 每个 Agent 从 ~80 行降到 ~30 行（删除 parse + fallback 段）
    - 结构化输出由 SDK 保证（Pydantic 验证 + 自动重试）
    - Mock 与真实 API 走同一代码路径（测试与生产一致）
"""

from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Generic, TypeVar

from agents import Agent, Model, ModelProvider, Runner

from aegisos_agents.tools.llms.mock_provider import MockProvider
from aegisos_agents.tools.llms.mock_sdk_model import MockSDKModel

T = TypeVar("T")  # output_type 的 Pydantic 类型


class StructuredAgent(Generic[T]):
    """结构化 Agent 基类 —— 封装 SDK Agent + Runner，提供同步结构化输出。

    子类需定义 ``SYSTEM_PROMPT`` 和 ``OUTPUT_TYPE``，通过 :meth:`_run` 发起
    结构化 LLM 调用，返回 ``OUTPUT_TYPE`` 类型的实例。

    Attributes:
        _sdk_agent: SDK ``Agent`` 实例（含 instructions + output_type）。
        _model: SDK ``Model`` 实例（Mock 或真实 API）。
    """

    SYSTEM_PROMPT: str = ""
    OUTPUT_TYPE: type[T] | None = None
    TEMPERATURE: float = 0.3

    def __init__(self, model: Model | None = None, mock: MockProvider | None = None) -> None:
        """初始化结构化 Agent。

        Args:
            model: SDK ``Model`` 实例（真实 API 模式）；为 ``None`` 时用 mock。
            mock: :class:`MockProvider` 实例（Mock 模式）；``model`` 为 None 时使用。
        """
        if model is None:
            # Mock 模式：用 MockSDKModel 包装项目 MockProvider
            self._model: Model = MockSDKModel(mock)
        else:
            self._model = model

        # DeepSeek 检测：base_url 含 deepseek 且非 Mock 模型时，SDK 的
        # json_schema response_format 不被 DeepSeek 支持 → 纯文本输出 + 本地解析。
        base_url = os.getenv("OPENAI_BASE_URL", "") or ""
        host = base_url.split("//")[-1].split("/")[0] if base_url else ""
        self._plain_json = (
            self._model.__class__.__name__ != "MockSDKModel" and "deepseek" in host
        )

        # DeepSeek 平台限制：① response_format=json_object 时 prompt 必须含
        # "json" 字样（否则 400）；② 仅支持 json_object，不支持 SDK 硬编码的
        # json_schema 类型。统一追加 JSON 提示（OpenAI/ARK 无此限制，追加
        # 无害）；纯文本模式下把输出结构写入提示，引导模型按 schema 输出。
        json_hint = (
            "\n\n输出必须为合法 JSON 对象，字段与类型严格遵循既定结构。"
            if self.SYSTEM_PROMPT
            else "Always respond in valid JSON."
        )
        if self._plain_json and self.OUTPUT_TYPE is not None:
            schema = self.OUTPUT_TYPE.model_json_schema()
            props = schema.get("properties", {})
            if props:
                parts = []
                for name, meta in props.items():
                    t = meta.get("type", "any")
                    desc = meta.get("description", "")
                    parts.append(f'"{name}": {t}' + (f" ({desc})" if desc else ""))
                json_hint += " 必须仅包含以下字段: " + ", ".join(parts) + "。"
        instructions = f"{self.SYSTEM_PROMPT}{json_hint}"

        from agents import AgentOutputSchema, ModelSettings

        # OUTPUT_TYPE 为 None 时用 str 兜底（SDK 要求非 None）
        output_type = self.OUTPUT_TYPE or str
        if self._plain_json:
            # DeepSeek：不设 output_type → SDK 不传 response_format，避免 400
            self._sdk_agent: Agent = Agent(
                name=self.__class__.__name__,
                instructions=instructions,
                model=self._model,
                model_settings=ModelSettings(temperature=self.TEMPERATURE),
            )
        else:
            # 构造 SDK Agent：instructions + output_type + model + temperature
            # 用 AgentOutputSchema(strict_json_schema=False) 包装 output_type，
            # 允许含 dict 字段（如 AlertModel.raw / IRPlannerResult.rollback /
            # ForensicsResult.timeline）的类型通过 SDK 的 JSON schema 校验。
            self._sdk_agent: Agent = Agent(
                name=self.__class__.__name__,
                instructions=instructions,
                output_type=AgentOutputSchema(output_type, strict_json_schema=False),
                model=self._model,
                model_settings=ModelSettings(temperature=self.TEMPERATURE),
            )

    def _run(self, prompt: str, timeout: float = 120.0) -> T:
        """执行一次结构化 LLM 调用，返回 ``OUTPUT_TYPE`` 实例。

        封装 ``Runner.run_sync``，SDK 自动处理：
            - 调用 ``Model.get_response``
            - 用 ``output_type``（Pydantic）解析响应
            - 失败时自动重试（可配置）

        当检测到运行中的事件循环（如 FastAPI 异步上下文）时，
        自动将 ``Runner.run_sync`` 投递到线程池执行，避免
        ``asyncio.run()`` 嵌套冲突。

        Args:
            prompt: 用户 prompt 文本。
            timeout: 线程池模式的超时秒数（仅在线程池模式下生效）。

        Returns:
            ``OUTPUT_TYPE`` 类型的结构化输出实例。

        Raises:
            RuntimeError: 在线程池模式下等待超时时抛出。
        """
        try:
            asyncio.get_running_loop()  # 探测有无运行中的事件循环
        except RuntimeError:
            # 无运行中的事件循环 → 直接同步执行
            return self._run_sync(prompt)

        # 事件循环已运行（FastAPI / uvicorn）→ 线程池隔离执行
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._run_sync, prompt)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as err:
                raise RuntimeError(
                    f"StructuredAgent._run timed out after {timeout}s for prompt: {prompt[:200]}"
                ) from err

    def _run_sync(self, prompt: str) -> T:
        """同步执行结构化调用；DeepSeek 纯文本路径解析失败时带纠错提示重试一次。"""
        max_attempts = 2 if self._plain_json else 1
        last_error: ValueError | None = None
        for attempt in range(max_attempts):
            result = Runner.run_sync(self._sdk_agent, prompt)
            try:
                return self._finalize(result)  # type: ignore[no-any-return]
            except ValueError as exc:
                last_error = exc
                if attempt == max_attempts - 1:
                    break
                prompt = (
                    f"{prompt}\n\n上次输出无效：{exc}\n"
                    "请重新输出，必须是严格合法的单个 JSON 对象，不要附加任何解释文字或代码块标记。"
                )
        raise last_error or ValueError("structured output failed")  # type: ignore[misc]

    def _finalize(self, result) -> T:
        """把 SDK 运行结果转换为 ``OUTPUT_TYPE`` 实例。

        普通路径：SDK 已按 ``output_type`` 解析，直接返回 ``final_output``。
        DeepSeek 路径（``_plain_json``）：SDK 返回纯文本 JSON，本地解析 +
        Pydantic 校验（剥离可能的 markdown 代码块包裹）。

        Args:
            result: ``Runner.run_sync`` 的返回结果。

        Returns:
            ``OUTPUT_TYPE`` 类型的结构化输出实例。

        Raises:
            ValueError: DeepSeek 返回非 JSON 文本且无法恢复时。
        """
        if not self._plain_json:
            return result.final_output  # type: ignore[no-any-return]
        text = result.final_output
        data = None
        if isinstance(text, str):
            candidates: list[str] = []
            # 候选 1：全文
            candidates.append(text)
            # 候选 2：第一个 { 到最后一个 }（模型常在 JSON 前后夹带解释文字）
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                candidates.append(text[start : end + 1])
            # 候选 3：```json ... ``` 代码块内
            fence = text.find("```")
            if fence != -1:
                inner = text[fence + 3 :]
                end_f = inner.rfind("```")
                if end_f != -1:
                    inner = inner[:end_f].lstrip()
                    if inner.startswith("json"):
                        inner = inner[4:].lstrip()
                    candidates.append(inner)
            for cand in candidates:
                try:
                    data = json.loads(cand)
                    if isinstance(data, dict):
                        break
                except (json.JSONDecodeError, TypeError):
                    continue
        if not isinstance(data, dict):
            raise ValueError(f"model returned non-JSON output: {text[:200]!r}")
        if self.OUTPUT_TYPE is None:
            return data  # type: ignore[no-any-return]
        return self.OUTPUT_TYPE.model_validate(data)

    async def _run_streamed(self, prompt: str):
        """异步流式执行，逐事件 yield SDK ``RunResultStreaming.stream_events()``。

        R5.3：供后端 SSE router 实时推送 Agent 思考过程到前端。

        用 SDK ``Runner.run_streamed()`` 启动流式执行，逐事件 yield。
        事件类型包括：
            - ``AgentUpdatedStreamEvent``：Agent 切换（handoff）
            - ``RunItemStreamEvent``：产出项（消息/工具调用/输出）
            - ``RawResponsesStreamEvent``：原始模型响应

        Args:
            prompt: 用户 prompt 文本。

        Yields:
            SDK 流式事件对象（由调用方决定如何序列化为 SSE 帧）。
        """
        result = Runner.run_streamed(self._sdk_agent, prompt)
        async for event in result.stream_events():
            yield event


def create_sdk_model_provider(
    mock: MockProvider | None = None,
) -> ModelProvider:
    """创建 SDK ``ModelProvider`` —— 根据运行模式返回 Mock 或真实 API Provider。

    供 ``RunConfig(model_provider=...)`` 使用，让 SDK ``Runner`` 按模式选择 Model。

    Args:
        mock: Mock 模式下的预置响应表。

    Returns:
        :class:`ModelProvider` 实例。
    """

    class _Provider(ModelProvider):
        def __init__(self, mock_provider: MockProvider | None) -> None:
            self._mock = mock_provider

        def get_model(self, model_name: str | None) -> Model:
            if self._mock is not None:
                return MockSDKModel(self._mock)
            # 真实 API 模式：从 SDKProvider 获取
            from aegisos_agents.tools.llms.sdk_provider import SDKProvider

            sdk = SDKProvider(model_id=model_name or "")
            return sdk.get_sdk_model(model_name)

    return _Provider(mock)
