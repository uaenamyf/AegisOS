"""Backend domain public API.

Other modules import from `backend.api` only — never from internal
controllers/services/mappers/gateway. This achieves decoupling.
"""
from __future__ import annotations

from typing import Any, Protocol

from protocol import Message, Event, Task, MemoryPacket


class SessionAPI(Protocol):
    def create_session(self, user_id: str) -> str: ...
    def get_session(self, session_id: str) -> dict: ...
    def close_session(self, session_id: str) -> bool: ...


class TaskAPI(Protocol):
    def create_task(self, goal: str, session_id: str) -> Task: ...
    def get_task(self, task_id: str) -> Task: ...
    def cancel_task(self, task_id: str) -> bool: ...


class MemoryGatewayAPI(Protocol):
    def read_memory(self, session_id: str) -> MemoryPacket: ...
    def write_memory(self, packet: MemoryPacket) -> bool: ...


class GraphAPI(Protocol):
    def get_graph(self) -> dict: ...
    def subscribe_graph_updates(self, handler) -> None: ...


class EventStreamAPI(Protocol):
    def stream_events(self, session_id: str, handler) -> None: ...
    def send_message(self, msg: Message) -> None: ...


__all__ = [
    "SessionAPI", "TaskAPI", "MemoryGatewayAPI",
    "GraphAPI", "EventStreamAPI",
]
