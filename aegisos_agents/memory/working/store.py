# date: 2026-07-06
# dev: myf
"""工作记忆存储模块。

工作记忆是 Agent 认知循环中"当前会话"的临时上下文栈：短时、高带宽、
随会话结束回收。本模块按 ``session_id`` 隔离，维护每个会话的
``MemoryPacket`` 列表，供编排器在推理前读取、推理后写入、上下文超长时压缩。

设计要点：
    - 纯内存实现（进程内 dict），不持久化；会话结束调用 ``clear`` 回收。
    - 按 session 隔离，避免跨会话上下文污染。
    - 写入追加到栈尾，读取返回整栈（保持时序），便于 compactor 按序压缩。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


class WorkingMemory:
    """工作记忆存储 —— 当前会话的临时上下文栈。

    按 ``session_id`` 隔离存储 ``MemoryPacket`` 列表，模拟 Agent 工作记忆的
    短时上下文。写入追加至栈尾，读取按写入时序返回整栈。

    Attributes:
        _store: session_id -> 该会话的工作记忆栈（按写入顺序）。
    """

    def __init__(self) -> None:
        """初始化空的工作记忆存储。"""
        self._store: dict[str, list[MemoryPacket]] = {}

    def add(self, packet: MemoryPacket) -> None:
        """向指定会话的工作记忆栈追加一条记忆。

        若 packet 未填 session_id，则归入空串键（全局上下文）。

        Args:
            packet: 待写入的工作记忆片段，其 ``session_id`` 决定落入哪个会话栈。
        """
        self._store.setdefault(packet.session_id, []).append(packet)

    def get(self, session_id: str) -> list[MemoryPacket]:
        """读取指定会话的完整工作记忆栈（按写入时序）。

        Args:
            session_id: 目标会话标识符。

        Returns:
            该会话的工作记忆列表；会话不存在时返回空列表（不抛异常）。
        """
        return list(self._store.get(session_id, []))

    def clear(self, session_id: str) -> None:
        """回收指定会话的工作记忆（会话结束时调用）。

        Args:
            session_id: 待清理的会话标识符。
        """
        self._store.pop(session_id, None)

    def sessions(self) -> list[str]:
        """枚举当前持有工作记忆的会话标识符列表。

        Returns:
            非空会话的 session_id 列表。
        """
        return [sid for sid in self._store if self._store[sid]]
