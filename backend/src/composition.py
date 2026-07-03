# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 注册 11 个攻防 Agent + MockRuntime.run() 接入真实攻防 Agent 调用 + 预置 MockProvider 攻防场景响应
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 DI 组合根——装配 DB/仓储/服务/mock agents.api 实现/DI 端口，提供 get_composition 与 FastAPI 依赖提供者
from __future__ import annotations

import contextlib
from typing import Annotated, Any

from fastapi import Depends

from agents.action.critic.agent import CriticAgent
from agents.action.detector.agent import DetectorAgent
from agents.action.exploit_planner.agent import ExploitPlannerAgent
from agents.action.forensics.agent import ForensicsAgent
from agents.action.ir_planner.agent import IRPlannerAgent
from agents.action.lateral_move.agent import LateralMoveAgent
from agents.action.recon.agent import ReconAgent
from agents.action.reviewer.agent import ReviewerAgent
from agents.action.threat_hunt.agent import ThreatHuntAgent
from agents.action.triage.agent import TriageAgent
from agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from agents.tools.llms.base import LLMRequest, LLMResponse
from agents.tools.llms.mock_provider import MockProvider
from backend.src.mappers.database import (
    configure_session_factory,
    create_engine,
    create_session_factory,
    init_db,
)
from backend.src.mappers.repositories import SessionRepository, TaskRepository
from backend.src.services.agent import AgentService
from backend.src.services.graph import GraphService
from backend.src.services.memory import MemoryService
from backend.src.services.ports import (
    PersistencePortImpl,
    SessionPortImpl,
    TaskUpdatePortImpl,
)
from backend.src.services.session import SessionService
from backend.src.services.task import TaskService
from protocol import (
    Agent,
    AgentStatus,
    Event,
    Heartbeat,
    MemoryPacket,
    NodeRef,
    Task,
    TaskStatus,
    ToolCall,
    ToolResult,
)
from protocol.cyber import (
    Alert,
    Asset,
    AttackChain,
    ResponsePlan,
    VulnFinding,
)

# ---------------------------------------------------------------------------
# 攻防 Agent 元数据定义
# ---------------------------------------------------------------------------

_CYBER_AGENT_SPECS: list[dict[str, Any]] = [
    {
        "agent_id": "recon",
        "name": "Recon Agent",
        "role": "recon",
        "capabilities": ["asset-discovery", "port-scan", "service-fingerprint"],
    },
    {
        "agent_id": "vuln_correlator",
        "name": "Vulnerability Correlator",
        "role": "vuln_correlator",
        "capabilities": ["cve-correlation", "cvss-scoring", "attack-surface-mapping"],
    },
    {
        "agent_id": "exploit_planner",
        "name": "Exploit Planner",
        "role": "exploit_planner",
        "capabilities": ["exploit-chain", "attack-graph", "kill-chain"],
    },
    {
        "agent_id": "lateral_move",
        "name": "Lateral Movement Planner",
        "role": "lateral_move",
        "capabilities": ["lateral-movement", "privilege-escalation", "pivot"],
    },
    {
        "agent_id": "detector",
        "name": "Detector Agent",
        "role": "detector",
        "capabilities": ["intrusion-detection", "anomaly-detection", "alerting"],
    },
    {
        "agent_id": "triage",
        "name": "Triage Agent",
        "role": "triage",
        "capabilities": ["alert-triage", "deduplication", "prioritization"],
    },
    {
        "agent_id": "threat_hunt",
        "name": "Threat Hunter",
        "role": "threat_hunt",
        "capabilities": ["threat-hunting", "hypothesis-generation", "attck-mapping"],
    },
    {
        "agent_id": "ir_planner",
        "name": "IR Planner",
        "role": "ir_planner",
        "capabilities": ["incident-response", "containment", "rollback-planning"],
    },
    {
        "agent_id": "forensics",
        "name": "Forensics Agent",
        "role": "forensics",
        "capabilities": ["digital-forensics", "root-cause-analysis", "timeline-reconstruction"],
    },
    {
        "agent_id": "critic",
        "name": "Critic Agent",
        "role": "critic",
        "capabilities": ["adversarial-critique", "red-blue-validation", "attck-compliance"],
    },
    {
        "agent_id": "reviewer-defense",
        "name": "Consistency Reviewer",
        "role": "reviewer",
        "capabilities": ["consistency-review", "artifact-validation", "cross-check"],
    },
]


