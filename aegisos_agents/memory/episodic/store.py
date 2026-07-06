# date: 2026-07-06
# dev: myf
"""情景记忆存储模块。

情景记忆记录 Agent 历史任务"经历"：每个完成的任务/决策作为一条
``MemoryPacket``（kind 常为 decision 或 normal）累积，跨会话保留。
编排器在推理前调用 recaller 据触发词从本存储中唤醒相关历史经验，
实现超长程任务的"经验复用"。

设计要点：
    - 纯内存 list，按写入顺序累积；未来可接持久化（archive 子模块）。
    - 决策类记忆（kind=decision）是唤醒时的优先对象（见 recaller）。
    - 支持按 task_id 精确回查单条经验，以及整库枚举供 recaller 扫描。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


class EpisodicMemory:
    """情景记忆存储 —— 跨会话的历史任务经验累积。

    以 ``list[MemoryPacket]`` 维护所有历史经历，支持追加、按 task_id 精确
    查找与整库枚举。recaller 在唤醒时会扫描本存储做关键词匹配。

    Attributes:
        _episodes: 历史经验列表，按写入顺序排列。
    """

    def __init__(self) -> None:
        """初始化空的情景记忆存储。"""
        self._episodes: list[MemoryPacket] = []

    def add(self, packet: MemoryPacket) -> None:
        """追加一条历史经验。

        通常在任务完成或产生决策时调用；packet 的 ``task_id`` 用于后续精确回查。

        Args:
            packet: 历史经验记忆片段，建议填充 summary 与 task_id。
        """
        self._episodes.append(packet)

    def all(self) -> list[MemoryPacket]:
        """返回全部历史经验（按写入顺序）。

        Returns:
            情景记忆列表的副本，供 recaller 扫描；修改副本不影响内部存储。
        """
        return list(self._episodes)

    def by_task(self, task_id: str) -> MemoryPacket | None:
        """按任务 ID 精确回查单条历史经验。

        Args:
            task_id: 目标任务唯一标识符。

        Returns:
            匹配的记忆片段；未找到时返回 ``None``。
        """
        for m in self._episodes:
            if m.task_id == task_id:
                return m
        return None

    def __len__(self) -> int:
        """返回已累积的历史经验条数。"""
        return len(self._episodes)
