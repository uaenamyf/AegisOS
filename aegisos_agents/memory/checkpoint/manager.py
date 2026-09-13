# date: 2026-08-01
# dev: myf
"""检查点管理器 —— 任务中断恢复。

维护每个 session 的检查点栈，每 N 步自动保存编排器执行状态，
支持断点恢复与老检查点清理。
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING

from protocol.memory import MemoryPacket

if TYPE_CHECKING:
    from aegisos_agents.memory.memory_store import MemoryStore

# 默认自动保存间隔（步数）
DEFAULT_INTERVAL = 5


class CheckpointManager:
    """检查点管理器 —— 保存/恢复/自动检查点/清理。

    按 session_id 隔离，维护 ``deque[MemoryPacket]`` 检查点栈。
    支持每 N 步自动保存（``maybe_save``）与保留最近 K 个检查点（``prune``）。

    Attributes:
        _checkpoints: {session_id -> deque[MemoryPacket]} 检查点栈。
        _step_counter: {session_id -> int} 步骤计数器。
        _store: MemoryStore 引用，save 时可选 write-through 到情景记忆。
    """

    def __init__(self, store: MemoryStore | None = None) -> None:
        """初始化检查点管理器。

        Args:
            store: 可选的 MemoryStore 引用，save 时同步写入情景记忆。
        """
        self._checkpoints: dict[str, deque[MemoryPacket]] = {}
        self._step_counter: dict[str, int] = {}
        self._store = store

    # ---- 公开接口 ----

    def save(self, session_id: str, state: dict, label: str = "") -> str:
        """保存一个检查点。

        将编排器状态序列化到 ``MemoryPacket.archive`` 字段，记录时间戳与可选标签。

        Args:
            session_id: 所属会话标识符。
            state: 编排器状态字典（step_index / completed_tasks / working_summary / topology_snapshot）。
            label: 可选标签，如 ``"after_scan"``。

        Returns:
            检查点标识符（``"{session_id}_{step_index}"``）。
        """
        checkpoint_id = f"{session_id}_{state.get('step_index', 0)}"
        record = state.copy()
        record["timestamp"] = time.monotonic()
        record["label"] = label
        pkt = MemoryPacket(
            task_id=checkpoint_id,
            session_id=session_id,
            kind="checkpoint",
            archive=record,
            compression={"saved_at": time.monotonic()},
        )
        self._checkpoints.setdefault(session_id, deque()).append(pkt)
        # write-through 到情景记忆（确保持久语义）
        if self._store is not None:
            self._store.write(pkt)
        return checkpoint_id

    def restore(self, session_id: str) -> dict | None:
        """恢复指定会话的最新检查点。

        Args:
            session_id: 目标会话标识符。

        Returns:
            最新检查点的状态字典；不存在时返回 ``None``。
        """
        dq = self._checkpoints.get(session_id)
        if not dq:
            return None
        return dict(dq[-1].archive)

    def list_checkpoints(self, session_id: str) -> list[dict]:
        """列举指定会话的所有检查点（按保存时间升序）。

        Args:
            session_id: 目标会话标识符。

        Returns:
            检查点状态字典列表。
        """
        dq = self._checkpoints.get(session_id)
        if not dq:
            return []
        return [dict(pkt.archive) for pkt in dq]

    def prune(self, session_id: str, keep_last: int = 5) -> None:
        """清理旧检查点，仅保留最近 K 个。

        Args:
            session_id: 目标会话标识符。
            keep_last: 保留最近 K 个检查点，默认 5。
        """
        dq = self._checkpoints.get(session_id)
        if dq is None:
            return
        while len(dq) > max(keep_last, 1):
            dq.popleft()

    # ---- R-mem: 持久化辅助（供 MemoryPersistence 使用，避免触及私有态）----

    def dump(self) -> dict[str, list["MemoryPacket"]]:
        """导出全部检查点（供落盘恢复使用）。

        Returns:
            {session_id: [MemoryPacket]} 检查点映射（副本）。
        """
        return {
            sid: list(dq) for sid, dq in self._checkpoints.items()
        }

    def restore_all(self, data: dict[str, list["MemoryPacket"]]) -> None:
        """从持久化数据重建全部检查点（覆盖现有）。

        Args:
            data: {session_id: [MemoryPacket]} 检查点映射。
        """
        self._checkpoints = {sid: deque(entries) for sid, entries in data.items()}

    def maybe_save(
        self, session_id: str, state: dict, interval: int = DEFAULT_INTERVAL
    ) -> str | None:
        """按步进计数，每 N 步自动保存检查点。

        内部维护 ``_step_counter``，每次调用递增；达到 interval 时调用 ``save()``
        并重置计数器。

        Args:
            session_id: 目标会话标识符。
            state: 编排器当前状态字典。
            interval: 触发保存的步数间隔，默认 5。

        Returns:
            触发保存时返回 checkpoint_id；否则返回 ``None``。
        """
        count = self._step_counter.get(session_id, 0) + 1
        self._step_counter[session_id] = count
        if count % interval == 0:
            return self.save(session_id, state)
        return None
