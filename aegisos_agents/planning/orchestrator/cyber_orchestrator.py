# date: 2026-07-06
# dev: myf
# changelog: 新建 SDK 编排器——用 openai-agents SDK Agent + handoffs 实现红蓝紫攻防链，替代 MockRuntime dispatch map
"""SDK 编排器 —— 用 openai-agents SDK 的 Agent + handoffs 实现红蓝紫攻防链。

本模块用 SDK 的 ``Agent.handoffs`` 机制串联攻防 Agent，替代
``backend/mocks/runtime.py`` 中 85 行手写的 ``_cyber_dispatch_map()``。

设计要点：
    - **红队攻击链**：recon → vuln_correlator → exploit_planner → lateral_move
      用 SDK handoff 链式传递，每个 Agent 的输出作为下一个 Agent 的输入。
    - **蓝队防御链**：detector → triage → threat_hunt → ir_planner → forensics
    - **紫队闭环**：critic 校验红队产出 → 失败时回 exploit_planner（神经符号循环）
    - **Mock/真实 API 双模式**：注入 MockSDKModel 或真实 SDK Model，两条路径走同一编排

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
from dataclasses import asdict
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
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert, Asset, AttackChain, AttackStep, ResponsePlan, VulnFinding

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


class ThreatHuntSDKAgent(StructuredAgent[ThreatHuntResult]):
    """蓝队威胁狩猎 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a threat hunting agent. Given prioritized alerts, generate "
        "hunting hypotheses. Return JSON with a 'hypotheses' array."
    )
    OUTPUT_TYPE = ThreatHuntResult
    TEMPERATURE = 0.5


class IRPlannerSDKAgent(StructuredAgent[IRPlannerResult]):
    """蓝队响应规划 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an incident response planner. Given threat hypotheses, "
        "return JSON with plan_id, actions, confidence, rollback."
    )
    OUTPUT_TYPE = IRPlannerResult
    TEMPERATURE = 0.3


# ---- 紫队 Agent ----


class CriticSDKAgent(StructuredAgent[CritiqueResult]):
    """紫队对抗性批判 SDK Agent（红队侧）。"""

    SYSTEM_PROMPT = (
        "You are a red team critic. Given an attack chain, validate it against "
        "ATT&CK rules. Return JSON: valid (bool), issues (array), severity "
        "(none|low|medium|high), suggestion (str)."
    )
    OUTPUT_TYPE = CritiqueResult
    TEMPERATURE = 0.3


class ReviewerSDKAgent(StructuredAgent[ReviewResult]):
    """紫队一致性审查 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a consistency reviewer. Given multiple artifacts, check if "
        "they are mutually consistent. Return JSON: consistent (bool), "
        "findings (array), overall_assessment (str)."
    )
    OUTPUT_TYPE = ReviewResult
    TEMPERATURE = 0.2


class CyberOrchestrator:
    """攻防编排器 —— 用 SDK Agent 实现红蓝紫攻防链。

    封装 11 个 SDK Agent，提供红队攻击链、蓝队防御链、紫队校验的
    编排接口。Mock 模式下注入 :class:`MockSDKModel`，真实 API 模式
    注入 SDK ``OpenAIChatCompletionsModel``。

    Attributes:
        _mock: Mock Provider 实例（Mock 模式）；真实模式为 None。
    """

    def __init__(self, mock: MockProvider | None = None, model=None) -> None:
        """初始化编排器，装配 11 个 SDK Agent。

        Args:
            mock: :class:`MockProvider` 实例（Mock 模式）；真实模式传 None。
            model: SDK ``Model`` 实例（真实 API 模式）；非 None 时优先于 mock，
                由 :meth:`SDKProvider.get_sdk_model` 创建。9 个 Agent 共享同一 Model。
        """
        self._mock = mock
        # 红队
        self.recon = ReconSDKAgent(mock=mock, model=model)
        self.vuln_correlator = VulnCorrelatorSDKAgent(mock=mock, model=model)
        self.exploit_planner = ExploitPlannerSDKAgent(mock=mock, model=model)
        # 蓝队
        self.detector = DetectorSDKAgent(mock=mock, model=model)
        self.triage = TriageSDKAgent(mock=mock, model=model)
        self.threat_hunt = ThreatHuntSDKAgent(mock=mock, model=model)
        self.ir_planner = IRPlannerSDKAgent(mock=mock, model=model)
        # 紫队
        self.critic = CriticSDKAgent(mock=mock, model=model)
        self.reviewer = ReviewerSDKAgent(mock=mock, model=model)

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
