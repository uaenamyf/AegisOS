# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 注册 11 个攻防 Agent + MockRuntime.run() 接入真实攻防 Agent 调用 + 预置 MockProvider 攻防场景响应
# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 DI 组合根——装配 DB/仓储/服务/mock agents.api 实现/DI 端口，提供 get_composition 与 FastAPI 依赖提供者
"""依赖注入（DI）组合根。

本模块是 AegisOS 后端的组合根（composition root），负责装配所有运行时依赖：
数据库引擎与仓储、11 个攻防 Agent 的模拟运行时、内存/执行/事件总线等
``agents.api`` 端口的占位实现，以及上层业务服务（Session/Task/Agent/Memory/Graph）。
同时通过 ``Annotated[...Depends(...)]`` 形式暴露 FastAPI 惯用的依赖别名，
供路由层直接注入。
"""
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
# 每个 spec 描述一个攻防 Agent 的 id、显示名、角色与能力标签，供 _make_cyber_agent
# 转换为 protocol.Agent 数据类并注册到 MockAgentRegistry。
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
    """根据 spec 字典构建 protocol ``Agent`` 数据类。

    Args:
        spec: 攻防 Agent 元数据，须包含 ``agent_id``、``name``、``role``、
            ``capabilities`` 字段。

    Returns:
        初始状态为 ``Idle`` 的 :class:`protocol.Agent` 实例。
    """
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
    """预置 MockProvider 的攻防场景 JSON 响应。

    为每个攻防 Agent 的典型 prompt 返回一段结构化的 JSON 文本，覆盖 Recon、
    Detector、VulnCorrelator、ExploitPlanner、LateralMove、Triage、ThreatHunt、
    IRPlanner、Forensics、Critic、Reviewer 等场景。这些响应以 prompt 前缀作为
    键，供 :class:`_CyberMockProvider` 做前缀匹配。

    Returns:
        ``prompt 前缀 -> JSON 响应文本`` 的映射字典。
    """
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
    """对 :class:`MockProvider` 的包装，提供基于前缀的 prompt 匹配能力。

    攻防 Agent 会把动态内容（JSON payload）嵌入到 prompt 中，导致精确匹配
    经常失败。该包装先尝试精确匹配；若未命中（响应以 ``[mock]`` 开头或为空），
    再回退为：检查任一预置 key 是否为输入 prompt 的前缀。

    Attributes:
        _inner: 被包装的 :class:`MockProvider` 实例，持有预置响应表。
    """

    def __init__(self) -> None:
        self._inner = MockProvider(_build_cyber_mock_responses())

    def complete(self, request: LLMRequest) -> LLMResponse:
        """完成一次 LLM 调用，支持精确匹配与前缀回退。

        Args:
            request: LLM 请求对象，至少包含 ``prompt`` 与 ``model_id``。

        Returns:
            匹配命中的 :class:`LLMResponse`；若均未命中则返回 MockProvider
            的默认 mock 响应。
        """
        # 先尝试精确匹配。
        resp = self._inner.complete(request)
        if resp.ok and resp.text and not resp.text.startswith("[mock]"):
            return resp
        # 回退：对预置 key 做前缀匹配（攻防 prompt 含动态 JSON，需前缀匹配）。
        for key, text in self._inner._responses.items():
            if request.prompt.startswith(key):
                # token 用量按字符数粗略估算（每 4 字符约 1 token）。
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
    ""``agents.api.AgentRegistryAPI`` 的占位实现，返回预设的 Agent 列表。

    内置 3 个通用 Agent（coder/reviewer/researcher）与 11 个攻防 Agent。
    攻防 Agent 元数据来自 :data:`_CYBER_AGENT_SPECS`。

    Attributes:
        _agents: ``agent_id -> Agent`` 的内存索引表。
    """

    def __init__(self) -> None:
        # 3 个通用 Agent。
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
        # 11 个攻防 Agent，由 spec 列表批量构建。
        for spec in _CYBER_AGENT_SPECS:
            agent = _make_cyber_agent(spec)
            self._agents[agent.agent_id] = agent

    def register(self, agent: Agent) -> None:
        """注册或覆盖一个 Agent。"""
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> Agent:
        """按 id 查询 Agent。

        Args:
            agent_id: Agent 唯一标识。

        Returns:
            对应的 :class:`Agent` 实例。

        Raises:
            KeyError: 当 ``agent_id`` 不存在时抛出。
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        return agent

    def list_agents(self) -> list[Agent]:
        """返回所有已注册 Agent 的列表。"""
        return list(self._agents.values())


