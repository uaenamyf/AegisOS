# date: 2026-07-05
# dev: myf
"""MockRuntime — agents.api.RuntimeAPI 的占位实现，将攻防 Agent 路由到真实逻辑。

R4.6 重构：删除 85 行手写 ``_cyber_dispatch_map()``，内部委托
:class:`CyberOrchestrator` 的红蓝紫三条链。保留单 Agent 路由用于
非链式调用场景（如 e2e 测试中单独调用 ``recon`` 等）。

向后兼容：接口签名（``submit`` / ``run`` / ``stop`` / ``heartbeat``）不变。
"""

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
from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol import Heartbeat, NodeRef, Task, TaskStatus
from protocol.cyber import Alert, Asset, AttackChain, ResponsePlan, VulnFinding
from protocol.graph import Graph


class MockRuntime:
    """``agents.api.RuntimeAPI`` 的占位实现，将攻防 Agent 路由到真实逻辑。

    R4.6 重构后：
        - 链式调用（``red_chain`` / ``blue_chain`` / ``purple_review``）委托
          :class:`CyberOrchestrator`（SDK Agent 编排）
        - 单 Agent 调用（如 ``recon`` / ``detector`` 等）保留原有的单 Agent
          路由逻辑（直接调用对应 Agent 类的方法）
        - 删除了原 85 行手写 ``_cyber_dispatch_map()`` 中的链式 handler

    Attributes:
        _provider: 所有攻防 Agent 共享的 LLM mock 提供者。
        _orchestrator: R4.6 引入的 SDK 编排器（处理链式调用）。
        _recon/_detector/...: 各攻防 Agent 实例（处理单 Agent 调用）。
    """

    def __init__(self, orchestrator: CyberOrchestrator | None = None) -> None:
        self._provider = _CyberMockProvider()
        # R4.6/R4.7: CyberOrchestrator 处理链式调用，允许外部注入共享实例
        self._orchestrator = orchestrator or CyberOrchestrator(mock=self._provider)
        # 单 Agent 实例（保留用于非链式调用）
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

        R4.6：链式调用委托 ``CyberOrchestrator``，单 Agent 调用走原路由。

        Args:
            agent_id: 目标 Agent 唯一标识。支持链式 ID：
                ``red_chain`` / ``blue_chain`` / ``purple_review``，
                以及单 Agent ID：``recon`` / ``detector`` / ``vuln_correlator``
                / ``exploit_planner`` / ``lateral_move`` / ``triage``
                / ``threat_hunt`` / ``ir_planner`` / ``forensics``
                / ``critic`` / ``reviewer-defense``。
            task: 待执行的任务对象，``payload`` 提供输入数据。

        Returns:
            包含 ``agent_id``、``task_id``、``status``、``output`` 的结果字典。
        """
        goal = task.goal
        payload = getattr(task, "payload", None) or {}

        # R4.6: 链式调用委托 CyberOrchestrator
        if agent_id == "red_chain":
            target_range = payload.get("target_range", goal if "/" in goal else "10.0.0.0/24")
            output = self._orchestrator.run_red_chain(target_range)
            return self._wrap(agent_id, task.task_id, self._serialize_red(output))

        if agent_id == "blue_chain":
            event_stream = payload.get("event_stream", [])
            output = self._orchestrator.run_blue_chain(event_stream)
            return self._wrap(agent_id, task.task_id, self._serialize_blue(output))

        if agent_id == "purple_review":
            chain_data = payload.get("attack_chain", {})
            chain = (
                AttackChain.from_dict(chain_data)
                if isinstance(chain_data, dict)
                else chain_data
            )
            plan_data = payload.get("response_plan", {})
            plan = (
                ResponsePlan(**plan_data) if isinstance(plan_data, dict) else plan_data
            )
            alerts_data = payload.get("alerts", [])
            alerts = [
                Alert(**a) if isinstance(a, dict) else a for a in alerts_data
            ]
            output = self._orchestrator.run_purple_review(chain, plan, alerts)
            return self._wrap(agent_id, task.task_id, output)

        # 单 Agent 路由（保留原有逻辑）
        cyber_handlers = self._single_agent_dispatch()
        handler = cyber_handlers.get(agent_id)
        if handler is not None:
            output = handler(goal, payload)
            return self._wrap(agent_id, task.task_id, output)

        return self._wrap(
            agent_id, task.task_id, f"mock result from {agent_id} for goal: {goal}"
        )

    def _single_agent_dispatch(self) -> dict[str, Any]:
        """返回单 ``agent_id`` -> 处理函数 的映射表（非链式调用）。

        R4.6：仅保留单 Agent 路由，链式调用已迁移到 ``CyberOrchestrator``。

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

    @staticmethod
    def _wrap(agent_id: str, task_id: str, output: Any) -> dict[str, Any]:
        """包装执行结果为统一响应字典。"""
        return {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "completed",
            "output": output,
        }

    @staticmethod
    def _serialize_red(result: dict) -> dict:
        """序列化红队链产出：dataclass 列表转 dict。"""
        return {
            "assets": [_asdict(a) for a in result["assets"]],
            "findings": [_asdict(f) for f in result["findings"]],
            "chain": result["chain"].to_dict(),
        }

    @staticmethod
    def _serialize_blue(result: dict) -> dict:
        """序列化蓝队链产出：dataclass 列表转 dict。"""
        return {
            "alerts": [_asdict(a) for a in result["alerts"]],
            "triaged": [_asdict(a) for a in result["triaged"]],
            "hypotheses": result["hypotheses"],
            "plan": _asdict(result["plan"]),
        }
