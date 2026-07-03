"""Infrastructure domain public API.

Other modules import from `infrastructure.api` only — never from internal
transport/nodes/delivery. This achieves decoupling.
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol import Message, SyncPacket


class CommunicationAPI(Protocol):
    def send(self, msg: Message) -> bool: ...
    def recv(self, timeout: float = 30.0) -> Message: ...
    def broadcast(self, msg: Message) -> int: ...


class NodeRegistryAPI(Protocol):
    def register_node(self, node_id: str, meta: dict) -> None: ...
    def discover_nodes(self, kind: str = "") -> list: ...
    def heartbeat(self, node_id: str) -> dict: ...


class SyncAPI(Protocol):
    def sync(self, packet: SyncPacket) -> bool: ...
    def resolve_conflict(self, packet: SyncPacket) -> SyncPacket: ...


class DeploymentAPI(Protocol):
    def deploy(self, env: str, config: dict) -> bool: ...
    def rollback(self, version: str) -> bool: ...
    def status(self) -> dict: ...


__all__ = [
    "CommunicationAPI",
    "NodeRegistryAPI",
    "SyncAPI",
    "DeploymentAPI",
]
