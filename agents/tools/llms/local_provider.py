# date: 2026-07-04
# dev: myf
# changelog: Local model provider (Ollama / vLLM / LM Studio compatible)
"""本地模型 Provider 实现（兼容 Ollama / vLLM / LM Studio）。

调用本地运行的 OpenAI 兼容端点（如 Ollama 的 ``/v1/chat/completions``、
vLLM、LM Studio），无需 API Key，适合端侧/边侧部署。

环境变量：
- ``LOCAL_LLM_BASE_URL``：本地服务地址，默认
  ``http://localhost:11434/v1``（Ollama 默认端口）。
"""
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class LocalProvider:
    """本地 LLM Provider。

    兼容 Ollama / vLLM / LM Studio 等 OpenAI 兼容端点。
    不需要 API Key，超时设为 120 秒（本地模型通常比云端慢）。

    Attributes:
        _base_url: 本地服务基础地址，从参数或 ``LOCAL_LLM_BASE_URL``
            环境变量获取，默认 ``http://localhost:11434/v1``。
    """

    def __init__(self, base_url: str | None = None):
        """初始化本地 Provider。

        Args:
            base_url: 本地服务基础地址；为 ``None`` 时回退读取
                ``LOCAL_LLM_BASE_URL`` 环境变量，再无则使用默认值
                ``http://localhost:11434/v1``。
        """
        self._base_url = base_url or os.environ.get(
            "LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        """调用本地 OpenAI 兼容端点完成推理。

        复用 OpenAI 的 ``/chat/completions`` 协议，但不附带
        Authorization 头（本地服务通常无需鉴权）。任何异常都会被
        捕获并封装为 ``ok=False`` 的 :class:`LLMResponse`。

        Args:
            request: 包含 prompt、model_id、temperature 等的请求对象。

        Returns:
            成功时 ``ok=True`` 且 ``text`` 为模型输出；失败时
            ``ok=False`` 且 ``error`` 为异常信息。
        """
        try:
            import httpx

            payload = {
                # model_id 为空时使用默认本地模型 qwen2.5:7b
                "model": request.model_id or "qwen2.5:7b",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            # 本地模型推理较慢，超时设为 120 秒（云端通常 60 秒）
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                )
                # 非 2xx 状态码抛 HTTPStatusError
                resp.raise_for_status()
                data = resp.json()
                # choices[0].message.content 为首选生成结果
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "local",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            # 捕获网络/解析/状态码异常，统一封装为失败响应
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
