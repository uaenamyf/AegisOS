# date: 2026-07-06
# dev: myf
"""SDK Provider 适配器 —— 桥接项目 MockProvider 与 openai-agents SDK。

本模块根据 ``AEGIS_USE_MOCK`` 环境变量在两种模式间切换：
    - Mock 模式（``AEGIS_USE_MOCK=true``）：使用 :class:`MockProvider`，无需 API Key，
      返回预置响应。用于评委本地演示、CI、单元测试。
    - 真实 API 模式（``AEGIS_USE_MOCK=false``）：通过 SDK 调用 OpenAI 兼容端点
      （火山引擎 ARK / OpenAI 原生），使用 ``ChatCompletions`` API。

火山引擎适配：
    - 火山引擎 ARK 仅支持 Chat Completions API（不支持 Responses API）
    - 通过 ``OPENAI_BASE_URL`` 指向 ARK 端点
    - 通过 ``OPENAI_DEFAULT_MODEL`` 指定推理接入点 endpoint ID

与现有架构的关系：
    - 保留 :class:`MockProvider`（测试依赖，不删除）
    - 保留 :class:`LLMRequest` / :class:`LLMResponse`（Mock 内部契约不变）
    - 本适配器仅通过 :meth:`SDKProvider.get_sdk_model` 提供真实 API 的 SDK ``Model``，
      不再提供旧 ``complete()`` 同步调用（已由 SDK ``Runner.run_sync`` 替代）
"""

from __future__ import annotations

import os
import time
from typing import Any

from agents import set_default_openai_api, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .mock_provider import MockProvider


