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
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Generic, TypeVar

from aegisos_agents.tools.llms.mock_provider import MockProvider
from aegisos_agents.tools.llms.mock_sdk_model import MockSDKModel
from agents import Agent, Model, ModelProvider, Runner

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

        # 构造 SDK Agent：instructions + output_type + model + temperature
        # 用 AgentOutputSchema(strict_json_schema=False) 包装 output_type，
        # 允许含 dict 字段（如 AlertModel.raw / IRPlannerResult.rollback /
        # ForensicsResult.timeline）的类型通过 SDK 的 JSON schema 校验。
        from agents import AgentOutputSchema, ModelSettings

        # OUTPUT_TYPE 为 None 时用 str 兜底（SDK 要求非 None）
        output_type = self.OUTPUT_TYPE or str
        self._sdk_agent: Agent = Agent(
            name=self.__class__.__name__,
            instructions=self.SYSTEM_PROMPT,
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
            result = Runner.run_sync(self._sdk_agent, prompt)
            return result.final_output  # type: ignore[no-any-return]

        # 事件循环已运行（FastAPI / uvicorn）→ 线程池隔离执行
        def _sync_call() -> T:
            result = Runner.run_sync(self._sdk_agent, prompt)
            return result.final_output  # type: ignore[no-any-return]

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_sync_call)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as err:
                raise RuntimeError(
                    f"StructuredAgent._run timed out after {timeout}s for prompt: {prompt[:200]}"
                ) from err

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
