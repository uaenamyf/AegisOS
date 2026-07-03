# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 修复接口签名与 05_API_SPEC 对齐——create_session 补 user_id→session_id；close_session 补 REST；TaskAPI.create_task 补 session_id；GraphAPI 注释来源
"""Backend domain public API.

Other modules import from `backend.src.api` only — never from internal
controllers/services/mappers/gateway. This achieves decoupling.
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol import Event, Graph, MemoryPacket, Message, Task


class SessionAPI(Protocol):
    def create_session(self, user_id: str) -> str: ...
    def get_session(self, session_id: str) -> dict: ...
    def close_session(self, session_id: str) -> bool: ...


class TaskAPI(Protocol):
    def create_task(self, goal: str, session_id: str) -> Task: ...
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