def _is_mock_mode() -> bool:
    """判断是否启用 Mock 模式。

    读取 ``AEGIS_USE_MOCK`` 环境变量，``true``（不区分大小写）时启用。
    无 ``OPENAI_API_KEY`` 时也自动降级为 Mock 模式（避免运行时崩溃）。

    Returns:
        True 表示使用 Mock Provider；False 表示使用真实 API。
    """
    flag = os.getenv("AEGIS_USE_MOCK", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    # 无 API Key 时自动降级 Mock，避免评委本地启动崩溃
    return not os.getenv("OPENAI_API_KEY")


class RoutedSDKModel(OpenAIChatCompletionsModel):
    """端边云路由代理 Model —— C-5 自适应调度的执行时闭环（R20）。

    实现与 SDK ``Model`` 协议兼容的 ``get_response``，每次真实推理请求
    到达时才做路由决策：

        1. 从 NodeRegistry 取当前在线节点快照（探活状态驱动候选集）；
        2. 用 engine.scheduler.schedule() 按任务特征（latency_budget /
           privacy / capability）对候选集选层 —— 而非写死映射；
        3. 被选层的节点不可执行（离线/配置缺 API）时自动降级到最近
           可执行层，并在决策理由中注明；
        4. 决策结果（tier / node / reason / 耗时）经 ``last_decisions``
           与回调暴露给编排层，供 drill_agent 事件与战报端边云轨迹使用。

    代理 Model 本身不改变消息协议：路由选中的节点若与默认 SDK client
    指向同一端点（当前部署形态：三节点同指 ARK），则零开销直接走
    底层 client；指向不同端点时按节点档案动态构建 AsyncOpenAI client。
    """

    # agent 名 → 阶段任务特征（与 _DRILL_PHASE_FEATURES 语义一致，
    # 放在本模块避免 orchestrator ↔ provider 循环依赖）
    _AGENT_FEATURES: dict[str, dict[str, Any]] = {
        # 红队：攻击链实时生成 → 超低延迟优先端侧
        "recon": {"latency_budget": 0.8, "privacy": "standard", "capability": "recon", "reason": "侦察实时性要求高"},
        "vuln_correlator": {"latency_budget": 0.8, "privacy": "standard", "capability": "recon", "reason": "漏洞关联实时性要求高"},
        "exploit_planner": {"latency_budget": 3.0, "privacy": "standard", "capability": "plan", "reason": "利用链规划需规划能力"},
        # 蓝队：防御响应 → 低延迟优先边侧
        "detector": {"latency_budget": 3.0, "privacy": "standard", "capability": "detect", "reason": "告警检测低延迟"},
        "triage": {"latency_budget": 3.0, "privacy": "standard", "capability": "detect", "reason": "告警分诊低延迟"},
        "threat_hunt": {"latency_budget": 5.0, "privacy": "standard", "capability": "detect", "reason": "威胁狩猎需关联分析"},
        "ir_planner": {"latency_budget": 5.0, "privacy": "standard", "capability": "plan", "reason": "响应规划需规划能力"},
        # 紫队：评审总结 → 高算力优先云侧
        "critic": {"latency_budget": 10.0, "privacy": "unrestricted", "capability": "review", "reason": "评审需强算力"},
        "reviewer": {"latency_budget": 10.0, "privacy": "unrestricted", "capability": "review", "reason": "一致性审查需强算力"},
    }

    def __init__(self, fallback_model, registry=None, on_decision=None) -> None:
        """初始化路由代理模型。

        Args:
            fallback_model: 默认 SDK Model（所有端点相同的兜底执行体）。
            registry: NodeRegistry 实例；None 时延迟从组合根取（避免导入环）。
            on_decision: 每次路由决策回调 ``fn(agent_name, decision_dict)``。
        """
        # 继承 OpenAIChatCompletionsModel：SDK Agent 的 model 类型校验
        # 要求 Model 基类实例（TypeError: Agent model must be a string,
        # Model, or None），duck-typed 代理不被接受；继承后既是合法 Model
        # 又可覆写 get_response 插入路由决策。
        super().__init__(
            model=getattr(fallback_model, "model", ""),
            openai_client=fallback_model._client,
        )
        self._fallback = fallback_model
        self._registry = registry
        self._on_decision = on_decision
        self._client_cache: dict[str, OpenAIChatCompletionsModel] = {}
        # 最近路由决策（编排层读取后转 drill_agent 事件 / 战报）
        self.last_decisions: list[dict[str, Any]] = []
        self._current_agent: str = ""

    # ---- 编排层接线 ----

    def set_agent(self, agent_name: str) -> None:
        """标记即将执行的 agent 名（路由特征查表键）。由编排层在调用前设置。"""
        self._current_agent = agent_name

    def snapshot(self) -> list[dict[str, Any]]:
        """导出决策历史（编排层写战报 / get_drill 恢复用）。"""
        return list(self.last_decisions)

    # ---- 路由决策 ----

    def _decide(self) -> dict[str, Any]:
        """执行一次调度决策，返回含 tier/node/reason/执行体的决策 dict。"""
        from infrastructure.nodes.descriptor import detect_vendor

        feat = self._AGENT_FEATURES.get(
            self._current_agent,
            {"latency_budget": 10.0, "privacy": "unrestricted", "capability": None, "reason": "未登记 agent，默认高算力路径"},
        )
        registry = self._registry
        if registry is None:
            try:
                from backend.main import _infra_service

                if _infra_service is None:
                    from backend.main import _init_infra_service

                    _init_infra_service()
                registry = _infra_service.registry
            except Exception:  # noqa: BLE001 —— 组合根不可用时按无候选处理
                registry = None

        candidates: list[dict[str, Any]] = []
        if registry is not None:
            try:
                for snap in registry.snapshot():
                    if snap.get("status") == "offline":
                        continue
                    candidates.append(snap)
            except Exception:  # noqa: BLE001
                candidates = []

        decision: dict[str, Any] = {
            "agent": self._current_agent,
            "ts": time.time(),
            "latency_budget": feat["latency_budget"],
            "privacy": feat["privacy"],
            "capability": feat["capability"],
            "candidates": [c["node_id"] for c in candidates],
        }
        if not candidates:
            decision.update({
                "tier": "cloud",
                "node_id": "",
                "model_id": str(getattr(self._fallback, "model", "")),
                "reason": f"{feat['reason']}；无在线节点候选，走默认模型",
                "fallback": True,
            })
            return decision

        # 用真实调度器按任务特征选层（隐私分级 / 延迟预算 / 能力过滤）
        from aegisos_agents.planning.engine.scheduler.scheduler import Model, schedule
        from protocol.scheduler import Task

        models = [
            Model(
                model_id=str(s.get("model_id") or s["node_id"]),
                tier=str(s.get("tier", "cloud")),
                size={"device": "small", "edge": "medium", "cloud": "large"}.get(
                    str(s.get("tier", "cloud")), "large"
                ),
                capabilities=["recon", "detect", "plan", "review", "chat", "reasoning"],
            )
            for s in candidates
        ]
        task = Task(
            goal=f"drill agent {self._current_agent}",
            latency_budget=feat["latency_budget"],
            privacy=feat["privacy"],
        )
        try:
            chosen = schedule(task, models, feat["capability"])
            chosen_tier = str(chosen.tier)
        except ValueError:
            chosen_tier = "cloud"

        # 选定层不可执行（节点离线剔除后仍可能选到空层）→ 降级最近可执行层
        tier_rank = {"device": 0, "edge": 1, "cloud": 2}
        exec_tiers = {str(s.get("tier", "cloud")) for s in candidates}
        if chosen_tier not in exec_tiers:
            best = min(exec_tiers, key=lambda t: abs(tier_rank.get(t, 2) - tier_rank.get(chosen_tier, 2)))
            decision["downgraded_from"] = chosen_tier
            chosen_tier = best

        snap = next(s for s in candidates if str(s.get("tier", "cloud")) == chosen_tier)
        model_id = str(snap.get("model_id") or "")
        reason = f"{feat['reason']} → {_TIER_CN.get(chosen_tier, chosen_tier)}（延迟预算 {feat['latency_budget']}s/隐私 {feat['privacy']}）"
        if "downgraded_from" in decision:
            reason += f"，原选 {decision['downgraded_from']} 层离线降级"
        decision.update({
            "tier": chosen_tier,
            "node_id": str(snap.get("node_id", "")),
            "model_id": model_id,
            "reason": reason,
            "vendor": detect_vendor(str(snap.get("base_url", ""))),
            "base_url": str(snap.get("base_url", "")),
        })
        return decision

    def _model_for(self, decision: dict[str, Any]):
        """按决策取执行 Model：同端点零开销走 fallback；异端点按档案建 client。"""
        base_url = decision.get("base_url") or ""
        env_url = os.getenv("OPENAI_BASE_URL") or ""
        if not base_url or base_url.rstrip("/") == env_url.rstrip("/"):
            return self._fallback
        cached = self._client_cache.get(base_url)
        if cached is None:
            from infrastructure.nodes.descriptor import detect_vendor
            api_header = "Authorization"
            api_key = os.getenv("OPENAI_API_KEY", "")
            cached = OpenAIChatCompletionsModel(
                model=decision.get("model_id") or str(getattr(self._fallback, "model", "")),
                openai_client=AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=float(os.getenv("AEGIS_LLM_TIMEOUT", "180") or 180),
                    max_retries=int(os.getenv("AEGIS_LLM_MAX_RETRIES", "1") or 1),
                ),
            )
            self._client_cache[base_url] = cached
        return cached

    # ---- SDK Model 协议 ----

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, *, previous_response_id=None, conversation_id=None, prompt=None):
        """实现 SDK ``Model`` 协议：先路由决策，再委托执行。"""
        decision = self._decide()
        decision["latency_ms"] = 0  # 由下层执行后补充真实耗时（占位）
        self.last_decisions.append(decision)
        # 防泄漏：只保留最近 200 条
        if len(self.last_decisions) > 200:
            del self.last_decisions[:-200]
        if self._on_decision is not None:
            try:
                self._on_decision(decision)
            except Exception:  # noqa: BLE001 —— 回调失败不影响推理
                pass
        model = self._model_for(decision)
        t0 = time.time()
        resp = await model.get_response(
            system_instructions, input, model_settings, tools, output_schema,
            handoffs, tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        )
        decision["latency_ms"] = int((time.time() - t0) * 1000)
        return resp