class MockRuntime:
    ""``agents.api.RuntimeAPI`` 的占位实现，将攻防 Agent 路由到真实逻辑。

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

        若 ``agent_id`` 命中攻防分发表，则调用对应 Agent 真实实现并返回其输出；
        否则返回通用的 mock 结果文本。

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

        每个处理函数签名为 ``(goal: str, payload: dict) -> dict``，内部会从
        payload 构造领域对象并调用对应攻防 Agent 的真实实现。

        Returns:
            ``agent_id`` 到可调用处理器的字典。
        """
        from dataclasses import asdict as _asdict

        def _handle_recon(goal: str, payload: dict) -> dict:
            # goal 来自聊天输入；若不像 CIDR/IP 则回退到默认网段。
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
        """停止指定 Agent（mock 实现总是返回成功）。"""
        return True

    def heartbeat(self, agent_id: str) -> Heartbeat:
        """返回指定 Agent 的心跳（mock 实现总是返回 healthy）。"""
        return Heartbeat(node=NodeRef(agent_id, "agent", agent_id), status="healthy")


class MockMemoryAPI:
    ""``agents.api.MemoryAPI`` 的占位实现，在内存中存储 MemoryPacket。"""

    def __init__(self) -> None:
        self._store: dict[str, MemoryPacket] = {}

    def read(self, query: dict[str, Any]) -> MemoryPacket:
        """按 ``session_id`` 读取记忆包。"""
        session_id = query.get("session_id", "")
        return self._store.get(session_id, MemoryPacket(session_id=session_id))

    def write(self, packet: MemoryPacket) -> bool:
        """写入或覆盖记忆包。"""
        self._store[packet.session_id] = packet
        return True

    def retrieve(self, query: dict[str, Any]) -> list[Any]:
        """检索相关记忆（mock 实现始终返回空列表）。"""
        return []


