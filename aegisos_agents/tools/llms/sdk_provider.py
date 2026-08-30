# date: 2026-07-06
# dev: myf
"""SDK Provider 适配器 —— 桥接项目 MockProvider 与 openai-agents SDK。

本模块根据 ``AEGIS_USE_MOCK`` 环境变量在两种模式间切换：
    - Mock 模式（``AEGIS_USE_MOCK=true``）：使用 :class:`MockProvider`，无需 API Key，
      返回预置响应。用于评委本地演示、CI、单元测试。
    - 真实 API 模式（``AEGIS_USE_MOCK=false``）：通过 SDK 调用 OpenAI 兼容端点
      （火山引擎 ARK / OpenAI 原生），使用 ``ChatCompletions`` API。

火山引擎适配：
    - 火山引擎 ARK 仅支持 Chat Completions API（不支持 Responses API）
    - 通过 ``OPENAI_BASE_URL`` 指向 ARK 端点
    - 通过 ``OPENAI_DEFAULT_MODEL`` 指定推理接入点 endpoint ID

与现有架构的关系：
    - 保留 :class:`MockProvider`（测试依赖，不删除）
    - 保留 :class:`LLMRequest` / :class:`LLMResponse`（Mock 内部契约不变）
    - 本适配器仅通过 :meth:`SDKProvider.get_sdk_model` 提供真实 API 的 SDK ``Model``，
      不再提供旧 ``complete()`` 同步调用（已由 SDK ``Runner.run_sync`` 替代）
"""

from __future__ import annotations

import os

from agents import set_default_openai_api, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .mock_provider import MockProvider


def _is_mock_mode() -> bool:
    """判断是否启用 Mock 模式。

    读取 ``AEGIS_USE_MOCK`` 环境变量，``true``（不区分大小写）时启用。
    无 ``OPENAI_API_KEY`` 时也自动降级为 Mock 模式（避免运行时崩溃）。

    Returns:
        True 表示使用 Mock Provider；False 表示使用真实 API。
    """
    flag = os.getenv("AEGIS_USE_MOCK", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    # 无 API Key 时自动降级 Mock，避免评委本地启动崩溃
    return not os.getenv("OPENAI_API_KEY")


class SDKProvider:
    """SDK 桥接 Provider -- 真实 API 模式下提供 SDK ``Model`` 供 Agent 使用。

    在真实 API 模式下，创建 ``AsyncOpenAI`` 客户端并配置 SDK 全局默认 API 为
    ``chat_completions``（火山引擎 ARK 不支持 Responses API），通过
    :meth:`get_sdk_model` 返回 :class:`OpenAIChatCompletionsModel` 供 SDK
    ``Agent(model=...)`` 直接使用。

    火山引擎 ARK 兼容：通过 ``OPENAI_BASE_URL`` + ``OPENAI_API_KEY`` 环境变量
    自动指向 ARK 端点，使用 Chat Completions API。

    R6.1 清理：删除了旧 ``complete()`` 同步调用方法（已被 SDK
    ``Runner.run_sync`` + ``output_type`` 结构化输出替代，无业务调用方）。

    Attributes:
        _client: OpenAI 异步客户端（真实模式）；Mock 模式下为 None。
        _mock: Mock Provider 实例（Mock 模式下使用）。
        _model: 默认模型 ID（来自 ``OPENAI_DEFAULT_MODEL`` 或代码默认值）。
    """

    def __init__(self, model_id: str = "") -> None:
        """初始化 SDK Provider。

        根据 ``AEGIS_USE_MOCK`` 与 ``OPENAI_API_KEY`` 决定运行模式。
        真实模式下创建 ``AsyncOpenAI`` 客户端并配置 SDK 全局默认 API 为
        ``chat_completions``（火山引擎 ARK 不支持 Responses API）。

        Args:
            model_id: 默认模型 ID；为空时从 ``OPENAI_DEFAULT_MODEL`` 环境变量读取。
        """
        self._mock: MockProvider | None = None
        self._client: AsyncOpenAI | None = None
        self._model = model_id or os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

        if _is_mock_mode():
            # Mock 模式：不创建网络客户端
            self._mock = MockProvider()
            return

        # 真实 API 模式：创建 OpenAI 兼容客户端（火山引擎 ARK / OpenAI 原生）
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL") or None  # None 时用 OpenAI 默认
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # 火山引擎 ARK 仅支持 Chat Completions，强制切换（OpenAI 原生也兼容此 API）
        set_default_openai_api("chat_completions")

        # 禁用 trace 上传（火山引擎无 OpenAI 的 tracing 端点，否则 401）
        if os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "").lower() in ("1", "true"):
            set_tracing_disabled(disabled=True)

    @property
    def is_mock(self) -> bool:
        """当前是否为 Mock 模式。"""
        return self._mock is not None

    def get_sdk_model(self, model_name: str | None = None) -> OpenAIChatCompletionsModel:
        """获取 SDK ``Model`` 实例，供 SDK ``Agent(model=...)`` 直接使用。

        用于 S2/S3 阶段将 Agent 迁移到 SDK ``Agent`` 类时，注入 SDK 原生 Model。
        Mock 模式下抛出 ``RuntimeError``（SDK Agent 不应在 Mock 模式下用真实 Model）。

        Args:
            model_name: 模型名称；为空时用初始化时的默认模型。

        Returns:
            :class:`OpenAIChatCompletionsModel` 实例。

        Raises:
            RuntimeError: Mock 模式下调用此方法。
        """
        if self._mock is not None:
            raise RuntimeError(
                "Mock 模式不支持获取 SDK Model；请用 AEGIS_USE_MOCK=false 切换真实 API"
            )
        assert self._client is not None
        return OpenAIChatCompletionsModel(
            model=model_name or self._model,
            openai_client=self._client,
        )


def create_provider(model_id: str = "") -> SDKProvider | MockProvider:
    """工厂函数 —— 根据运行模式创建合适的 Provider。

    被 ``backend/core/composition.py`` 组合根调用，注入到 11 个 Agent。
    Mock 模式返回 :class:`MockProvider`（保持与现有测试完全兼容），
    真实模式返回 :class:`SDKProvider`。

    Args:
        model_id: 默认模型 ID。

    Returns:
        :class:`MockProvider`（Mock 模式）或 :class:`SDKProvider`（真实模式）。
    """
    if _is_mock_mode():
        # Mock 模式返回原生 MockProvider，保持测试兼容
        # （cyber_provider.py 的 _CyberMockProvider 会包装它）
        return MockProvider()
    return SDKProvider(model_id=model_id)
