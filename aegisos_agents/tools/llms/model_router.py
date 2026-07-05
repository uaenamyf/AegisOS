# date: 2026-07-04
# dev: myf
# changelog: 多模型路由器
"""多模型路由器：根据模型 ID 或调度层级选择对应 Provider。

本模块提供 :class:`ModelRouter`，负责把一次 :class:`LLMRequest`
分发到合适的 Provider（OpenAI / Anthropic / Local / Mock 等）。

两种路由方式：
1. ``complete()``：根据 ``request.model_id`` 的前缀匹配 Provider
2. ``complete_with_model()``：根据调度器返回的 ``Model.tier`` 匹配 Provider
"""

from __future__ import annotations

from .base import LLMRequest, LLMResponse, ModelProvider


class ModelRouter:
    """将 LLM 请求路由到合适 Provider 的中央调度器。

    Provider 选择逻辑：
    1. 若 ``request.model_id`` 匹配已知前缀（gpt-* -> openai,
       claude-* -> anthropic, local/* -> local），路由到对应 Provider。
    2. 否则使用 ``default_provider``。
    3. ``complete_with_model()`` 使用调度器 ``Model.tier`` -> Provider 映射。

    Attributes:
        MODEL_PREFIX_MAP: 模型 ID 前缀到 Provider 名的静态映射，
            如 ``{"gpt": "openai", "claude": "anthropic", ...}``。
        TIER_PROVIDER_MAP: 调度层级（device/edge/cloud）到 Provider 名的映射。
        _providers: Provider 名到 Provider 实例的字典，构造时注入。
        _default: 兜底 Provider 名，当路由失败时使用。
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

    # 三层 tier → provider 映射
    # device: 端侧（PC/手机/IoT）— 本地规则引擎/嵌入式小模型
    # edge:   边侧（边缘网关/机架服务器）— 中型本地模型 (Ollama/vLLM)
    # cloud:  云侧（GPU 集群/厂家 API）— OpenAI/Anthropic/大模型
    TIER_PROVIDER_MAP = {
        "device": "local",
        "edge": "local",
        "cloud": "cloud",
    }

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        default_provider: str = "mock",
    ):
        """初始化路由器。

        Args:
            providers: Provider 名到 Provider 实例的映射字典，
                如 ``{"openai": OpenAIProvider(), "mock": MockProvider()}``。
            default_provider: 兜底 Provider 名，当模型 ID 无法匹配或
                层级映射缺失时使用，默认为 ``"mock"``。
        """
        self._providers = providers
        self._default = default_provider

    def complete(self, request: LLMRequest) -> LLMResponse:
        """根据模型 ID 前缀路由请求并执行推理。

        路由失败（包括兜底 Provider 也缺失）时返回 ``ok=False`` 的响应，
        不抛出异常。

        Args:
            request: 包含 prompt 和 model_id 的请求对象。

        Returns:
            目标 Provider 的推理结果；若无任何可用 Provider，
            返回 ``ok=False`` 的 :class:`LLMResponse`。
        """
        # 1. 尝试按 model_id 前缀匹配 Provider
        provider_name = self._resolve_provider_by_model(request.model_id)
        provider = self._providers.get(provider_name)
        # 2. 匹配不到则回退到默认 Provider
        if provider is None:
            provider = self._providers.get(self._default)
        # 3. 连默认 Provider 都没有，返回错误响应而非抛异常
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
        """根据调度器选定的 ``Model.tier`` 路由请求。

        与 :meth:`complete` 不同，此方法用模型所属的调度层级
        （device/edge/cloud）决定 Provider，并会覆盖请求中的
        ``model_id`` 为调度器指定的模型。

        Args:
            request: 原始请求，仅取其 prompt、温度等参数。
            model: 调度器返回的目标模型，其 ``tier`` 决定 Provider，
                其 ``model_id`` 覆盖请求中的模型。

        Returns:
            对应层级 Provider 的推理结果；若无可用 Provider，
            返回 ``ok=False`` 的 :class:`LLMResponse`。
        """
        # 按 tier 查 Provider，缺失则回退默认
        provider_name = self.TIER_PROVIDER_MAP.get(model.tier, self._default)
        provider = self._providers.get(provider_name, self._providers.get(self._default))
        if provider is None:
            return LLMResponse(
                text="",
                ok=False,
                error=f"No provider for tier '{model.tier}'",
            )
        # 用调度器指定的 model_id 覆盖请求，构造新请求
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
        """根据模型 ID 前缀解析 Provider 名。

        Args:
            model_id: 模型标识符，如 ``"gpt-4o-mini"``。

        Returns:
            匹配到的 Provider 名（如 ``"openai"``）；无匹配或
            ``model_id`` 为空时返回 ``self._default``。
        """
        if not model_id:
            return self._default
        # 大小写不敏感地比较前缀
        lower = model_id.lower()
        for prefix, provider_name in self.MODEL_PREFIX_MAP.items():
            if lower.startswith(prefix):
                return provider_name
        return self._default
