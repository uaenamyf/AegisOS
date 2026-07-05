# date: 2026-07-05
# dev: myf
# changelog: 从 composition.py 拆出 MockRuntime（含攻防 Agent 分发表）
"""MockRuntime — agents.api.RuntimeAPI 的占位实现，将攻防 Agent 路由到真实逻辑。"""

from __future__ import annotations

from dataclasses import asdict as _asdict
from typing import Any

from aegisos_agents.action.critic.agent import CriticAgent
from aegisos_agents.action.detector.agent import DetectorAgent
from aegisos_agents.action.exploit_planner.agent import ExploitPlannerAgent
from aegisos_agents.action.forensics.agent import ForensicsAgent
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.action.lateral_move.agent import LateralMoveAgent
from aegisos_agents.action.recon.agent import ReconAgent
from aegisos_agents.action.reviewer.agent import ReviewerAgent
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent
from aegisos_agents.action.triage.agent import TriageAgent
from aegisos_agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol import Heartbeat, NodeRef, Task, TaskStatus
from protocol.cyber import Alert, Asset, AttackChain, ResponsePlan, VulnFinding
from protocol.graph import Graph


class MockRuntime:
    """``agents.api.RuntimeAPI`` 的占位实现，将攻防 Agent 路由到真实逻辑。

    内部持有 11 个攻防 Agent 实例（均共享 :class:`_CyberMockProvider`），
    并通过 :meth:`_cyber_dispatch_map` 将 ``agent_id`` 映射到对应的处理函数，
    从而在 mock 环境下复现真实的攻防流程。

    Attributes:
        _provider: 所有攻防 Agent 共享的 LLM mock 提供者。
        _recon/_detector/...: 各攻防 Agent 实例。
    """

    def __init__(self) -> None:
        self._provider = _CyberMockProvider()
        self._recon = ReconAgent(self._provider)
        self._detector = DetectorAgent(self._provider)
        self._critic = CriticAgent(self._provider)
        self._vuln_correlator = VulnCorrelatorAgent(self._provider)
        self._exploit_planner = ExploitPlannerAgent(self._provider)
        self._lateral_move = LateralMoveAgent(self._provider)
        self._triage = TriageAgent(self._provider)
        self._threat_hunt = ThreatHuntAgent(self._provider)
        self._ir_planner = IRPlannerAgent(self._provider)
        self._forensics = ForensicsAgent(self._provider)
        self._reviewer = ReviewerAgent(self._provider)

    def submit(self, task: Task) -> Task:
        """提交任务，标记为 Running 并填充占位 plan。"""
        task.status = TaskStatus.Running
        task.plan = {"steps": ["analyze", "route", "execute", "verify"]}
        return task

    def run(self, agent_id: str, task: Task) -> Any:
        """执行任务，将攻防 Agent 路由到真实逻辑或返回通用 mock 结果。

        Args:
            agent_id: 目标 Agent 唯一标识。
            task: 待执行的任务对象，``payload`` 提供输入数据。

        Returns:
            包含 ``agent_id``、``task_id``、``status``、``output`` 的结果字典。
        """
        goal = task.goal
        # payload 可能为空，兜底为空字典。
        payload = getattr(task, "payload", None) or {}
        cyber_handlers = self._cyber_dispatch_map()
        handler = cyber_handlers.get(agent_id)
        if handler is not None:
            output = handler(goal, payload)
            return {
                "agent_id": agent_id,
                "task_id": task.task_id,
                "status": "completed",
                "output": output,
            }
        return {
            "agent_id": agent_id,
            "task_id": task.task_id,
            "status": "completed",
            "output": f"mock result from {agent_id} for goal: {goal}",
        }

    def _cyber_dispatch_map(self) -> dict[str, Any]:
        """返回 ``agent_id`` -> 处理函数 的映射表。

        Returns:
            ``agent_id`` 到可调用处理器的字典。
        """

        def _handle_recon(goal: str, payload: dict) -> dict:
            target_range = payload.get("target_range")
            if not target_range:
                target_range = (
                    goal if "/" in goal or goal.replace(".", "").isdigit() else "10.0.0.0/24"
                )
            assets = self._recon.scan(target_range)
            return {"target_range": target_range, "assets": [_asdict(a) for a in assets]}

        def _handle_detector(goal: str, payload: dict) -> dict:
            event_stream = payload.get("event_stream", [])
            alerts = self._detector.detect(event_stream)
            return {"alerts": [_asdict(a) for a in alerts]}

        def _handle_vuln_correlator(goal: str, payload: dict) -> dict:
            assets_data = payload.get("assets", [])
            assets = [Asset(**a) if isinstance(a, dict) else a for a in assets_data]
            findings = self._vuln_correlator.correlate(assets)
            return {"findings": [_asdict(f) for f in findings]}

        def _handle_exploit_planner(goal: str, payload: dict) -> dict:
            findings_data = payload.get("findings", [])
            findings = [VulnFinding(**f) if isinstance(f, dict) else f for f in findings_data]
            chain = self._exploit_planner.plan(findings)
            return chain.to_dict()

        def _handle_lateral_move(goal: str, payload: dict) -> dict:
            chain_data = payload.get("attack_chain", {})
            chain = AttackChain.from_dict(chain_data) if chain_data else AttackChain(chain_id="")
            topology = payload.get("topology")
            graph = Graph(nodes={}) if topology is None else Graph(**topology)
            steps = self._lateral_move.plan_moves(chain, graph)
            return {"steps": [_asdict(s) for s in steps]}

        def _handle_triage(goal: str, payload: dict) -> dict:
            alerts_data = payload.get("alerts", [])
            alerts = [Alert(**a) if isinstance(a, dict) else a for a in alerts_data]
            triaged = self._triage.triage(alerts)
            return {"alerts": [_asdict(a) for a in triaged]}

        def _handle_threat_hunt(goal: str, payload: dict) -> dict:
            alerts_data = payload.get("alerts", [])
            alerts = [Alert(**a) if isinstance(a, dict) else a for a in alerts_data]
            hypotheses = self._threat_hunt.hunt(alerts)
            return {"hypotheses": hypotheses}

        def _handle_ir_planner(goal: str, payload: dict) -> dict:
            hypotheses = payload.get("hypotheses", [])
            plan = self._ir_planner.plan_response(hypotheses)
            return _asdict(plan)

        def _handle_forensics(goal: str, payload: dict) -> dict:
            plan_data = payload.get("response_plan", {})
            plan = ResponsePlan(**plan_data) if plan_data else ResponsePlan(plan_id="")
            return self._forensics.investigate(plan)

        def _handle_critic(goal: str, payload: dict) -> dict:
            target = payload.get("target", {})
            side = payload.get("side", "red")
            return self._critic.critique(target, side)

        def _handle_reviewer(goal: str, payload: dict) -> dict:
            artifacts = payload.get("artifacts", {})
            return self._reviewer.review(artifacts)

        return {
            "recon": _handle_recon,
            "detector": _handle_detector,
            "vuln_correlator": _handle_vuln_correlator,
            "exploit_planner": _handle_exploit_planner,
            "lateral_move": _handle_lateral_move,
            "triage": _handle_triage,
            "threat_hunt": _handle_threat_hunt,
            "ir_planner": _handle_ir_planner,
            "forensics": _handle_forensics,
            "critic": _handle_critic,
            "reviewer-defense": _handle_reviewer,
        }

    def stop(self, agent_id: str) -> bool:
        """停止指定 Agent（mock 实现总是返回成功）。"""
        return True

    def heartbeat(self, agent_id: str) -> Heartbeat:
        """返回指定 Agent 的心跳（mock 实现总是返回 healthy）。"""
        return Heartbeat(node=NodeRef(agent_id, "agent", agent_id), status="healthy")
