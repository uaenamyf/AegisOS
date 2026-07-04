# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: Mock LLM provider for testing
"""Mock LLM Provider：用于测试和离线开发的确定性桩件。

不发起任何网络请求，根据预设的响应表返回固定文本，
保证测试结果可复现。当未配置响应映射时，返回带 ``[mock]``
前缀的 prompt 片段作为占位输出。
"""
from __future__ import annotations

from .base import LLMRequest, LLMResponse


class MockProvider:
    """确定性 Mock Provider。

    用于单元测试和离线开发，避免依赖真实 API。根据 prompt
    在预设响应表中查找结果；未命中时使用 ``"default"`` 键或
    返回 prompt 前缀作为占位。

    Attributes:
        _responses: prompt 到响应文本的映射字典；可含 ``"default"``
            键作为兜底响应。
    """

    def __init__(self, responses: dict[str, str] | None = None):
        """初始化 Mock Provider。

        Args:
            responses: prompt 到期望响应文本的映射字典，可包含
                特殊键 ``"default"`` 作为未命中时的兜底响应；
                为 ``None`` 时使用空字典（所有请求走兜底逻辑）。
        """
        self._responses = responses or {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        """返回预设的确定性响应。

        查找顺序：精确匹配 prompt -> ``"default"`` 键 ->
        返回 ``"[mock] " + prompt 前 50 字符``。始终返回
        ``ok=True``，并附带模拟的 token 用量统计。

        Args:
            request: 包含 prompt 的请求对象。

        Returns:
            ``ok=True`` 的 :class:`LLMResponse`，``text`` 为预设
            或占位文本，``usage`` 为基于文本长度的近似统计。
        """
        # 1. 精确匹配 prompt
        text = self._responses.get(request.prompt)
        if text is None:
            # 2. 未命中则尝试 default 键，再无则截取 prompt 前 50 字符作占位
            text = self._responses.get("default", f"[mock] {request.prompt[:50]}")
        return LLMResponse(
            text=text,
            ok=True,
            model_id=request.model_id or "mock",
            # 模拟 token 用量：按 4 字符 ≈ 1 token 近似估算
            usage={"prompt_tokens": len(request.prompt) // 4, "completion_tokens": len(text) // 4},
        )
