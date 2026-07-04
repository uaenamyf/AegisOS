# date: 2026-06-27
# dev: myf
# changelog: 新建 MemoryService（实现 backend.api.MemoryGatewayAPI，委托 agents.api.MemoryAPI mock）
"""Memory 服务层：委托 agents 的 MemoryAPI 实现记忆读写网关。"""

from __future__ import annotations

from agents.api import MemoryAPI
from protocol import MemoryPacket


class MemoryService:
    """实现 ``backend.api.MemoryGatewayAPI``，底层委托 ``agents.api.MemoryAPI``。

    Attributes:
        _memory: agents 提供的记忆 API，负责实际的记忆读写操作。
    """

    def __init__(self, memory_api: MemoryAPI) -> None:
        self._memory = memory_api

    async def read_memory(self, session_id: str) -> MemoryPacket:
        """读取指定会话的记忆包。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            该会话对应的 ``MemoryPacket`` 记忆包。
        """
        return self._memory.read({"session_id": session_id})

    async def write_memory(self, session_id: str, packet: MemoryPacket) -> bool:
        """写入记忆包到指定会话。

        Args:
            session_id: 会话唯一标识符。
            packet: 待写入的记忆包。

        Returns:
            写入成功返回 ``True``，否则返回 ``False``。
        """
        packet.session_id = session_id  # 绑定记忆包到对应会话
        return self._memory.write(packet)
