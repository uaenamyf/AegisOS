# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 MemoryService（实现 backend.api.MemoryGatewayAPI，委托 agents.api.MemoryAPI mock）
from __future__ import annotations

from agents.api import MemoryAPI
from protocol import MemoryPacket


class MemoryService:
    """Implements ``backend.src.api.MemoryGatewayAPI`` backed by ``agents.api.MemoryAPI``."""

    def __init__(self, memory_api: MemoryAPI) -> None:
        self._memory = memory_api

    async def read_memory(self, session_id: str) -> MemoryPacket:
        return self._memory.read({"session_id": session_id})

    async def write_memory(self, session_id: str, packet: MemoryPacket) -> bool:
        packet.session_id = session_id
        return self._memory.write(packet)