def _make_cyber_agent(spec: dict[str, Any]) -> Agent:
    """Build a protocol ``Agent`` dataclass from a spec dict."""
    aid = spec["agent_id"]
    return Agent(
        agent_id=aid,
        name=spec["name"],
        role=spec["role"],
        ref=NodeRef(aid, "agent", spec["name"]),
        capabilities=spec["capabilities"],
        status=AgentStatus.Idle,
    )


# ---------------------------------------------------------------------------
# MockProvider 预置攻防场景响应
# ---------------------------------------------------------------------------


def _build_cyber_mock_responses() -> dict[str, str]:
    """Pre-seed MockProvider with realistic cyber-defense JSON responses."""
    import json as _json

    return {
        # --- ReconAgent.scan ---
        "Scan target range: 10.0.0.0/24": _json.dumps(
            {
                "assets": [
                    {
                        "asset_id": "asset-1",
                        "host": "10.0.0.5",
                        "services": ["ssh:22", "http:80"],
                        "os": "Ubuntu 22.04",
                        "exposure": "external",
                    },
                    {
                        "asset_id": "asset-2",
                        "host": "10.0.0.10",
                        "services": ["redis:6379"],
                        "os": "Debian 12",
                        "exposure": "internal",
                    },
                ]
            }
        ),
        # --- DetectorAgent.detect ---
        # prompt includes the event stream JSON; match on prefix
        "Detect anomalies in: ": _json.dumps(
            {
                "alerts": [
                    {
                        "alert_id": "alert-1",
                        "severity": "high",
                        "src": "10.0.0.99",
                        "dst": "10.0.0.5",
                        "technique": "T1110",
                        "raw": {"event": "brute-force"},
                    }
                ]
            }
        ),
        # --- VulnCorrelatorAgent.correlate ---
        "Correlate vulnerabilities for these assets: ": _json.dumps(
            {
                "findings": [
                    {
                        "finding_id": "vuln-1",
                        "cve_id": "CVE-2024-1234",
                        "asset_id": "asset-1",
                        "cvss": 8.1,
                        "attack_surface": "ssh",
                    }
                ]
            }
        ),
        # --- ExploitPlannerAgent.plan ---
        "Plan exploit chain for: ": _json.dumps(
            {
                "chain_id": "chain-1",
                "target": "asset-1",
                "steps": [
                    {
                        "step_id": "step-1",
                        "technique": "T1110",
                        "from_asset": "external",
                        "to_asset": "asset-1",
                        "success": True,
                    }
                ],
                "status": "planned",
            }
        ),
        # --- LateralMoveAgent.plan_moves ---
        "Plan lateral moves. Chain: ": _json.dumps(
            {
                "steps": [
                    {
                        "step_id": "lat-1",
                        "technique": "T1021",
                        "from_asset": "asset-1",
                        "to_asset": "asset-2",
                        "success": True,
                    }
                ]
            }
        ),
        # --- TriageAgent.triage ---
        "Triage these alerts: ": _json.dumps(
            {
                "alerts": [
                    {"alert_id": "alert-1", "severity": "high"},
                ]
            }
        ),
        # --- ThreatHuntAgent.hunt ---
        "Generate hunting hypotheses for: ": _json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis": "Adversary is using stolen credentials for lateral movement",
                        "confidence": 0.82,
                        "technique": "T1078",
                    }
                ]
            }
        ),
        # --- IRPlannerAgent.plan_response ---
        "Plan response for: ": _json.dumps(
            {
                "plan_id": "rp-1",
                "actions": [
                    {
                        "action_id": "act-1",
                        "kind": "isolate",
                        "target": "asset-1",
                        "rationale": "Isolate compromised host",
                    }
                ],
                "confidence": 0.9,
                "rollback": {"enabled": True, "steps": ["reconnect-host", "verify-services"]},
            }
        ),
        # --- ForensicsAgent.investigate ---
        "Investigate: ": _json.dumps(
            {
                "report_id": "forensic-1",
                "root_cause": "SSH brute-force due to weak password policy",
                "timeline": [
                    {"ts": "2026-07-04T10:00Z", "event": "Initial brute-force detected"},
                    {"ts": "2026-07-04T10:05Z", "event": "Successful login from 10.0.0.99"},
                ],
                "recommendations": ["Enforce key-based SSH auth", "Enable fail2ban"],
            }
        ),
        # --- CriticAgent.critique (red side) ---
        "Critique: ": _json.dumps(
            {
                "valid": True,
                "issues": [],
                "severity": "none",
                "suggestion": "Attack chain is valid and follows ATT&CK methodology.",
            }
        ),
        # --- ReviewerAgent.review ---
        "Review consistency: ": _json.dumps(
            {
                "consistent": True,
                "findings": [],
                "overall_assessment": "All artifacts are mutually consistent.",
            }
        ),
    }


