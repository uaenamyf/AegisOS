# date: 2026-07-05
# dev: myf
# changelog: 从 composition.py 拆出 MockMemoryAPI
"""MockMemoryAPI — agents.api.MemoryAPI 的内存占位实现。"""

from __future__ import annotations

from typing import Any

from protocol import MemoryPacket


class MockMemoryAPI:
    """``agents.api.MemoryAPI`` 的占位实现，在内存中存储 MemoryPacket。"""

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
