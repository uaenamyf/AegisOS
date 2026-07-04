# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: OpenAI API provider
"""OpenAI 兼容 API 的 Provider 实现。

调用 OpenAI Chat Completions 接口（或任何兼容该协议的端点，
如 Azure OpenAI、LiteLLM 代理），将 :class:`LLMRequest` 翻译为
HTTP 请求并解析返回结果。

环境变量：
- ``OPENAI_API_KEY``：API 密钥，未设置时 ``complete`` 返回错误响应。
"""
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class OpenAIProvider:
    """OpenAI 兼容 API 的 Provider。

    通过 ``httpx`` 同步调用 Chat Completions 接口，遵循
    :class:`ModelProvider` 协议。未配置 API Key 时会返回
    ``ok=False`` 的响应而非抛异常，便于在无 Key 环境降级。

    Attributes:
        _api_key: OpenAI API 密钥，从参数或 ``OPENAI_API_KEY`` 环境变量获取。
        _base_url: API 基础地址，默认官方 ``https://api.openai.com/v1``，
            可指向兼容端点。
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """初始化 OpenAI Provider。

        Args:
            api_key: API 密钥；为 ``None`` 时回退读取 ``OPENAI_API_KEY``
                环境变量。
            base_url: API 基础地址；为 ``None`` 时使用官方地址
                ``https://api.openai.com/v1``。
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or "https://api.openai.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        """调用 OpenAI Chat Completions 完成推理。

        将请求转为 OpenAI messages 格式（system + user），
        通过 HTTP POST 发送并解析 JSON 响应。任何异常都会被捕获并
        封装为 ``ok=False`` 的 :class:`LLMResponse`。

        Args:
            request: 包含 prompt、model_id、temperature 等的请求对象。

        Returns:
            成功时 ``ok=True`` 且 ``text`` 为模型输出；失败时
            ``ok=False`` 且 ``error`` 为异常信息。
        """
        # 未配置 API Key，直接返回降级错误，避免发起注定失败的请求
        if not self._api_key:
            return LLMResponse(
                text="",
                ok=False,
                error="OPENAI_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                # model_id 为空时使用默认模型 gpt-4o-mini
                "model": request.model_id or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            # 仅在显式提供停止序列时附加 stop 字段
            if request.stop:
                payload["stop"] = request.stop

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                # 非 2xx 状态码抛 HTTPStatusError
                resp.raise_for_status()
                data = resp.json()
                # choices[0].message.content 为首选生成结果
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "gpt-4o-mini",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            # 捕获网络/解析/状态码异常，统一封装为失败响应
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
