# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 DI 组合根——装配 DB/仓储/服务/mock agents.api 实现/DI 端口，提供 get_composition 与 FastAPI 依赖提供者
from __future__ import annotations

import contextlib
from typing import Annotated, Any

from fastapi import Depends

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


class MockAgentRegistry:
    """Placeholder ``agents.api.AgentRegistryAPI`` — returns canned agents."""

    def __init__(self) -> None:
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
    """Placeholder ``agents.api.RuntimeAPI`` — returns deterministic mock results."""

    def submit(self, task: Task) -> Task:
        task.status = TaskStatus.Running
        task.plan = {"steps": ["analyze", "route", "execute", "verify"]}
        return task

    def run(self, agent_id: str, task: Task) -> Any:
        return {
            "agent_id": agent_id,
            "task_id": task.task_id,
            "status": "completed",
            "output": f"mock result from {agent_id} for goal: {task.goal}",
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
