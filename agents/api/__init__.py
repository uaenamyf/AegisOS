# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 重构 agents/api，移除 PlanningAPI 和 PerceptionAPI（内聚为域内部），仅保留外部真正需要的 5 个接口
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 修复接口合理性——RuntimeAPI 加 submit(task)（不指定 agent）；移除 AgentRegistryAPI.invoke（与 Runtime 重叠）；ExecutionAPI 标注直调场景
"""Agents domain public API — minimal external interface.

Only interfaces that other domains (backend) legitimately call are exposed
here. Internal cognitive capabilities (planning/perception) are NOT exposed —
the backend calls RuntimeAPI.submit(task) and the agents domain handles
plan→route→schedule→execute→reflect internally. See
developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md §3.1.

Exposed (5): AgentRegistryAPI · RuntimeAPI · MemoryAPI · EventBusAPI · ExecutionAPI
Internal (not here): PlanningAPI (agents/planning/engine/) · PerceptionAPI (agents/perception/)
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol import (
    Agent,
    Event,
    Heartbeat,
    MemoryPacket,
    Task,
    ToolCall,
    ToolResult,
)

from .ports import PersistencePort, SessionPort, TaskUpdatePort


class AgentRegistryAPI(Protocol):
    def register(self, agent: Agent) -> None: ...
    def get(self, agent_id: str) -> Agent: ...
    def list_agents(self) -> list[Agent]: ...


class MemoryAPI(Protocol):
    def read(self, query: dict) -> MemoryPacket: ...
    def write(self, packet: MemoryPacket) -> bool: ...
    def retrieve(self, query: dict) -> list: ...


class ExecutionAPI(Protocol):
    def execute(self, call: ToolCall) -> ToolResult: ...


class EventBusAPI(Protocol):
    def publish(self, event: Event) -> None: ...
    def subscribe(self, topic: str, handler) -> None: ...


class RuntimeAPI(Protocol):
    def submit(self, task: Task) -> Task: ...
    def run(self, agent_id: str, task: Task) -> Any: ...
    def stop(self, agent_id: str) -> bool: ...
    def heartbeat(self, agent_id: str) -> Heartbeat: ...


__all__ = [
    "AgentRegistryAPI",
    "MemoryAPI",
    "ExecutionAPI",
    "EventBusAPI",
    "RuntimeAPI",
    "PersistencePort",
    "SessionPort",
    "TaskUpdatePort",
]
