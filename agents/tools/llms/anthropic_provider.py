# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Anthropic API provider
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class AnthropicProvider:
    """Anthropic Claude API provider. Requires ANTHROPIC_API_KEY env var."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or "https://api.anthropic.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="", ok=False,
                error="ANTHROPIC_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": request.model_id or "claude-sonnet-4-20250514",
                "max_tokens": request.max_tokens,
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
                resp.raise_for_status()
                data = resp.json()
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
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
