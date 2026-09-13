# date: 2026-06-27
# dev: myf
"""Memory 服务层：委托 agents 的 MemoryAPI 实现记忆读写网关。"""

from __future__ import annotations

from aegisos_agents.api import MemoryAPI
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

    # date: 2026-09-13
    # changelog: 新增 stats——暴露记忆子系统可观测统计（供前端 Monitor 面板）
    async def stats(self) -> dict:
        """返回记忆子系统统计。

        委托底层 ``MemoryStore.stats``，暴露各层记忆条数、检查点/快照数、
        持久化与最近决策经验，供前端记忆可视化。

        Returns:
            记忆子系统统计字典。
        """
        s = getattr(self._memory, "stats", None)
        if s is None:
            # 兼容未实现 stats 的 MemoryAPI（如 MockMemoryAPI）
            return {"supported": False}
        return s()
