# date: 2026-07-06
# dev: myf
"""SDK 编排器 —— 用 openai-agents SDK 的 Agent + handoffs 实现红蓝紫攻防链。

本模块用 SDK 的 ``Agent.handoffs`` 机制串联攻防 Agent，替代
``backend/mocks/runtime.py`` 中 85 行手写的 ``_cyber_dispatch_map()``。

设计要点：
    - **红队攻击链**：recon → vuln_correlator → exploit_planner → lateral_move
      用 SDK handoff 链式传递，每个 Agent 的输出作为下一个 Agent 的输入。
    - **蓝队防御链**：detector → triage → threat_hunt → ir_planner → forensics
    - **紫队闭环**：critic 校验红队产出 → 失败时回 exploit_planner（神经符号循环）
    - **Mock/真实 API 双模式**：注入 MockSDKModel 或真实 SDK Model，两条路径走同一编排

R4.2 SDK handoffs 架构（声明式链 vs 手动串联）：
    - **手动链**（``run_red_chain``）：逐步 ``_run()`` + ``json.dumps`` 传递，
      保留作为默认执行路径（固定顺序管道的正确架构）
    - **handoff 链**（``run_red_chain_via_handoffs``）：SDK ``Agent.handoffs``
      声明式串联，LLM 通过 ``transfer_to_*`` 工具调用触发移交，
      ``on_handoff`` 回调标记各步完成状态到 :class:`ChainContext`
    - **ChainContext**：跨 handoff 共享上下文，累积各步产出（assets/findings/chain）
    - **SDK handoff 规则**：不提供 ``input_type`` 时，``on_handoff`` 回调只接收
      1 个参数 (context)；提供 ``input_type`` 时接收 2 个参数 (context, input)。
      本实现不使用 ``input_type``（中间产出类型不固定），回调只接收 context。

与现有架构的关系：
    - 本模块是 S3 阶段新增的 SDK 原生编排层，位于 ``aegisos_agents/planning/orchestrator/``
    - ``backend/mocks/runtime.py`` 的 MockRuntime 保留作为兼容层（backend DI 依赖）
    - e2e 测试可逐步切换到本编排器
    - 后续 S4 阶段将 backend composition.py 的 runtime 注入切换到本编排器

收益（对比 MockRuntime dispatch map）：
    - 删除 85 行手写 handler + 类型转换
    - SDK handoffs 自动管理状态传递 + 对话历史
    - 获得 SDK 的 tracing（可视化编排流程）+ 流式输出能力
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from aegisos_agents.action.output_types import (
    CritiqueResult,
    DetectorResult,
    ExploitPlannerResult,
    IRPlannerResult,
    ReconResult,
    ReviewResult,
    ThreatHuntResult,
    TriageResult,
    VulnCorrelatorResult,
)
# AP4: 复用规范层（action/）定义的红蓝紫 Agent 作为链上实例，单一事实来源，
# 使 AP4 的 Ask 人机协同方法在运行时编排链路中直接生效（避免编排器内重复定义）。
from aegisos_agents.action.critic.agent import CriticAgent
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert, Asset, AttackChain, AttackStep, ResponsePlan, VulnFinding

# R4.2: SDK handoffs 依赖
try:
    from agents import Agent as SDKAgent, RunContextWrapper
    from agents.handoffs import handoff

    _SDK_HANDOFF_AVAILABLE = True
except ImportError:
    _SDK_HANDOFF_AVAILABLE = False

# R4.3: SDK output_guardrail 依赖
try:
    from agents import OutputGuardrail, OutputGuardrailTripwireTriggered
    from agents.guardrail import GuardrailFunctionOutput, output_guardrail

    _SDK_GUARDRAIL_AVAILABLE = True
except ImportError:
    _SDK_GUARDRAIL_AVAILABLE = False

# R4.4: SDK tracing 依赖
try:
    from agents import add_trace_processor, set_trace_processors, trace

    _SDK_TRACING_AVAILABLE = True
except ImportError:
    _SDK_TRACING_AVAILABLE = False

from observability.inspect.monitor.tracing import (
    CyberAgentHooks,
    CyberTraceData,
    CyberTraceProcessor,
)

# R4.5: SDK FunctionTool 依赖
try:
    from agents import FunctionTool as SDKFunctionTool

    _SDK_FUNCTION_TOOL_AVAILABLE = True
except ImportError:
    _SDK_FUNCTION_TOOL_AVAILABLE = False

# AP3: GoalMode 依赖
from aegisos_agents.perception.reasoning.strategies.goal_mode import (
    GoalMode,
    GoalNode,
    GoalResult,
    GoalStatus,
)


# ==================================================================
# R4.2: ChainContext —— handoff 链共享上下文
# ==================================================================


@dataclass
class ChainContext:
    """Handoff 链共享上下文，累积各步产出。

    在 SDK handoff 链中，每个 ``on_handoff`` 回调将前一个 Agent 的
    结构化产出（JSON dict）写入对应字段。链完成后，由
    :meth:`CyberOrchestrator._context_to_red_result` /
    :meth:`CyberOrchestrator._context_to_blue_result` 转换为 protocol dataclass。

    Attributes:
        target_range: 红队目标范围。
        event_stream: 蓝队原始事件流。
        recon_output: 侦察 Agent 产出（dict）。
        vuln_output: 漏洞关联 Agent 产出（dict）。
        exploit_output: 利用链规划 Agent 产出（dict）。
        detector_output: 入侵检测 Agent 产出（dict）。
        triage_output: 告警分诊 Agent 产出（dict）。
        hunt_output: 威胁狩猎 Agent 产出（dict）。
        ir_output: 响应规划 Agent 产出（dict）。
    """

    target_range: str | None = None
    event_stream: list[dict[str, Any]] = field(default_factory=list)
    # 红队链产出
    recon_output: dict[str, Any] | None = None
    vuln_output: dict[str, Any] | None = None
    exploit_output: dict[str, Any] | None = None
    # 蓝队链产出
    detector_output: dict[str, Any] | None = None
    triage_output: dict[str, Any] | None = None
    hunt_output: dict[str, Any] | None = None
    ir_output: dict[str, Any] | None = None
    # 最终产出
    chain: Any | None = None
    plan: Any | None = None


# ---- 红队 Agent（SDK Agent 定义，供编排用）----


class ReconSDKAgent(StructuredAgent[ReconResult]):
    """红队侦察 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a network reconnaissance agent. Given a target range, "
        "return a JSON object with an 'assets' array. Each asset has "
        "asset_id, host, services (list), os, exposure."
    )
    OUTPUT_TYPE = ReconResult
    TEMPERATURE = 0.3