class _CyberMockProvider:
    """Wraps :class:`MockProvider` with prefix-based prompt matching.

    The attack-defense agents embed dynamic content (JSON payloads) in their
    prompts, so exact-key matching often fails. This wrapper tries an exact
    match first, then falls back to checking whether any pre-seeded key is a
    prefix of the incoming prompt.
    """

    def __init__(self) -> None:
        self._inner = MockProvider(_build_cyber_mock_responses())

    def complete(self, request: LLMRequest) -> LLMResponse:
        # Try exact match first
        resp = self._inner.complete(request)
        if resp.ok and resp.text and not resp.text.startswith("[mock]"):
            return resp
        # Fallback: prefix match on seeded keys
        for key, text in self._inner._responses.items():
            if request.prompt.startswith(key):
                return LLMResponse(
                    text=text,
                    ok=True,
                    model_id=request.model_id or "mock",
                    usage={
                        "prompt_tokens": len(request.prompt) // 4,
                        "completion_tokens": len(text) // 4,
                    },
                )
        # Final fallback: default mock
        return self._inner.complete(request)


class MockAgentRegistry:
    """Placeholder ``agents.api.AgentRegistryAPI`` — returns canned agents."""

    def __init__(self) -> None:
        # 3 通用 Agent
        self._agents: dict[str, Agent] = {
            "coder": Agent(
                agent_id="coder",
                name="Coder",
                role="coder",
                ref=NodeRef("coder", "agent", "Coder"),
                capabilities=["code", "debug", "test"],
                status=AgentStatus.Idle,
            ),
            "reviewer": Agent(
                agent_id="reviewer",
                name="Reviewer",
                role="reviewer",
                ref=NodeRef("reviewer", "agent", "Reviewer"),
                capabilities=["review", "critique"],
                status=AgentStatus.Idle,
            ),
            "researcher": Agent(
                agent_id="researcher",
                name="Researcher",
                role="researcher",
                ref=NodeRef("researcher", "agent", "Researcher"),
                capabilities=["search", "summarize"],
                status=AgentStatus.Idle,
            ),
        }
        # 11 攻防 Agent
        for spec in _CYBER_AGENT_SPECS:
            agent = _make_cyber_agent(spec)
            self._agents[agent.agent_id] = agent

    def register(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        return agent

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())


class MockRuntime:
    """Placeholder ``agents.api.RuntimeAPI`` — routes cyber-defense agents to real logic."""

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
        task.status = TaskStatus.Running
        task.plan = {"steps": ["analyze", "route", "execute", "verify"]}
        return task

    def run(self, agent_id: str, task: Task) -> Any:
        """Dispatch to real cyber-defense agent logic or return generic mock."""
        goal = task.goal
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
        """Return a mapping of ``agent_id`` → callable handler."""
        from dataclasses import asdict as _asdict

        def _handle_recon(goal: str, payload: dict) -> dict:
            # goal is free-text from the chat; use payload or default if it
            # doesn't look like a target range (CIDR / IP).
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
            from protocol.graph import Graph

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
        return True

    def heartbeat(self, agent_id: str) -> Heartbeat:
        return Heartbeat(node=NodeRef(agent_id, "agent", agent_id), status="healthy")


