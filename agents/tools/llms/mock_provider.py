# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Mock LLM provider for testing
from __future__ import annotations

from .base import LLMRequest, LLMResponse


class MockProvider:
    """Deterministic mock provider for tests and offline development."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        text = self._responses.get(request.prompt)
        if text is None:
            text = self._responses.get("default", f"[mock] {request.prompt[:50]}")
        return LLMResponse(
            text=text,
            ok=True,
            model_id=request.model_id or "mock",
            usage={"prompt_tokens": len(request.prompt) // 4, "completion_tokens": len(text) // 4},
        )
