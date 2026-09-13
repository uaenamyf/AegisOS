# date: 2026-08-01
# dev: myf
"""快照管理器 —— 拓扑/状态时间点固化。

定期拍摄系统全局状态快照，为 replay/monitor 提供时间线数据源。
每条快照以 ``MemoryPacket`` 承载（kind=snapshot），按时间戳排序。
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from protocol.memory import MemoryPacket


class SnapshotManager:
    """快照管理器 —— 全局状态时间点快照。

    以 ``{snapshot_id: MemoryPacket}`` 维护快照集合，支持拍摄、恢复、
    列举与清理。快照数据序列化到 ``MemoryPacket.archive`` 字段。

    Attributes:
        _snapshots: {snapshot_id: MemoryPacket} 快照存储。
        _order: [snapshot_id] 按拍摄时间排序的 ID 列表。
    """

    def __init__(self) -> None:
        """初始化空的快照管理器。"""
        self._snapshots: dict[str, MemoryPacket] = {}
        self._order: list[str] = []

    # ---- 公开接口 ----

    def capture(self, label: str, state: dict | None = None) -> str:
        """拍摄一次全局状态快照。

        Args:
            label: 快照标签，如 ``"after_recon"``。
            state: 可选的全局状态字典（memory_stats / topology_state / recent_decisions）。

        Returns:
            快照唯一标识符（UUID hex）。
        """
        snapshot_id = uuid.uuid4().hex[:12]
        record = {
            "label": label,
            "timestamp": time.monotonic(),
            **(state or {}),
        }
        pkt = MemoryPacket(
            task_id=snapshot_id,
            kind="snapshot",
            archive=record,
        )
        self._snapshots[snapshot_id] = pkt
        self._order.append(snapshot_id)
        return snapshot_id

    def restore(self, snapshot_id: str) -> dict | None:
        """恢复指定快照。

        Args:
            snapshot_id: 快照标识符。

        Returns:
            快照状态字典；不存在返回 ``None``。
        """
        pkt = self._snapshots.get(snapshot_id)
        if pkt is None:
            return None
        return dict(pkt.archive)

    def list_snapshots(self, session_id: str = "") -> list[str]:
        """列举所有快照 ID（按拍摄时间升序）。

        Args:
            session_id: 当前未使用；为未来按会话过滤预留。

        Returns:
            快照 ID 列表。
        """
        return list(self._order)

    def prune(self, session_id: str = "", keep: int = 10) -> None:
        """清理旧快照，仅保留最近 K 个。

        Args:
            session_id: 当前未使用；为未来按会话过滤预留。
            keep: 保留最近 K 个快照，默认 10。
        """
        while len(self._order) > max(keep, 1):
            oldest = self._order.pop(0)
            self._snapshots.pop(oldest, None)

    def stats(self) -> dict:
        """返回快照统计信息。

        Returns:
            含 total_snapshots 的字典。
        """
        return {"total_snapshots": len(self._snapshots)}

    # ---- R-mem: 持久化辅助（供 MemoryPersistence 使用，避免触及私有态）----

    def dump(self) -> dict[str, Any]:
        """导出全部快照（供落盘恢复使用）。

        Returns:
            含 ``snapshots``（{id: MemoryPacket}）与 ``order``（ID 列表）的字典。
        """
        return {
            "snapshots": dict(self._snapshots),
            "order": list(self._order),
        }

    def restore_all(self, data: dict[str, Any]) -> None:
        """从持久化数据重建全部快照（覆盖现有）。

        Args:
            data: ``dump()`` 产出的字典（含 snapshots / order）。
        """
        snaps = data.get("snapshots") or {}
        order = data.get("order") or []
        self._snapshots = {sid: pkt for sid, pkt in snaps.items()}
        keys = set(self._snapshots.keys())
        self._order = [oid for oid in order if oid in keys] + [
            oid for oid in keys if oid not in set(order)
        ]
