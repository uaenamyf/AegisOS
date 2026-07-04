# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: Anthropic API provider
"""Anthropic Claude API 的 Provider 实现。

调用 Anthropic Messages 接口，将 :class:`LLMRequest` 翻译为
Claude 专用的请求格式（system 字段独立于 messages）并解析返回结果。

环境变量：
- ``ANTHROPIC_API_KEY``：API 密钥，未设置时 ``complete`` 返回错误响应。
"""
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class AnthropicProvider:
    """Anthropic Claude API 的 Provider。

    通过 ``httpx`` 同步调用 Messages 接口，遵循 :class:`ModelProvider` 协议。
    与 OpenAI 不同，Claude 的 system 提示词是独立字段而非 messages 中的一项。

    Attributes:
        _api_key: Anthropic API 密钥，从参数或 ``ANTHROPIC_API_KEY`` 环境变量获取。
        _base_url: API 基础地址，默认官方 ``https://api.anthropic.com/v1``。
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """初始化 Anthropic Provider。

        Args:
            api_key: API 密钥；为 ``None`` 时回退读取 ``ANTHROPIC_API_KEY``
                环境变量。
            base_url: API 基础地址；为 ``None`` 时使用官方地址
                ``https://api.anthropic.com/v1``。
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or "https://api.anthropic.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        """调用 Anthropic Messages 接口完成推理。

        将请求转为 Claude 格式（system 字段 + messages 列表），
        通过 HTTP POST 发送并解析 JSON 响应。Anthropic 返回的
        ``content`` 是一个 block 数组，本方法会拼接其中所有
        ``type=="text"`` 的 block。

        Args:
            request: 包含 prompt、model_id、temperature 等的请求对象。

        Returns:
            成功时 ``ok=True`` 且 ``text`` 为模型输出（多个 text block
            已拼接）；失败时 ``ok=False`` 且 ``error`` 为异常信息。
        """
        # 未配置 API Key，直接返回降级错误
        if not self._api_key:
            return LLMResponse(
                text="",
                ok=False,
                error="ANTHROPIC_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                # Anthropic 用 x-api-key 头而非 Bearer token
                "x-api-key": self._api_key,
                # anthropic-version 头指定 API 版本日期
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                # model_id 为空时使用默认模型 claude-sonnet-4-20250514
                "model": request.model_id or "claude-sonnet-4-20250514",
                "max_tokens": request.max_tokens,
                # system 是独立字段，为空时给一个默认提示
                "system": request.system_prompt or "You are a helpful assistant.",
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
            }

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )
                # 非 2xx 状态码抛 HTTPStatusError
                resp.raise_for_status()
                data = resp.json()
                # Anthropic 返回 content 为 block 数组，需拼接所有 text block
                text_parts = [
                    block["text"]
                    for block in data.get("content", [])
                    if block.get("type") == "text"
                ]
                return LLMResponse(
                    text="".join(text_parts),
                    ok=True,
                    model_id=request.model_id or "claude-sonnet-4-20250514",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            # 捕获网络/解析/状态码异常，统一封装为失败响应
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