_TIER_CN = {
    "device": "端侧·超低延迟/本地隐私",
    "edge": "边侧·低延迟/区域隔离",
    "cloud": "云侧·强算力/可脱敏",
}


class SDKProvider:
    """SDK 桥接 Provider -- 真实 API 模式下提供 SDK ``Model`` 供 Agent 使用。

    在真实 API 模式下，创建 ``AsyncOpenAI`` 客户端并配置 SDK 全局默认 API 为
    ``chat_completions``（火山引擎 ARK 不支持 Responses API），通过
    :meth:`get_sdk_model` 返回 :class:`OpenAIChatCompletionsModel` 供 SDK
    ``Agent(model=...)`` 直接使用。

    火山引擎 ARK 兼容：通过 ``OPENAI_BASE_URL`` + ``OPENAI_API_KEY`` 环境变量
    自动指向 ARK 端点，使用 Chat Completions API。

    R6.1 清理：删除了旧 ``complete()`` 同步调用方法（已被 SDK
    ``Runner.run_sync`` + ``output_type`` 结构化输出替代，无业务调用方）。

    Attributes:
        _client: OpenAI 异步客户端（真实模式）；Mock 模式下为 None。
        _mock: Mock Provider 实例（Mock 模式下使用）。
        _model: 默认模型 ID（来自 ``OPENAI_DEFAULT_MODEL`` 或代码默认值）。
    """

    def __init__(self, model_id: str = "", *, enable_routing: bool | None = None) -> None:
        """初始化 SDK Provider。

        根据 ``AEGIS_USE_MOCK`` 与 ``OPENAI_API_KEY`` 决定运行模式。
        真实模式下创建 ``AsyncOpenAI`` 客户端并配置 SDK 全局默认 API 为
        ``chat_completions``（火山引擎 ARK 不支持 Responses API）。

        R20 端边云路由：``enable_routing=True`` 时，:meth:`get_sdk_model`
        返回 :class:`RoutedSDKModel` 代理 —— 每次真实推理请求到达时按
        NodeRegistry 在线节点与任务特征（延迟/隐私/能力）实时选层，
        代替写死的单模型直连。缺省由环境变量 ``AEGIS_DRILL_ROUTING``
        控制（默认开启）。

        Args:
            model_id: 默认模型 ID；为空时从 ``OPENAI_DEFAULT_MODEL`` 环境变量读取。
            enable_routing: 是否启用端边云路由代理；None 读环境变量。
        """
        self._mock: MockProvider | None = None
        self._client: AsyncOpenAI | None = None
        self._model = model_id or os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
        if enable_routing is None:
            enable_routing = os.getenv("AEGIS_DRILL_ROUTING", "true").strip().lower() not in (
                "0", "false", "no",
            )
        self._enable_routing = enable_routing
        self.routed_model: RoutedSDKModel | None = None

        if _is_mock_mode():
            # Mock 模式：不创建网络客户端
            self._mock = MockProvider()
            return

        # 真实 API 模式：创建 OpenAI 兼容客户端（火山引擎 ARK / OpenAI 原生）
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL") or None  # None 时用 OpenAI 默认
        # R19：显式超时 + 收紧重试。旧版用库默认（600s 超时、失败重试 2 次），
        # 单步最坏可吃掉约 30min，是「一场演练 50 分钟」的尾部放大器。实测正常
        # 单步 12-42s（开思考偶发 160s），默认 120s 足够覆盖；真卡住时快速失败
        # 降级，好过整场演练死等。可用 AEGIS_LLM_TIMEOUT / AEGIS_LLM_MAX_RETRIES 调。
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=float(os.getenv("AEGIS_LLM_TIMEOUT", "180") or 180),
            max_retries=int(os.getenv("AEGIS_LLM_MAX_RETRIES", "1") or 1),
        )

        # 火山引擎 ARK 仅支持 Chat Completions，强制切换（OpenAI 原生也兼容此 API）
        set_default_openai_api("chat_completions")

        # 禁用 trace 上传（火山引擎无 OpenAI 的 tracing 端点，否则 401）
        if os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "").lower() in ("1", "true"):
            set_tracing_disabled(disabled=True)

    @property
    def is_mock(self) -> bool:
        """当前是否为 Mock 模式。"""
        return self._mock is not None

    def get_sdk_model(self, model_name: str | None = None) -> OpenAIChatCompletionsModel:
        """获取 SDK ``Model`` 实例，供 SDK ``Agent(model=...)`` 直接使用。

        用于 S2/S3 阶段将 Agent 迁移到 SDK ``Agent`` 类时，注入 SDK 原生 Model。
        Mock 模式下抛出 ``RuntimeError``（SDK Agent 不应在 Mock 模式下用真实 Model）。

        R20：启用端边云路由时返回 :class:`RoutedSDKModel` 代理 —— 代理实现
        与 SDK Model 相同的 ``get_response`` 协议，每次调用先路由后执行；
        SDK Agent/Runner 对其无感知。

        Args:
            model_name: 模型名称；为空时用初始化时的默认模型。

        Returns:
            :class:`OpenAIChatCompletionsModel` 或 :class:`RoutedSDKModel`。

        Raises:
            RuntimeError: Mock 模式下调用此方法。
        """
        if self._mock is not None:
            raise RuntimeError(
                "Mock 模式不支持获取 SDK Model；请用 AEGIS_USE_MOCK=false 切换真实 API"
            )
        assert self._client is not None
        inner = OpenAIChatCompletionsModel(
            model=model_name or self._model,
            openai_client=self._client,
        )
        if not self._enable_routing:
            return inner
        if self.routed_model is None:
            self.routed_model = RoutedSDKModel(inner)
        return self.routed_model


def create_provider(model_id: str = "") -> SDKProvider | MockProvider:
    """工厂函数 —— 根据运行模式创建合适的 Provider。

    被 ``backend/core/composition.py`` 组合根调用，注入到 11 个 Agent。
    Mock 模式返回 :class:`MockProvider`（保持与现有测试完全兼容），
    真实模式返回 :class:`SDKProvider`。

    Args:
        model_id: 默认模型 ID。

    Returns:
        :class:`MockProvider`（Mock 模式）或 :class:`SDKProvider`（真实模式）。
    """
    if _is_mock_mode():
        # Mock 模式返回原生 MockProvider，保持测试兼容
        # （cyber_provider.py 的 _CyberMockProvider 会包装它）
        return MockProvider()
    return SDKProvider(model_id=model_id)