class VulnCorrelatorSDKAgent(StructuredAgent[VulnCorrelatorResult]):
    """红队漏洞关联 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a vulnerability correlation agent. Given a list of assets, "
        "return JSON with a 'findings' array. Each finding has: finding_id, "
        "cve_id, asset_id, cvss (float), attack_surface."
    )
    OUTPUT_TYPE = VulnCorrelatorResult
    TEMPERATURE = 0.2


class ExploitPlannerSDKAgent(StructuredAgent[ExploitPlannerResult]):
    """红队利用链规划 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an exploit chain planner. Given vulnerability findings, "
        "return JSON with chain_id, target, steps (array of {step_id, technique, "
        "from_asset, to_asset, success}), status."
    )
    OUTPUT_TYPE = ExploitPlannerResult
    TEMPERATURE = 0.4


# ---- 蓝队 Agent ----


class DetectorSDKAgent(StructuredAgent[DetectorResult]):
    """蓝队入侵检测 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an intrusion detection agent. Given an event stream, "
        "return JSON with an 'alerts' array. Each alert has: alert_id, "
        "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
    )
    OUTPUT_TYPE = DetectorResult
    TEMPERATURE = 0.2


class TriageSDKAgent(StructuredAgent[TriageResult]):
    """蓝队告警分诊 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an alert triage agent. Given alerts, return JSON with an "
        "'alerts' array containing deduplicated, severity-ordered alerts."
    )
    OUTPUT_TYPE = TriageResult
    TEMPERATURE = 0.1


