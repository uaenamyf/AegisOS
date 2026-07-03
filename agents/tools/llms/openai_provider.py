# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: OpenAI API provider
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class OpenAIProvider:
    """OpenAI-compatible API provider. Requires OPENAI_API_KEY env var."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or "https://api.openai.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="", ok=False,
                error="OPENAI_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": request.model_id or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            if request.stop:
                payload["stop"] = request.stop

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "gpt-4o-mini",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
