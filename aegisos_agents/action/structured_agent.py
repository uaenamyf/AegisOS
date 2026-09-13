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
from pydantic import BaseModel

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
        self._instructions = instructions

        # Mock / 非 DeepSeek 路径：复用同一个 SDK Agent（共享 model）
        self._sdk_agent: Agent = self._build_agent(self._model)

    def _model_settings(self) -> "ModelSettings":
        """构造 ModelSettings（R19：默认关闭 ARK 深度思考以砍掉主要耗时）。

        走**完全相同**的 Agent 链路 A/B 实测（drill-7b797871 第 5 轮真实 critic
        prompt，2,039 tok 输入）：

            思考开  222.7s  issues=4  suggestion=432ch
            思考关   16.5s  issues=5  suggestion=497ch   ← 13.5x，质量相当

        耗时几乎全花在 reasoning token 上，与**输入大小无关**，且波动极大。
        故：
          * 本处**不设** max_tokens——实测封顶反而更慢（41.6s→100.9s，思考被
            拉长），且会截断 JSON 破坏结构化输出；
          * 默认关闭思考，可用 ``AEGIS_DISABLE_THINKING=false`` 切回（需要展示
            深度推理链时）。

        火山 ARK 通过 ``extra_body.thinking.type=disabled`` 传达，SDK 会将其
        透传给 ``chat.completions.create``（已验证 model_settings.extra_body 直达）。

        厂商限定（重要）：``thinking`` 是 ARK 专有字段，发给 OpenAI 官方或其他
        兼容端点可能被 400 拒绝，因此仅在 base_url 指向 ARK（volces）时注入；
        其他厂商保持原行为不变。
        """
        from agents import ModelSettings

        kw: dict[str, object] = {"temperature": self.TEMPERATURE}
        want_disable = os.getenv("AEGIS_DISABLE_THINKING", "true").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        base_url = (os.getenv("OPENAI_BASE_URL") or "").lower()
        is_ark = "volces" in base_url or "ark" in base_url
        if want_disable and is_ark:
            kw["extra_body"] = {"thinking": {"type": "disabled"}}
        return ModelSettings(**kw)

    def _build_agent(self, model) -> Agent:
        """用给定 model 构造 SDK Agent（复用 __init__ 的构造逻辑）。

        真实模式（``_plain_json``）每次调用用独立 model + client 时也会
        走到这里，因此 instructions 提前存到 ``self._instructions``。
        """
        from agents import AgentOutputSchema

        if self._plain_json:
            # DeepSeek：不设 output_type → SDK 不传 response_format，避免 400
            return Agent(
                name=self.__class__.__name__,
                instructions=self._instructions,
                model=model,
                model_settings=self._model_settings(),
            )
        # 构造 SDK Agent：instructions + output_type + model + temperature
        # 用 AgentOutputSchema(strict_json_schema=False) 包装 output_type，
        # 允许含 dict 字段（如 AlertModel.raw / IRPlannerResult.rollback /
        # ForensicsResult.timeline）的类型通过 SDK 的 JSON schema 校验。
        return Agent(
            name=self.__class__.__name__,
            instructions=self._instructions,
            output_type=AgentOutputSchema(self.OUTPUT_TYPE or str, strict_json_schema=False),
            model=model,
            model_settings=self._model_settings(),
        )

    def _fresh_model(self):
        """真实模式：构造独立的 Model + AsyncOpenAI client。

        共享的 AsyncOpenAI 客户端（SDKProvider 单例）跨线程/跨事件循环
        （``asyncio.run`` 每次调用新建循环）复用时，httpx 连接池可能挂起
        （实测：API 层第二次调用后第三次请求永不发起，curl 超时 000）。
        每次调用用独立 client 从根上消除该风险；client 由 GC 回收连接。
        """
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI

        return OpenAIChatCompletionsModel(
            model=str(self._model.model),
            openai_client=AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                # R19：与 SDKProvider 同样收紧超时/重试（旧版用库默认 600s x3）
                timeout=float(os.getenv("AEGIS_LLM_TIMEOUT", "180") or 180),
                max_retries=int(os.getenv("AEGIS_LLM_MAX_RETRIES", "1") or 1),
            ),
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

        # 事件循环已运行（FastAPI / uvicorn）→ 线程池隔离执行。
        # DeepSeek 真实链路：单 Agent 一次调用 30-60s，解析失败纠错重试后
        # 可达 120s+，默认 120s 超时会导致链路中途抛 RuntimeError → 500
        # （实测：real 模式跑约 2 分钟后 internal server error）。纯文本路径
        # 放宽到 600s 覆盖 3 次串行调用 + 重试；mock 模式不受影响（<1s）。
        if self._plain_json:
            timeout = max(timeout, 600.0)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._run_sync, prompt)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as err:
                raise RuntimeError(
                    f"StructuredAgent._run timed out after {timeout}s for prompt: {prompt[:200]}"
                ) from err

    def _run_sync(self, prompt: str) -> T:
        """同步执行结构化调用；DeepSeek 纯文本路径解析失败或空结果时带纠错提示重试。

        实测 DeepSeek 偶发返回空数组（如 ``{"assets": []}``），且输出随机性大
        （同一 prompt 时而完整时而空）。空输出 1s 即返回，重试成本极低，故最多
        尝试 3 次；每次重试都附引导提示（输出至少 1 个条目）。
        """
        max_attempts = 3 if self._plain_json else 1
        last_error: ValueError | None = None
        # 真实模式每次调用用独立 client，避免共享 AsyncOpenAI 跨线程/
        # 跨事件循环复用连接池时挂起（实测 API 层第三次调用永不发起）。
        agent = self._build_agent(self._fresh_model()) if self._plain_json else self._sdk_agent
        for attempt in range(max_attempts):
            result = Runner.run_sync(agent, prompt)
            try:
                output = self._finalize(result)  # type: ignore[no-any-return]
                # 空结果检测：DeepSeek 偶发返回全空数组，视为无效输出触发重试
                if self._plain_json and self._is_empty_result(output):
                    raise ValueError("model returned empty result (all list fields empty)")
                return output
            except ValueError as exc:
                last_error = exc
                if attempt == max_attempts - 1:
                    break
                prompt = (
                    f"{prompt}\n\n上次输出无效：{exc}\n"
                    "请重新输出，必须是严格合法的单个 JSON 对象，不要附加任何解释文字或代码块标记。"
                    "请基于给定信息完整作答，输出至少 1 个条目，不要返回空数组。"
                )
        raise last_error or ValueError("structured output failed")  # type: ignore[misc]

    def _is_empty_result(self, output) -> bool:
        """判断结构化输出是否为空结果（DeepSeek 偶发偷懒返回空数组）。

        规则：OUTPUT_TYPE 的所有 array 字段都为空 → 视为空结果。特例：含
        ``status`` 字段且非空（如 ExploitPlannerResult 的 ``no_vulnerabilities``）
        时视为明确的降级响应，不算空。

        Args:
            output: ``_finalize`` 的产物（OUTPUT_TYPE 实例或 dict）。

        Returns:
            True 表示空结果（应重试）。
        """
        if self.OUTPUT_TYPE is None:
            return False
        if isinstance(output, BaseModel):
            data = output.model_dump()
        elif isinstance(output, dict):
            data = output
        else:
            return False
        schema = self.OUTPUT_TYPE.model_json_schema()
        props = schema.get("properties", {})
        list_fields = [k for k, v in props.items() if v.get("type") == "array"]
        if not list_fields:
            return False
        if all(not data.get(k) for k in list_fields):
            # 明确降级响应（如 status="no_vulnerabilities"）不算空
            if "status" in props and data.get("status"):
                return False
            return True
        return False

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
