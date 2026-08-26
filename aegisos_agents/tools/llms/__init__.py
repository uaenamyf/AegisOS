# date: 2026-07-04
# dev: myf
"""LLM 工具包 —— Mock 与真实 API 双模式 Provider。

导出：
    - :class:`LLMRequest` / :class:`LLMResponse`：Mock 内部数据契约
    - :class:`MockProvider`：测试用确定性 Mock
    - :class:`SDKProvider`：真实 API 模式桥接 SDK
    - :func:`create_provider`：工厂函数
"""

from .base import LLMRequest, LLMResponse
from .mock_provider import MockProvider
from .sdk_provider import SDKProvider, create_provider

__all__ = [
    "LLMRequest",
    "LLMResponse",
    "MockProvider",
    "SDKProvider",
    "create_provider",
]