class ReviewerSDKAgent(StructuredAgent[ReviewResult]):
    """紫队一致性审查 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a consistency reviewer. Given multiple artifacts, check if "
        "they are mutually consistent. Return JSON: consistent (bool), "
        "findings (array), overall_assessment (str)."
    )
    OUTPUT_TYPE = ReviewResult
    TEMPERATURE = 0.2


class CyberOrchestrator(GoalMode[dict]):
    """攻防编排器 —— 用 SDK Agent 实现红蓝紫攻防链。

    封装 11 个 SDK Agent，提供红队攻击链、蓝队防御链、紫队校验的
    编排接口。Mock 模式下注入 :class:`MockSDKModel`，真实 API 模式
    注入 SDK ``OpenAIChatCompletionsModel``。

    AP3：继承 :class:`GoalMode`，支持 :meth:`run_red_chain_with_goal` /
    :meth:`run_blue_chain_with_goal` 递归目标分解编排，替代固定模板链。

    Attributes:
        _mock: Mock Provider 实例（Mock 模式）；真实模式为 None。
        _trace_processor: R4.4 tracing 处理器（enable_tracing 后非 None）。
        _hooks: R4.4 AgentHooks 列表（install_hooks 后非空）。
    """

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 编排器接入 Ask——新增 ask_handler/eventbus 参数，蓝队 threat_hunt/ir_planner 与紫队 critic 改用规范层 Agent 以复用人机协同能力
    def __init__(
        self,
        mock: MockProvider | None = None,
        model=None,
        ask_handler=None,
        eventbus=None,
    ) -> None:
        """初始化编排器，装配 11 个 SDK Agent。

        Args:
            mock: :class:`MockProvider` 实例（Mock 模式）；真实模式传 None。
            model: SDK ``Model`` 实例（真实 API 模式）；非 None 时优先于 mock，
                由 :meth:`SDKProvider.get_sdk_model` 创建。9 个 Agent 共享同一 Model。
            ask_handler: 可选 :class:`AskHandler`（AP4 人机协同）；下发至
                threat_hunt / ir_planner / critic。None 时各 Agent 退化为
                :class:`AutoAskHandler`（无人值守即时安全降级）。
            eventbus: 可选事件总线；下发至上述三个 Agent，使其发布
                ``HumanInputRequired`` / ``HumanResponse`` 事件供前端渲染。
        """
        self._mock = mock
        # AP4: 保存人机协同 handler，供 _with_human_check 编排方法下发
        self._ask_handler = ask_handler
        # R4.4: tracing 状态
        self._trace_processor: CyberTraceProcessor | None = None
        self._hooks: list[CyberAgentHooks] = []
        # 红队
        self.recon = ReconSDKAgent(mock=mock, model=model)
        self.vuln_correlator = VulnCorrelatorSDKAgent(mock=mock, model=model)
        self.exploit_planner = ExploitPlannerSDKAgent(mock=mock, model=model)
        # 蓝队
        self.detector = DetectorSDKAgent(mock=mock, model=model)
        self.triage = TriageSDKAgent(mock=mock, model=model)
        # AP4: 规范层 Agent（自带 Ask 人机协同能力），注入 ask_handler/eventbus
        self.threat_hunt = ThreatHuntAgent(
            mock=mock, model=model, ask_handler=ask_handler
        )
        self.ir_planner = IRPlannerAgent(
            mock=mock, model=model, ask_handler=ask_handler
        )
        # 紫队
        self.critic = CriticAgent(mock=mock, model=model, ask_handler=ask_handler)
        self.reviewer = ReviewerSDKAgent(mock=mock, model=model)
        # AP4: 将事件总线下发至三个 HITL Agent，使其发布人机协同事件
        if eventbus is not None:
            self.threat_hunt.set_event_bus(eventbus)
            self.ir_planner.set_event_bus(eventbus)
            self.critic.set_event_bus(eventbus)

    def run_red_chain(self, target_range: str) -> dict[str, Any]:
        """执行红队攻击链：recon → vuln_correlator → exploit_planner。

        各步产出依次传递，返回包含 assets/findings/chain 的结果字典。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的字典（值为 protocol dataclass）。
        """
        # 1) 侦察
        recon_result = self.recon._run(f"Scan target range: {target_range}")
        assets = [
            Asset(
                asset_id=a.asset_id, host=a.host, services=a.services, os=a.os, exposure=a.exposure
            )
            for a in recon_result.assets
        ]

        # 2) 漏洞关联
        assets_desc = json.dumps(
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        vuln_result = self.vuln_correlator._run(
            f"Correlate vulnerabilities for these assets: {assets_desc}"
        )
        findings = [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                asset_id=f.asset_id,
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in vuln_result.findings
        ]

        # 3) 利用链规划
        findings_desc = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "cve_id": f.cve_id,
                    "asset_id": f.asset_id,
                    "cvss": f.cvss,
                }
                for f in findings
            ]
        )
        exploit_result = self.exploit_planner._run(f"Plan exploit chain for: {findings_desc}")
        chain = AttackChain(
            chain_id=exploit_result.chain_id,
            target=exploit_result.target,
            steps=[AttackStep(**s.model_dump()) for s in exploit_result.steps],
            status=exploit_result.status,
        )

        return {"assets": assets, "findings": findings, "chain": chain}

    def run_blue_chain(self, event_stream: list[dict[str, Any]]) -> dict[str, Any]:
        """执行蓝队防御链：detector → triage → threat_hunt → ir_planner。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        # 1) 入侵检测
        detector_result = self.detector._run(f"Detect anomalies in: {json.dumps(event_stream)}")
        alerts = [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in detector_result.alerts
        ]

        # 2) 告警分诊
        alerts_desc = json.dumps(
            [
                {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
                for a in alerts
            ]
        )
        triage_result = self.triage._run(f"Triage these alerts: {alerts_desc}")
        triaged = [Alert(**t.model_dump()) for t in triage_result.alerts] or alerts

        # 3) 威胁狩猎
        hunt_result = self.threat_hunt._run(f"Generate hunting hypotheses for: {alerts_desc}")
        hypotheses = [h.model_dump() for h in hunt_result.hypotheses]

        # 4) 响应规划
        ir_result = self.ir_planner._run(f"Plan response for: {json.dumps(hypotheses)}")
        plan = ResponsePlan(
            plan_id=ir_result.plan_id,
            actions=[a.model_dump() for a in ir_result.actions],
            confidence=ir_result.confidence,
            rollback=ir_result.rollback,
        )

        return {"alerts": alerts, "triaged": triaged, "hypotheses": hypotheses, "plan": plan}

    def run_purple_review(
        self, chain: AttackChain, plan: ResponsePlan, alerts: list[Alert]
    ) -> dict[str, Any]:
        """执行紫队校验：critic 校验攻击链 + reviewer 跨产出一致性审查。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。

        Returns:
            含 ``critique`` / ``review`` 的字典（均为 dict）。
        """
        # 紫队批判红队攻击链
        critique_result = self.critic._run(f"Critique: {json.dumps(chain.to_dict())}")
        critique = critique_result.model_dump()

        # 紫队跨产出一致性审查
        artifacts = {
            "attack_chain": chain.to_dict(),
            "response_plan": asdict(plan),
            "alerts": [asdict(a) for a in alerts],
        }
        review_result = self.reviewer._run(
            f"Review consistency: {json.dumps(artifacts, default=str)}"
        )
        review = review_result.model_dump()

        return {"critique": critique, "review": review}

    # ==================================================================
    # AP4: 带人机协同（Ask 范式）的攻防编排方法
    # ==================================================================

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 新增 run_blue_chain_with_human_check——蓝队防御链在威胁狩猎与响应规划处接入人机确认
    def run_blue_chain_with_human_check(
        self,
        event_stream: list[dict[str, Any]],
        ask_handler=None,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """执行带人机协同的蓝队防御链（AP4）。

        链路同 :meth:`run_blue_chain`（detector → triage → threat_hunt →
        ir_planner），但在 threat_hunt 假设置信度偏低、ir_planner 计划含破坏性
        动作时插入人工确认闸门（Ask 范式），超时/无人值守自动保守降级，
        不阻塞整条防御链。

        Args:
            event_stream: 原始事件流列表。
            ask_handler: 可选 :class:`AskHandler`；None 时使用编排器初始化时的 handler。
            confidence_threshold: 触发澄清的置信度下限。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        # 1) 入侵检测（无需人工确认）
        detector_result = self.detector._run(f"Detect anomalies in: {json.dumps(event_stream)}")
        alerts = [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in detector_result.alerts
        ]

        # 2) 告警分诊（无需人工确认）
        alerts_desc = json.dumps(
            [
                {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
                for a in alerts
            ]
        )
        triage_result = self.triage._run(f"Triage these alerts: {alerts_desc}")
        triaged = [Alert(**t.model_dump()) for t in triage_result.alerts] or alerts

        # 3) 威胁狩猎（低置信度假设时暂停澄清）
        hunt_handler = ask_handler or self._ask_handler
        hypotheses = self.threat_hunt.hunt_with_human_check(
            triaged, confidence_threshold=confidence_threshold, ask_handler=hunt_handler
        )

        # 4) 响应规划（破坏性动作前确认）
        ir_handler = ask_handler or self._ask_handler
        plan = self.ir_planner.plan_response_with_human_check(
            hypotheses, ask_handler=ir_handler
        )

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
        }

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 新增 run_purple_review_with_human_check——紫队批判严重度达阈值时请求人工复核
    def run_purple_review_with_human_check(
        self,
        chain: AttackChain,
        plan: ResponsePlan,
        alerts: list[Alert],
        ask_handler=None,
        severity_threshold: str = "high",
    ) -> dict[str, Any]:
        """执行带人机协同的紫队校验（AP4）。

        同 :meth:`run_purple_review` 的 reviewer 一致性审查，但 critic 批判在
        判定严重度达到 ``severity_threshold`` 时暂停请求人工复核（Ask 范式），
        超时/无人值守降级为确认结论并标记。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。
            ask_handler: 可选 :class:`AskHandler`；None 时使用编排器初始化时的 handler。
            severity_threshold: 触发人工复核的严重度阈值。

        Returns:
            含 ``critique`` / ``review`` 的字典。
        """
        handler = ask_handler or self._ask_handler
        # 紫队批判红队攻击链（严重度达阈值时请求人工复核）
        critique = self.critic.critique_with_human_check(
            chain.to_dict(),
            side="red",
            severity_threshold=severity_threshold,
            ask_handler=handler,
        )

        # 紫队跨产出一致性审查（保持原逻辑）
        artifacts = {
            "attack_chain": chain.to_dict(),
            "response_plan": asdict(plan),
            "alerts": [asdict(a) for a in alerts],
        }
        review_result = self.reviewer._run(
            f"Review consistency: {json.dumps(artifacts, default=str)}"
        )
        review = review_result.model_dump()

        return {"critique": critique, "review": review}

    # ==================================================================
    # R4.2: SDK Agent.handoffs 声明式链
    # ==================================================================

    def run_red_chain_via_handoffs(self, target_range: str) -> dict[str, Any]:
        """通过 SDK handoffs 执行红队攻击链（声明式链）。

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：手动逐步 ``_run()`` + ``json.dumps`` 传递
              （固定管道的正确架构，默认路径）
            - 本方法：用 SDK ``Agent.handoffs`` 声明式串联，
              LLM 通过 ``transfer_to_*`` 工具调用触发移交，
              ``on_handoff`` 回调 + ``input_type`` 结构化参数捕获中间产出

        限制：
            - Mock 模式下 ``MockSDKModel`` 返回纯文本（非工具调用），
              LLM 不会触发 handoff，本方法回退到 ``run_red_chain``。
            - 真实 LLM 模式下可用，但 LLM 可能不按预期移交
              （需在 prompt 中强制指令）。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的字典。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return self.run_red_chain(target_range)

        # 构建 handoff 链上下文
        ctx = ChainContext(target_range=target_range)

        try:
            await_result = self._run_red_handoff_chain(ctx, target_range)
            # 如果 handoff 链成功（LLM 驱动了移交），使用累积的产出
            if ctx.chain is not None:
                return self._context_to_red_result(ctx)
        except Exception:
            pass

        # 回退到手动链
        return self.run_red_chain(target_range)

    def run_blue_chain_via_handoffs(
        self, event_stream: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """通过 SDK handoffs 执行蓝队防御链（声明式链）。

        链路：detector → triage → threat_hunt → ir_planner

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return self.run_blue_chain(event_stream)

        ctx = ChainContext(event_stream=event_stream)

        try:
            await_result = self._run_blue_handoff_chain(ctx, event_stream)
            if ctx.plan is not None:
                return self._context_to_blue_result(ctx)
        except Exception:
            pass

        # 回退到手动链
        return self.run_blue_chain(event_stream)

    def _run_red_handoff_chain(
        self, ctx: ChainContext, target_range: str
    ) -> Any:
        """运行红队 handoff 链。

        创建 SDK Agent 并配置 handoffs，用 ``on_handoff`` 回调将
        各步产出捕获到 :class:`ChainContext`。
        """
        from agents import Runner

        # 创建轻量级 SDK Agent 用于 handoff 链
        # 每个 Agent 配置 handoffs 指向下一个 Agent
        exploit_agent = SDKAgent(
            name="ExploitPlannerAgent",
            instructions="Plan an exploit chain based on vulnerabilities. "
            "After producing your output, call transfer_to_complete to finish.",
            handoffs=[],  # 末端无 handoff
        )

        vuln_agent = SDKAgent(
            name="VulnCorrelatorAgent",
            instructions="Correlate vulnerabilities for given assets. "
            "After producing your output, call transfer_to_exploit_planner.",
            handoffs=[exploit_agent],
        )

        recon_agent = SDKAgent(
            name="ReconAgent",
            instructions=f"Scan target range {target_range}. "
            "After producing your output, call transfer_to_vuln_correlator.",
            handoffs=[vuln_agent],
        )

        # 配置 on_handoff 回调（捕获中间产出到 ChainContext）
        # 注意：on_handoff 接收 (context, input_json)，但无法访问 agent 的结构化输出
        # 因此我们用 ChainContext 累积 input_json 作为链间数据传递
        self._configure_red_handoff_callbacks(ctx, recon_agent, vuln_agent, exploit_agent)

        # 运行链——由 LLM 驱动 handoff
        return Runner.run_sync(
            recon_agent,
            f"Scan target range: {target_range}",
        )

    def _run_blue_handoff_chain(
        self, ctx: ChainContext, event_stream: list[dict[str, Any]]
    ) -> Any:
        """运行蓝队 handoff 链。

        链路：detector → triage → threat_hunt → ir_planner
        """
        from agents import Runner

        ir_agent = SDKAgent(
            name="IRPlannerAgent",
            instructions="Plan incident response actions. This is the final step.",
            handoffs=[],
        )
        hunt_agent = SDKAgent(
            name="ThreatHuntAgent",
            instructions="Generate threat hunting hypotheses. "
            "After producing your output, call transfer_to_ir_planner.",
            handoffs=[ir_agent],
        )
        triage_agent = SDKAgent(
            name="TriageAgent",
            instructions="Triage detected alerts. "
            "After producing your output, call transfer_to_threat_hunt.",
            handoffs=[hunt_agent],
        )
        detector_agent = SDKAgent(
            name="DetectorAgent",
            instructions="Detect anomalies in the event stream. "
            "After producing your output, call transfer_to_triage.",
            handoffs=[triage_agent],
        )

        self._configure_blue_handoff_callbacks(
            ctx, detector_agent, triage_agent, hunt_agent, ir_agent
        )

        return Runner.run_sync(
            detector_agent,
            f"Detect anomalies in: {json.dumps(event_stream)}",
        )

    def _configure_red_handoff_callbacks(
        self,
        ctx: ChainContext,
        recon_agent: Any,
        vuln_agent: Any,
        exploit_agent: Any,
    ) -> None:
        """配置红队 handoff 回调，捕获中间产出到 ChainContext。

        SDK ``handoff()`` 规则：
            - 不提供 ``input_type`` 时，``on_handoff`` 只接收 1 个参数 (context)
            - 提供 ``input_type`` 时，``on_handoff`` 接收 2 个参数 (context, input)

        本方法不使用 ``input_type``（因为中间产出类型不固定），
        因此 ``on_handoff`` 回调只接收 context，从 context 中读取累积的产出。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return

        def on_recon_to_vuln(wrapper: RunContextWrapper[ChainContext]) -> None:
            """recon → vuln handoff 回调：标记侦察完成。"""
            ctx.recon_output = {"status": "recon_handoff_triggered"}

        def on_vuln_to_exploit(wrapper: RunContextWrapper[ChainContext]) -> None:
            """vuln → exploit handoff 回调：标记漏洞关联完成。"""
            ctx.vuln_output = {"status": "vuln_handoff_triggered"}

        # 替换默认 handoffs 为带回调的版本
        recon_agent.handoffs = [handoff(vuln_agent, on_handoff=on_recon_to_vuln)]
        vuln_agent.handoffs = [handoff(exploit_agent, on_handoff=on_vuln_to_exploit)]

    def _configure_blue_handoff_callbacks(
        self,
        ctx: ChainContext,
        detector_agent: Any,
        triage_agent: Any,
        hunt_agent: Any,
        ir_agent: Any,
    ) -> None:
        """配置蓝队 handoff 回调，捕获中间产出到 ChainContext。"""
        if not _SDK_HANDOFF_AVAILABLE:
            return

        def on_detector_to_triage(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.detector_output = {"status": "detector_handoff_triggered"}

        def on_triage_to_hunt(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.triage_output = {"status": "triage_handoff_triggered"}

        def on_hunt_to_ir(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.hunt_output = {"status": "hunt_handoff_triggered"}

        detector_agent.handoffs = [handoff(triage_agent, on_handoff=on_detector_to_triage)]
        triage_agent.handoffs = [handoff(hunt_agent, on_handoff=on_triage_to_hunt)]
        hunt_agent.handoffs = [handoff(ir_agent, on_handoff=on_hunt_to_ir)]

    def _context_to_red_result(self, ctx: ChainContext) -> dict[str, Any]:
        """将 ChainContext 转换为红队链结果字典。"""
        assets: list[Asset] = []
        findings: list[VulnFinding] = []
        chain: AttackChain | None = None

        if ctx.recon_output:
            assets = [
                Asset(
                    asset_id=a.get("asset_id", ""),
                    host=a.get("host", ""),
                    services=a.get("services", []),
                    os=a.get("os", ""),
                    exposure=a.get("exposure", "unknown"),
                )
                for a in ctx.recon_output.get("assets", [])
            ]

        if ctx.vuln_output:
            findings = [
                VulnFinding(
                    finding_id=f.get("finding_id", ""),
                    cve_id=f.get("cve_id", ""),
                    asset_id=f.get("asset_id", ""),
                    cvss=f.get("cvss", 0.0),
                    attack_surface=f.get("attack_surface", ""),
                )
                for f in ctx.vuln_output.get("findings", [])
            ]

        if ctx.exploit_output:
            exp = ctx.exploit_output
            chain = AttackChain(
                chain_id=exp.get("chain_id", ""),
                target=exp.get("target", ctx.target_range or ""),
                steps=[AttackStep(**s) for s in exp.get("steps", [])],
                status=exp.get("status", "planned"),
            )
        else:
            chain = AttackChain(
                chain_id="", target=ctx.target_range or "", steps=[], status="failed"
            )

        return {"assets": assets, "findings": findings, "chain": chain}

    def _context_to_blue_result(self, ctx: ChainContext) -> dict[str, Any]:
        """将 ChainContext 转换为蓝队链结果字典。"""
        alerts: list[Alert] = []
        triaged: list[Alert] = []
        hypotheses: list[dict] = []
        plan: ResponsePlan | None = None

        if ctx.detector_output:
            alerts = [
                Alert(
                    alert_id=a.get("alert_id", ""),
                    severity=a.get("severity", "low"),
                    src=a.get("src", ""),
                    dst=a.get("dst", ""),
                    technique=a.get("technique", ""),
                    raw=a.get("raw", {}),
                )
                for a in ctx.detector_output.get("alerts", [])
            ]

        if ctx.triage_output:
            triaged = [
                Alert(**t) for t in ctx.triage_output.get("alerts", [])
            ] or alerts

        if ctx.hunt_output:
            hypotheses = ctx.hunt_output.get("hypotheses", [])

        if ctx.ir_output:
            ir = ctx.ir_output
            plan = ResponsePlan(
                plan_id=ir.get("plan_id", ""),
                actions=ir.get("actions", []),
                confidence=ir.get("confidence", 0.0),
                rollback=ir.get("rollback", {}),
            )
        else:
            plan = ResponsePlan(
                plan_id="", actions=[], confidence=0.0, rollback={}
            )

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
        }

    # ==================================================================
    # R4.3: SDK output_guardrails 紫队校验
    # ==================================================================

    def run_red_chain_with_guardrail(
        self, target_range: str, max_retries: int = 2
    ) -> dict[str, Any]:
        """带 output_guardrail 的红队攻击链（紫队校验闭环）。

        在 exploit_planner Agent 的 ``output_guardrails`` 上注入紫队 critic 校验：
            1. 正常执行红队链（recon → vuln → exploit）
            2. exploit_planner 产出后，guardrail 校验攻击链有效性
            3. 如果 guardrail tripwire 触发（``tripwire_triggered=True``），
               SDK 抛出 ``OutputGuardrailTripwireTriggered`` 异常
            4. 捕获异常，从 ``output_info`` 提取反馈，重新执行 exploit_planner
            5. 最多重试 ``max_retries`` 次

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：无校验，直接返回
            - 本方法：有 SDK guardrail 校验 + 手动重试循环

        限制：
            - SDK guardrail 抛异常后不会自动重试（需手动捕获 + 重新调用）
            - Mock 模式下 MockSDKModel 返回固定 JSON，guardrail 可能不触发

        Args:
            target_range: 目标网络范围。
            max_retries: guardrail 触发后最大重试次数（默认 2）。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` / ``guardrail_passed`` 的字典。
        """
        # 先执行 recon + vuln（不受 guardrail 影响）
        recon_result = self.recon._run(f"Scan target range: {target_range}")
        assets = [
            Asset(
                asset_id=a.asset_id, host=a.host, services=a.services, os=a.os, exposure=a.exposure
            )
            for a in recon_result.assets
        ]

        assets_desc = json.dumps(
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        vuln_result = self.vuln_correlator._run(
            f"Correlate vulnerabilities for these assets: {assets_desc}"
        )
        findings = [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                asset_id=f.asset_id,
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in vuln_result.findings
        ]

        findings_desc = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "cve_id": f.cve_id,
                    "asset_id": f.asset_id,
                    "cvss": f.cvss,
                }
                for f in findings
            ]
        )

        # 执行 exploit_planner + guardrail 重试循环
        guardrail_passed = False
        feedback = ""
        exploit_result = None

        # 注入 output_guardrail 到 exploit_planner 的 SDK Agent
        if _SDK_GUARDRAIL_AVAILABLE:
            guardrail = self.create_attack_chain_guardrail()
            if guardrail is not None:
                self.exploit_planner._sdk_agent.output_guardrails = [guardrail]

        for attempt in range(max_retries + 1):
            prompt = f"Plan exploit chain for: {findings_desc}"
            if feedback:
                prompt += f"\n\nPrevious attempt was rejected. Feedback: {feedback}"

            try:
                exploit_result = self.exploit_planner._run(prompt)
                guardrail_passed = True
                break
            except OutputGuardrailTripwireTriggered as e:
                # 从 guardrail 结果中提取反馈
                feedback = str(
                    e.guardrail_result.output.output_info
                    if e.guardrail_result and e.guardrail_result.output
                    else "Attack chain validation failed"
                )
                if attempt >= max_retries:
                    # 最后一次重试仍失败，返回未通过的结果
                    if exploit_result is None:
                        # 没有任何产出，返回空链
                        chain = AttackChain(
                            chain_id="",
                            target=target_range,
                            steps=[],
                            status="failed",
                        )
                        return {
                            "assets": assets,
                            "findings": findings,
                            "chain": chain,
                            "guardrail_passed": False,
                            "guardrail_feedback": feedback,
                        }
                    break

        # 构建最终攻击链
        if exploit_result is not None:
            chain = AttackChain(
                chain_id=exploit_result.chain_id,
                target=exploit_result.target,
                steps=[AttackStep(**s.model_dump()) for s in exploit_result.steps],
                status=exploit_result.status,
            )
        else:
            chain = AttackChain(
                chain_id="", target=target_range, steps=[], status="failed"
            )

        # 清理 guardrail（避免影响后续调用）
        if _SDK_GUARDRAIL_AVAILABLE:
            self.exploit_planner._sdk_agent.output_guardrails = []

        return {
            "assets": assets,
            "findings": findings,
            "chain": chain,
            "guardrail_passed": guardrail_passed,
            "guardrail_feedback": feedback if not guardrail_passed else "",
        }

    @staticmethod
    def create_attack_chain_guardrail() -> Any:
        """创建攻击链校验 output_guardrail。

        返回一个 :class:`OutputGuardrail`，校验 Agent 产出的攻击链是否：
            - 有至少 1 个步骤
            - 每个步骤有 technique 字段
            - chain_id 非空

        校验失败时返回 ``GuardrailFunctionOutput(tripwire_triggered=True)``，
        SDK 将抛出 ``OutputGuardrailTripwireTriggered`` 异常。

        Returns:
            :class:`OutputGuardrail` 实例；SDK 不可用时返回 None。
        """
        if not _SDK_GUARDRAIL_AVAILABLE:
            return None

        @output_guardrail(name="attack_chain_validator")
        def validate_attack_chain(
            ctx: RunContextWrapper[Any], agent: Any, agent_output: Any
        ) -> GuardrailFunctionOutput:
            """校验攻击链产出。"""
            issues: list[str] = []

            # agent_output 可能是 Pydantic 模型或 dict
            if hasattr(agent_output, "model_dump"):
                output_dict = agent_output.model_dump()
            elif isinstance(agent_output, dict):
                output_dict = agent_output
            else:
                return GuardrailFunctionOutput(
                    tripwire_triggered=True,
                    output_info="Invalid output type: expected ExploitPlannerResult",
                )

            chain_id = output_dict.get("chain_id", "")
            if not chain_id:
                issues.append("chain_id is empty")

            steps = output_dict.get("steps", [])
            if not steps:
                issues.append("attack chain has no steps")

            for i, step in enumerate(steps):
                step_dict = step if isinstance(step, dict) else step.model_dump() if hasattr(step, "model_dump") else {}
                if not step_dict.get("technique"):
                    issues.append(f"step {i} has no technique")

            if issues:
                return GuardrailFunctionOutput(
                    tripwire_triggered=True,
                    output_info="; ".join(issues),
                )

            return GuardrailFunctionOutput(
                tripwire_triggered=False,
                output_info="Attack chain validation passed",
            )

        return validate_attack_chain

    # ==================================================================
    # R4.4: SDK tracing + AgentHooks
    # ==================================================================

    def enable_tracing(self) -> CyberTraceProcessor:
        """启用 SDK tracing，返回 trace 处理器。

        创建 :class:`CyberTraceProcessor` 并注册到 SDK 全局。
        之后调用 :meth:`run_red_chain_traced` / :meth:`run_blue_chain_traced` /
        :meth:`run_purple_review_traced` 时，SDK 自动采集 trace/span 数据。

        Returns:
            :class:`CyberTraceProcessor` 实例（可通过 ``get_trace_data()`` 获取数据）。

        Raises:
            RuntimeError: SDK tracing 不可用时抛出。
        """
        if not _SDK_TRACING_AVAILABLE:
            raise RuntimeError("SDK tracing is not available")
        self._trace_processor = CyberTraceProcessor()
        set_trace_processors([self._trace_processor])
        return self._trace_processor

    def disable_tracing(self) -> None:
        """禁用 SDK tracing，清理处理器状态。"""
        if self._trace_processor is not None:
            self._trace_processor.shutdown()
            self._trace_processor = None
        # 恢复 SDK 默认 trace 处理器（空列表 = 禁用自定义处理器）
        if _SDK_TRACING_AVAILABLE:
            set_trace_processors([])

    def install_hooks(self, eventbus: Any = None, task_id: str = "") -> list[CyberAgentHooks]:
        """为所有 9 个 SDK Agent 安装生命周期钩子。

        为每个 Agent 创建 :class:`CyberAgentHooks` 并设置到 ``agent.hooks`` 属性。
        SDK Runner 执行 Agent 时自动触发回调，记录 ``on_start`` / ``on_end`` 等事件。

        R5.4：若注入 ``eventbus``，回调中还发布 :class:`protocol.Event` 到总线，
        供 ``backend/routers/sse.py`` 实时推送与 ``observability/inspect/replay/`` 回放消费。

        Args:
            eventbus: 可选的 :class:`EventBus` 实例；非 None 时钩子发布事件到总线。
            task_id: 可选的任务 ID，作为发布事件的 ``task_id`` 字段。

        Returns:
            安装的 :class:`CyberAgentHooks` 列表（9 个）。
        """
        agents = [
            self.recon,
            self.vuln_correlator,
            self.exploit_planner,
            self.detector,
            self.triage,
            self.threat_hunt,
            self.ir_planner,
            self.critic,
            self.reviewer,
        ]
        self._hooks = []
        for agent in agents:
            hook = CyberAgentHooks(
                agent_name=agent.__class__.__name__,
                eventbus=eventbus,
                task_id=task_id,
            )
            agent._sdk_agent.hooks = hook
            self._hooks.append(hook)
        return self._hooks

    def get_hooks_events(self) -> list[dict[str, Any]]:
        """汇总所有 AgentHooks 采集的事件。

        Returns:
            事件字典列表（每个含 ``event_type`` / ``agent_name`` / ``timestamp`` / ``data``）。
        """
        events: list[dict[str, Any]] = []
        for hook in self._hooks:
            for evt in hook.events:
                events.append(evt.to_dict())
        return events

    def get_trace_data(self) -> CyberTraceData | None:
        """获取最近一次 trace 的采集数据。

        Returns:
            :class:`CyberTraceData` 实例；未启用 tracing 或无 trace 时返回 None。
        """
        if self._trace_processor is None:
            return None
        return self._trace_processor.get_trace_data()

    def get_trace_json(self) -> str | None:
        """获取最近一次 trace 的 JSON 字符串。

        Returns:
            JSON 字符串；未启用 tracing 或无 trace 时返回 None。
        """
        data = self.get_trace_data()
        if data is None:
            return None
        return data.to_json()

    def run_red_chain_traced(self, target_range: str) -> dict[str, Any]:
        """带 SDK tracing 的红队攻击链。

        用 ``trace(workflow_name="cyber_red_chain")`` 上下文管理器包裹
        :meth:`run_red_chain`，SDK 自动采集 trace/span 数据。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的字典（同 :meth:`run_red_chain`）。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_red_chain(target_range)

        with trace(
            workflow_name="cyber_red_chain",
            metadata={"scenario": "red", "target": target_range},
        ):
            result = self.run_red_chain(target_range)
        return result

    def run_blue_chain_traced(
        self, event_stream: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """带 SDK tracing 的蓝队防御链。

        用 ``trace(workflow_name="cyber_blue_chain")`` 上下文管理器包裹
        :meth:`run_blue_chain`。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_blue_chain(event_stream)

        with trace(
            workflow_name="cyber_blue_chain",
            metadata={"scenario": "blue", "events": len(event_stream)},
        ):
            result = self.run_blue_chain(event_stream)
        return result

    def run_purple_review_traced(
        self, chain: AttackChain, plan: ResponsePlan, alerts: list[Alert]
    ) -> dict[str, Any]:
        """带 SDK tracing 的紫队校验。

        用 ``trace(workflow_name="cyber_purple_review")`` 上下文管理器包裹
        :meth:`run_purple_review`。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。

        Returns:
            含 ``critique`` / ``review`` 的字典。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_purple_review(chain, plan, alerts)

        with trace(
            workflow_name="cyber_purple_review",
            metadata={
                "scenario": "purple",
                "chain_steps": len(chain.steps),
                "alert_count": len(alerts),
            },
        ):
            result = self.run_purple_review(chain, plan, alerts)
        return result

    # ==================================================================
    # R4.5: SDK FunctionTool 注册攻防工具
    # ==================================================================

    def get_red_team_tools(self) -> list[Any]:
        """获取红队 SDK FunctionTool 列表。

        红队工具：
            - ``nmap_scan``         — 网络扫描（低风险）
            - ``metasploit_exploit`` — 漏洞利用（高危，needs_approval=True）
            - ``lateral_move_exec``  — 横向移动（高危，needs_approval=True）

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_red_team_tools

        return create_red_team_tools()

    def get_blue_team_tools(self) -> list[Any]:
        """获取蓝队 SDK FunctionTool 列表。

        蓝队工具：
            - ``query_attck_kb``    — 查询 ATT&CK 知识库
            - ``query_cve_db``      — 查询 CVE 漏洞库
            - ``correlate_alerts``  — 关联告警分析

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_blue_team_tools

        return create_blue_team_tools()

    def get_all_cyber_tools(self) -> list[Any]:
        """获取全部攻防 SDK FunctionTool 列表（红队 + 蓝队）。

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_all_cyber_tools

        return create_all_cyber_tools()

    def install_red_team_tools(self) -> list[Any]:
        """为红队 Agent 安装 FunctionTool。

        将红队工具注册到对应 Agent 的 SDK ``Agent.tools`` 属性：
            - ``recon`` ← ``nmap_scan``
            - ``exploit_planner`` ← ``metasploit_exploit``
            - ``exploit_planner`` ← ``lateral_move_exec``

        Returns:
            安装到 Agent 上的 FunctionTool 列表。
        """
        tools = self.get_red_team_tools()
        if not tools:
            return []

        tool_map: dict[str, list[Any]] = {
            "nmap_scan": [self.recon],
            "metasploit_exploit": [self.exploit_planner],
            "lateral_move_exec": [self.exploit_planner],
        }

        for tool in tools:
            tool_name = getattr(tool, "name", "")
            agents = tool_map.get(tool_name, [])
            for agent in agents:
                existing = list(agent._sdk_agent.tools)
                existing.append(tool)
                agent._sdk_agent.tools = existing

        return tools

    def install_blue_team_tools(self) -> list[Any]:
        """为蓝队 Agent 安装 FunctionTool。

        将蓝队工具注册到对应 Agent 的 SDK ``Agent.tools`` 属性：
            - ``detector`` ← ``correlate_alerts``
            - ``triage`` ← ``correlate_alerts``
            - ``vuln_correlator`` ← ``query_cve_db``
            - ``detector`` ← ``query_attck_kb``
            - ``threat_hunt`` ← ``query_attck_kb``

        Returns:
            安装到 Agent 上的 FunctionTool 列表。
        """
        tools = self.get_blue_team_tools()
        if not tools:
            return []

        tool_map: dict[str, list[Any]] = {
            "correlate_alerts": [self.detector, self.triage],
            "query_cve_db": [self.vuln_correlator],
            "query_attck_kb": [self.detector, self.threat_hunt],
        }

        for tool in tools:
            tool_name = getattr(tool, "name", "")
            agents = tool_map.get(tool_name, [])
            for agent in agents:
                existing = list(agent._sdk_agent.tools)
                existing.append(tool)
                agent._sdk_agent.tools = existing

        return tools

    def install_all_tools(self) -> list[Any]:
        """为所有 Agent 安装攻防 FunctionTool（红队 + 蓝队）。

        Returns:
            全部安装的 FunctionTool 列表。
        """
        red = self.install_red_team_tools()
        blue = self.install_blue_team_tools()
        return red + blue

    def uninstall_all_tools(self) -> None:
        """从所有 Agent 移除已安装的 FunctionTool。

        将所有 Agent 的 ``Agent.tools`` 重置为空列表。
        """
        agents = [
            self.recon,
            self.vuln_correlator,
            self.exploit_planner,
            self.detector,
            self.triage,
            self.threat_hunt,
            self.ir_planner,
            self.critic,
            self.reviewer,
        ]
        for agent in agents:
            agent._sdk_agent.tools = []

    def get_agent_tools(self, agent_name: str) -> list[Any]:
        """获取指定 Agent 已安装的 FunctionTool 列表。

        Args:
            agent_name: Agent 属性名（如 ``"recon"`` / ``"detector"``）。

        Returns:
            该 Agent 上已安装的 FunctionTool 列表。
        """
        agent = getattr(self, agent_name, None)
        if agent is None:
            return []
        return list(agent._sdk_agent.tools)

    def get_high_risk_tools(self) -> list[Any]:
        """获取需要审批的高危工具列表。

        高危工具（``needs_approval=True``）：
            - ``metasploit_exploit``
            - ``lateral_move_exec``

        Returns:
            高危 FunctionTool 列表。
        """
        all_tools = self.get_all_cyber_tools()
        return [t for t in all_tools if getattr(t, "needs_approval", False)]

    # ==================================================================
    # AP3: Goal 范式（递归目标分解 + 失败重试 + 备选路径）
    # ==================================================================

    # date: 2026-07-08
    # dev: myf
    # changelog: AP3.2 CyberOrchestrator 接入 Goal--新增 run_red_chain_with_goal / run_blue_chain_with_goal / _create_red_agent_executor / _create_blue_agent_executor 方法

    def run_red_chain_with_goal(
        self,
        target_range: str,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Goal 范式执行红队攻击链（递归目标分解 + 失败重试）。

        替代 :meth:`run_red_chain` 的固定模板链，将目标分解为子目标树：
            recon -> vuln_correlator -> exploit_planner -> lateral_move

        每个子目标由对应 Agent 执行，失败时自动重试（最多 max_retries 次），
        重试时注入 fallback 备选路径提示。最终汇聚所有子目标产出。

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：固定模板，无重试，单次执行
            - 本方法：递归分解，失败重试 + 备选路径，更鲁棒

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。
            max_retries: 子目标失败后的最大重试次数。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` / ``goal_result`` 的字典。
            ``goal_result`` 是 :class:`GoalResult`，含子目标执行状态。
        """
        tree = self.decompose(
            f"攻击 {target_range}",
            scenario="cyber_red",
        )
        executor = self._create_red_agent_executor(target_range)
        result = self.execute_tree(tree, executor, max_retries=max_retries)

        # 汇聚产出
        assets = result.outputs.get("recon", [])
        findings = result.outputs.get("vuln", [])
        chain = result.outputs.get("exploit", AttackChain(
            chain_id="", target=target_range, steps=[], status="failed"
        ))

        return {
            "assets": assets,
            "findings": findings,
            "chain": chain,
            "goal_result": result,
        }

    def run_blue_chain_with_goal(
        self,
        event_stream: list[dict[str, Any]],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Goal 范式执行蓝队防御链（递归目标分解 + 失败重试）。

        替代 :meth:`run_blue_chain` 的固定模板链，将目标分解为子目标树：
            detector -> triage -> threat_hunt -> ir_planner

        每个子目标由对应 Agent 执行，失败时自动重试。

        Args:
            event_stream: 原始事件流列表。
            max_retries: 子目标失败后的最大重试次数。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` / ``goal_result`` 的字典。
        """
        tree = self.decompose(
            "防御事件流",
            scenario="cyber_blue",
        )
        executor = self._create_blue_agent_executor(event_stream)
        result = self.execute_tree(tree, executor, max_retries=max_retries)

        alerts = result.outputs.get("detect", [])
        triaged = result.outputs.get("triage", alerts)
        hypotheses = result.outputs.get("hunt", [])
        plan = result.outputs.get("respond", ResponsePlan(
            plan_id="", actions=[], confidence=0.0, rollback={}
        ))

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
            "goal_result": result,
        }

    def _create_red_agent_executor(
        self, target_range: str
    ) -> Any:
        """创建红队子目标执行回调。

        返回一个 ``executor(node, context) -> Any`` 回调，根据 ``node.agent_name``
        调用对应的红队 Agent，并将上游产出注入为上下文。

        Args:
            target_range: 目标网络范围。

        Returns:
            执行回调函数。
        """

        def executor(node: GoalNode, context: dict[str, Any]) -> Any:
            """红队子目标执行器。

            根据 node.agent_name 分发到对应 Agent，上游产出从 context 中获取。
            失败时抛出异常，由 :meth:`GoalMode.execute_tree` 捕获并重试。
            """
            agent_name = node.agent_name
            fallback_hint = context.get("_fallback_hint", "")

            if agent_name == "recon":
                prompt = f"Scan target range: {target_range}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                recon_result = self.recon._run(prompt)
                return [
                    Asset(
                        asset_id=a.asset_id,
                        host=a.host,
                        services=a.services,
                        os=a.os,
                        exposure=a.exposure,
                    )
                    for a in recon_result.assets
                ]

            elif agent_name == "vuln_correlator":
                assets = context.get("recon", [])
                assets_desc = json.dumps(
                    [
                        {
                            "asset_id": a.asset_id,
                            "host": a.host,
                            "services": a.services,
                            "os": a.os,
                        }
                        for a in assets
                    ]
                )
                prompt = f"Correlate vulnerabilities for these assets: {assets_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                vuln_result = self.vuln_correlator._run(prompt)
                return [
                    VulnFinding(
                        finding_id=f.finding_id,
                        cve_id=f.cve_id,
                        asset_id=f.asset_id,
                        cvss=f.cvss,
                        attack_surface=f.attack_surface,
                    )
                    for f in vuln_result.findings
                ]

            elif agent_name == "exploit_planner":
                findings = context.get("vuln", [])
                findings_desc = json.dumps(
                    [
                        {
                            "finding_id": f.finding_id,
                            "cve_id": f.cve_id,
                            "asset_id": f.asset_id,
                            "cvss": f.cvss,
                        }
                        for f in findings
                    ]
                )
                prompt = f"Plan exploit chain for: {findings_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                exploit_result = self.exploit_planner._run(prompt)
                return AttackChain(
                    chain_id=exploit_result.chain_id,
                    target=exploit_result.target,
                    steps=[
                        AttackStep(**s.model_dump()) for s in exploit_result.steps
                    ],
                    status=exploit_result.status,
                )

            elif agent_name == "lateral_move":
                from aegisos_agents.action.lateral_move.agent import LateralMoveAgent

                chain = context.get("exploit", AttackChain())
                lateral_agent = LateralMoveAgent(
                    mock=self._mock,
                )
                prompt = f"Plan lateral moves. Chain: {json.dumps(chain.to_dict() if hasattr(chain, 'to_dict') else {})}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                lateral_result = lateral_agent._run(prompt)
                return [
                    AttackStep(**s.model_dump()) for s in lateral_result.steps
                ]

            else:
                raise ValueError(f"Unknown red team agent: {agent_name}")

        return executor

    def _create_blue_agent_executor(
        self, event_stream: list[dict[str, Any]]
    ) -> Any:
        """创建蓝队子目标执行回调。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            执行回调函数。
        """

        def executor(node: GoalNode, context: dict[str, Any]) -> Any:
            """蓝队子目标执行器。"""
            agent_name = node.agent_name
            fallback_hint = context.get("_fallback_hint", "")

            if agent_name == "detector":
                prompt = f"Detect anomalies in: {json.dumps(event_stream)}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                detector_result = self.detector._run(prompt)
                return [
                    Alert(
                        alert_id=a.alert_id,
                        severity=a.severity,
                        src=a.src,
                        dst=a.dst,
                        technique=a.technique,
                        raw=a.raw,
                    )
                    for a in detector_result.alerts
                ]

            elif agent_name == "triage":
                alerts = context.get("detect", [])
                alerts_desc = json.dumps(
                    [
                        {
                            "alert_id": a.alert_id,
                            "severity": a.severity,
                            "src": a.src,
                            "dst": a.dst,
                        }
                        for a in alerts
                    ]
                )
                prompt = f"Triage these alerts: {alerts_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                triage_result = self.triage._run(prompt)
                return [
                    Alert(**t.model_dump()) for t in triage_result.alerts
                ] or alerts

            elif agent_name == "threat_hunt":
                alerts = context.get("triage", context.get("detect", []))
                alerts_desc = json.dumps(
                    [
                        {"alert_id": a.alert_id, "severity": a.severity}
                        for a in alerts
                    ]
                )
                prompt = f"Generate hunting hypotheses for: {alerts_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                hunt_result = self.threat_hunt._run(prompt)
                return [h.model_dump() for h in hunt_result.hypotheses]

            elif agent_name == "ir_planner":
                hypotheses = context.get("hunt", [])
                prompt = f"Plan response for: {json.dumps(hypotheses)}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                ir_result = self.ir_planner._run(prompt)
                return ResponsePlan(
                    plan_id=ir_result.plan_id,
                    actions=[a.model_dump() for a in ir_result.actions],
                    confidence=ir_result.confidence,
                    rollback=ir_result.rollback,
                )

            else:
                raise ValueError(f"Unknown blue team agent: {agent_name}")

        return executor
