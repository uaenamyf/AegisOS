# date: 2026-06-27
# dev: myf
"""Backend domain public API.

Other modules import from `backend.api` only — never from internal
routers/services/repositories/models. This achieves decoupling.
"""

from __future__ import annotations

from typing import Protocol

from protocol import Graph, MemoryPacket, Task


class SessionAPI(Protocol):
    def create_session(self, user_id: str) -> str: ...
    def get_session(self, session_id: str) -> dict: ...
    def close_session(self, session_id: str) -> bool: ...


class TaskAPI(Protocol):
    def create_task(
        self, goal: str, session_id: str, payload: dict[str, object] | None = None
    ) -> Task: ...
    def get_task(self, task_id: str) -> Task: ...
    def list_tasks(self, session_id: str) -> list[Task]: ...
    def cancel_task(self, task_id: str) -> bool: ...


class MemoryGatewayAPI(Protocol):
    def read_memory(self, session_id: str) -> MemoryPacket: ...
    def write_memory(self, session_id: str, packet: MemoryPacket) -> bool: ...


class GraphAPI(Protocol):
    def get_graph(self) -> Graph: ...


class EventStreamAPI(Protocol):
    def stream_events(self, session_id: str, handler) -> None: ...


__all__ = [
    "SessionAPI",
    "TaskAPI",
    "MemoryGatewayAPI",
    "GraphAPI",
    "EventStreamAPI",
]
