# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 多模型路由器
from __future__ import annotations

from .base import LLMRequest, LLMResponse, ModelProvider


class ModelRouter:
    """Routes LLM requests to the appropriate provider.

    Provider selection logic:
    1. If request.model_id matches a known model prefix (gpt-* -> openai,
       claude-* -> anthropic, local/* -> local), route to that provider.
    2. Otherwise, use default_provider.
    3. complete_with_model() uses scheduler Model.tier -> provider mapping.
    """

    MODEL_PREFIX_MAP = {
        "gpt": "openai",
        "o1": "openai",
        "o3": "openai",
        "claude": "anthropic",
        "local": "local",
        "qwen": "local",
        "deepseek": "local",
        "llama": "local",
        "mock": "mock",
    }

    TIER_PROVIDER_MAP = {
        "edge": "edge",
        "cloud": "cloud",
    }

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        default_provider: str = "mock",
    ):
        self._providers = providers
        self._default = default_provider

    def complete(self, request: LLMRequest) -> LLMResponse:
        provider_name = self._resolve_provider_by_model(request.model_id)
        provider = self._providers.get(provider_name)
        if provider is None:
            provider = self._providers.get(self._default)
        if provider is None:
            return LLMResponse(
                text="",
                ok=False,
                error=f"No provider available for model '{request.model_id}'",
            )
        return provider.complete(request)

    def complete_with_model(
        self,
        request: LLMRequest,
        model: Model,
    ) -> LLMResponse:
        provider_name = self.TIER_PROVIDER_MAP.get(model.tier, self._default)
        provider = self._providers.get(provider_name, self._providers.get(self._default))
        if provider is None:
            return LLMResponse(
                text="",
                ok=False,
                error=f"No provider for tier '{model.tier}'",
            )
        req = LLMRequest(
            prompt=request.prompt,
            model_id=model.model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            stop=request.stop,
        )
        return provider.complete(req)

    def _resolve_provider_by_model(self, model_id: str) -> str:
        if not model_id:
            return self._default
        lower = model_id.lower()
        for prefix, provider_name in self.MODEL_PREFIX_MAP.items():
            if lower.startswith(prefix):
                return provider_name
        return self._default