class MockMemoryAPI:
    """Placeholder ``agents.api.MemoryAPI`` — stores packets in memory."""

    def __init__(self) -> None:
        self._store: dict[str, MemoryPacket] = {}

    def read(self, query: dict[str, Any]) -> MemoryPacket:
        session_id = query.get("session_id", "")
        return self._store.get(session_id, MemoryPacket(session_id=session_id))

    def write(self, packet: MemoryPacket) -> bool:
        self._store[packet.session_id] = packet
        return True

    def retrieve(self, query: dict[str, Any]) -> list[Any]:
        return []


class MockExecutionAPI:
    """Placeholder ``agents.api.ExecutionAPI`` — returns a successful mock ToolResult."""

    def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.call_id, ok=True, output={"mock": True, "name": call.name})


class MockEventBusAPI:
    """Placeholder ``agents.api.EventBusAPI`` — in-memory topic/handler registry."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Any]] = {}
        self._event_log: list[Event] = []

    def publish(self, event: Event) -> None:
        self._event_log.append(event)
        for handler in self._subscriptions.get(event.topic, []):
            with contextlib.suppress(Exception):
                handler(event)

    def subscribe(self, topic: str, handler: Any) -> str:
        self._subscriptions.setdefault(topic, []).append(handler)
        return f"sub:{topic}:{id(handler)}"

    def unsubscribe(self, subscription_id: str) -> bool:
        return True

    def recent_events(self, limit: int = 100) -> list[Event]:
        return list(self._event_log[-limit:])


class Composition:
    """Dependency-Injection composition root wiring the whole backend."""

    def __init__(self, database_url: str | None = None) -> None:
        # --- Persistence ---
        self.engine = create_engine(database_url) if database_url else create_engine()
        self.session_factory = create_session_factory(self.engine)
        configure_session_factory(self.session_factory)
        self.session_repo = SessionRepository(self.session_factory)
        self.task_repo = TaskRepository(self.session_factory)

        # --- Mock agents.api implementations (agents P5 not ready) ---
        self.agent_registry = MockAgentRegistry()
        self.runtime = MockRuntime()
        self.memory_api = MockMemoryAPI()
        self.execution_api = MockExecutionAPI()
        self.event_bus = MockEventBusAPI()

        # --- Services ---
        self.session_service = SessionService(self.session_repo)
        self.task_service = TaskService(self.task_repo, self.runtime)
        self.agent_service = AgentService(self.agent_registry, self.runtime)
        self.memory_service = MemoryService(self.memory_api)
        self.graph_service = GraphService(self.event_bus)

        # --- DI ports (agents.api.ports) implemented by backend ---
        self.persistence_port = PersistencePortImpl(self.task_repo)
        self.session_port = SessionPortImpl(self.session_repo)
        self.task_update_port = TaskUpdatePortImpl(self.task_repo)

    async def startup(self) -> None:
        await init_db(self.engine)

    async def shutdown(self) -> None:
        await self.engine.dispose()


_composition: Composition | None = None


def get_composition() -> Composition:
    """Return the process-wide singleton composition root."""
    global _composition
    if _composition is None:
        _composition = Composition()
    return _composition


def reset_composition(database_url: str | None = None) -> Composition:
    """Recreate the composition root (mainly for tests)."""
    global _composition
    _composition = Composition(database_url=database_url)
    return _composition


# --- FastAPI dependency providers ---


def get_session_service() -> SessionService:
    return get_composition().session_service


def get_task_service() -> TaskService:
    return get_composition().task_service


def get_agent_service() -> AgentService:
    return get_composition().agent_service


def get_memory_service() -> MemoryService:
    return get_composition().memory_service


def get_graph_service() -> GraphService:
    return get_composition().graph_service


def get_event_bus() -> MockEventBusAPI:
    return get_composition().event_bus


def get_execution_api() -> MockExecutionAPI:
    return get_composition().execution_api


# --- Annotated dependency aliases (idiomatic FastAPI DI, avoids B008) ---

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
EventBusDep = Annotated[MockEventBusAPI, Depends(get_event_bus)]
ExecutionApiDep = Annotated[MockExecutionAPI, Depends(get_execution_api)]
