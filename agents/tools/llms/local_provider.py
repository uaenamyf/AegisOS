# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Local model provider (Ollama / vLLM / LM Studio compatible)
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class LocalProvider:
    """Local LLM provider. Compatible with Ollama / vLLM / LM Studio OpenAI-compatible endpoints."""

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or os.environ.get(
            "LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            import httpx

            payload = {
                "model": request.model_id or "qwen2.5:7b",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "local",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
