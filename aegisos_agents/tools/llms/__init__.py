# date: 2026-07-04
# dev: myf
# changelog: R5.1/R5.2 清理——删除 ModelProvider/ModelRouter 导出，保留 LLMRequest/LLMResponse（Mock 内部契约）+ MockProvider + SDKProvider
"""LLM 工具包 —— Mock 与真实 API 双模式 Provider。

R5 清理后导出：
    - :class:`LLMRequest` / :class:`LLMResponse`：Mock 内部数据契约
    - :class:`MockProvider`：测试用确定性 Mock
    - :class:`SDKProvider`：真实 API 模式桥接 SDK
    - :func:`create_provider`：工厂函数

已删除（R5.1/R5.2）：
    - ``ModelProvider`` Protocol（SDK 有自己的 ``ModelProvider``）
    - ``ModelRouter``（无业务引用，模型选择由 ``Agent(model=...)`` 指定）
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