class MockExecutionAPI:
    ""``agents.api.ExecutionAPI`` 的占位实现，返回成功的 mock ToolResult。"""

    def execute(self, call: ToolCall) -> ToolResult:
        """执行工具调用（mock 实现总是返回成功且包含调用名）。"""
        return ToolResult(call_id=call.call_id, ok=True, output={"mock": True, "name": call.name})


class MockEventBusAPI:
    ""``agents.api.EventBusAPI`` 的占位实现，基于内存的 topic/handler 注册表。"""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Any]] = {}
        self._event_log: list[Event] = []

    def publish(self, event: Event) -> None:
        """发布事件：记入日志并调用订阅该 topic 的所有处理器。"""
        self._event_log.append(event)
        for handler in self._subscriptions.get(event.topic, []):
            # 单个 handler 异常不应阻断其他订阅者。
            with contextlib.suppress(Exception):
                handler(event)

    def subscribe(self, topic: str, handler: Any) -> str:
        """订阅指定 topic，返回订阅 ID。"""
        self._subscriptions.setdefault(topic, []).append(handler)
        return f"sub:{topic}:{id(handler)}"

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅（mock 实现总是返回成功）。"""
        return True

    def recent_events(self, limit: int = 100) -> list[Event]:
        """返回最近 ``limit`` 条事件。"""
        return list(self._event_log[-limit:])


class Composition:
    """依赖注入组合根，装配整个后端的运行时依赖。

    在构造时一次性创建并连接：数据库引擎与仓储、``agents.api`` 端口的 mock
    实现、上层业务服务，以及由后端实现的 DI 端口。进程内通过单例
    :func:`get_composition` 访问。

    Attributes:
        engine: SQLAlchemy 异步引擎。
        session_factory: 会话工厂，用于创建 DB 会话。
        session_repo: 会话仓储。
        task_repo: 任务仓储。
        agent_registry: Agent 注册表（mock）。
        runtime: Agent 运行时（mock，含攻防 Agent 调用）。
        memory_api: 记忆 API（mock）。
        execution_api: 工具执行 API（mock）。
        event_bus: 事件总线（mock）。
        session_service: 会话服务。
        task_service: 任务服务。
        agent_service: Agent 服务。
        memory_service: 记忆服务。
        graph_service: 图服务。
        persistence_port: 持久化 DI 端口实现。
        session_port: 会话 DI 端口实现。
        task_update_port: 任务更新 DI 端口实现。
    """

    def __init__(self, database_url: str | None = None) -> None:
        # --- 持久化层 ---
        self.engine = create_engine(database_url) if database_url else create_engine()
        self.session_factory = create_session_factory(self.engine)
        configure_session_factory(self.session_factory)
        self.session_repo = SessionRepository(self.session_factory)
        self.task_repo = TaskRepository(self.session_factory)

        # --- Mock agents.api 实现（agents P5 未就绪） ---
        self.agent_registry = MockAgentRegistry()
        self.runtime = MockRuntime()
        self.memory_api = MockMemoryAPI()
        self.execution_api = MockExecutionAPI()
        self.event_bus = MockEventBusAPI()

        # --- 服务层 ---
        self.session_service = SessionService(self.session_repo)
        self.task_service = TaskService(self.task_repo, self.runtime)
        self.agent_service = AgentService(self.agent_registry, self.runtime)
        self.memory_service = MemoryService(self.memory_api)
        self.graph_service = GraphService(self.event_bus)

        # --- DI 端口（agents.api.ports）由后端实现 ---
        self.persistence_port = PersistencePortImpl(self.task_repo)
        self.session_port = SessionPortImpl(self.session_repo)
        self.task_update_port = TaskUpdatePortImpl(self.task_repo)

    async def startup(self) -> None:
        """启动阶段：初始化数据库（建表）。"""
        await init_db(self.engine)

    async def shutdown(self) -> None:
        """关闭阶段：释放数据库引擎连接池。"""
        await self.engine.dispose()


_composition: Composition | None = None


def get_composition() -> Composition:
    """返回进程级单例组合根。"""
    global _composition
    if _composition is None:
        _composition = Composition()
    return _composition


def reset_composition(database_url: str | None = None) -> Composition:
    """重建组合根（主要用于测试场景）。

    Args:
        database_url: 可选的数据库连接字符串，用于测试隔离。

    Returns:
        新建的 :class:`Composition` 实例。
    """
    global _composition
    _composition = Composition(database_url=database_url)
    return _composition


# --- FastAPI 依赖提供者 ---


def get_session_service() -> SessionService:
    """提供 SessionService 依赖。"""
    return get_composition().session_service


def get_task_service() -> TaskService:
    """提供 TaskService 依赖。"""
    return get_composition().task_service


def get_agent_service() -> AgentService:
    """提供 AgentService 依赖。"""
    return get_composition().agent_service


def get_memory_service() -> MemoryService:
    """提供 MemoryService 依赖。"""
    return get_composition().memory_service


def get_graph_service() -> GraphService:
    """提供 GraphService 依赖。"""
    return get_composition().graph_service


def get_event_bus() -> MockEventBusAPI:
    """提供 EventBus 依赖。"""
    return get_composition().event_bus


def get_execution_api() -> MockExecutionAPI:
    """提供 ExecutionAPI 依赖。"""
    return get_composition().execution_api


# --- Annotated 依赖别名（FastAPI 惯用 DI 写法，避免 B008 告警） ---

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
EventBusDep = Annotated[MockEventBusAPI, Depends(get_event_bus)]
ExecutionApiDep = Annotated[MockExecutionAPI, Depends(get_execution_api)]
