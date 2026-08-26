# date: 2026-08-01
# dev: myf
"""归档记忆存储 —— 冷数据长期存储。

冷热分层：低引用频次的旧经验从 episodic 下沉到本模块长期保存，
支持按 task_id 精确回查、关键词检索、按需回热（defrost）。
纯内存 list 实现，为 H2 持久化预留文件/SQLite 升级路径。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from protocol.memory import MemoryPacket

if TYPE_CHECKING:
    from aegisos_agents.memory.episodic.store import EpisodicMemory


class ArchiveStore:
    """归档记忆存储 —— 冷数据长期存储（H2 持久化预留位）。

    以 ``list[MemoryPacket]`` 维护已归档的冷记忆，支持精确回查、
    关键词检索与回热到情景记忆。

    Attributes:
        _store: 已归档的记忆列表，按写入顺序排列。
    """

    def __init__(self) -> None:
        """初始化空的归档存储。"""
        self._store: list[MemoryPacket] = []

    # ---- 公开接口 ----

    def archive(self, packets: list[MemoryPacket]) -> int:
        """批量归档记忆。

        Args:
            packets: 待归档的记忆列表。

        Returns:
            实际归档的条数。
        """
        count = len(packets)
        self._store.extend(packets)
        return count

    def recall(self, task_id: str) -> MemoryPacket | None:
        """按 task_id 精确回查归档记忆。

        Args:
            task_id: 目标任务标识符。

        Returns:
            匹配的记忆包；未找到返回 ``None``。
        """
        for m in self._store:
            if m.task_id == task_id:
                return m
        return None

    def defrost(self, task_id: str, episodic: EpisodicMemory) -> bool:
        """回热：从归档移回情景记忆。

        找到匹配记忆后从 archive 移除并追加到 episodic。

        Args:
            task_id: 待回热的任务标识符。
            episodic: 目标情景记忆存储。

        Returns:
            回热成功返回 ``True``；未找到目标记忆返回 ``False``。
        """
        for i, m in enumerate(self._store):
            if m.task_id == task_id:
                episodic.add(m)
                del self._store[i]
                return True
        return False

    def search(self, keyword: str) -> list[MemoryPacket]:
        """关键词子串检索归档记忆（大小写不敏感）。

        Args:
            keyword: 检索关键词。

        Returns:
            命中的记忆包列表。
        """
        kw = keyword.lower()
        results: list[MemoryPacket] = []
        for m in self._store:
            if kw in (m.summary or "").lower():
                results.append(m)
        return results

    def size(self) -> int:
        """返回已归档记忆总数。"""
        return len(self._store)
