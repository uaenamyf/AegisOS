# date: 2026-08-01
# dev: myf
"""记忆同步 —— 端边云记忆一致性协议骨架。

为端-边-云三层节点的记忆同步提供 push/pull/merge 协议。
当前为进程内 dict 模拟多节点，为 H7 容器化替换 gRPC/WebSocket 预留接口。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


class MemorySync:
    """端边云记忆同步管理器。

    维护多节点注册表，每节点独立存储一段记忆列表。
    同步策略：推模式（push）+ 拉模式（pull）+ 合并去重（merge, last-write-wins）。

    Attributes:
        _nodes: {node_id -> {"role": str, "store": list[MemoryPacket]}} 节点注册表。
    """

    def __init__(self) -> None:
        """初始化空的同步管理器（不预注册节点）。"""
        self._nodes: dict[str, dict] = {}

    # ---- 节点管理 ----

    def register_node(self, node_id: str, role: str) -> None:
        """注册一个同步节点。

        Args:
            node_id: 节点唯一标识（如 ``"edge_01"``）。
            role: 节点角色：``"edge"`` / ``"fog"`` / ``"cloud"``。
        """
        if node_id not in self._nodes:
            self._nodes[node_id] = {"role": role, "store": []}

    def unregister_node(self, node_id: str) -> None:
        """注销一个同步节点并清理其数据。

        Args:
            node_id: 待注销的节点标识符。
        """
        self._nodes.pop(node_id, None)

    def list_nodes(self) -> list[dict]:
        """列举已注册节点。

        Returns:
            节点信息列表，每项含 ``node_id`` 与 ``role``。
        """
        return [{"node_id": nid, "role": info["role"]} for nid, info in self._nodes.items()]

    # ---- 同步操作 ----

    def push(self, node_id: str, packets: list[MemoryPacket]) -> int:
        """推模式：将本地记忆推送到目标节点。

        Args:
            node_id: 目标节点标识符。
            packets: 待推送的记忆列表。

        Returns:
            实际接收的记忆条数；节点未注册时返回 0。
        """
        info = self._nodes.get(node_id)
        if info is None:
            return 0
        info["store"].extend(packets)
        return len(packets)

    def pull(self, node_id: str, since_timestamp: float = 0.0) -> list[MemoryPacket]:
        """拉模式：从目标节点拉取增量记忆。

        Args:
            node_id: 源节点标识符。
            since_timestamp: 增量时间戳，仅拉取 ``synced_at`` 晚于该时间的记忆。

        Returns:
            增量记忆列表；节点未注册返回空列表。
        """
        info = self._nodes.get(node_id)
        if info is None:
            return []
        store: list[MemoryPacket] = info["store"]
        if since_timestamp <= 0.0:
            return list(store)
        return [pkt for pkt in store if pkt.compression.get("synced_at", 0.0) > since_timestamp]

    def merge(
        self,
        local: list[MemoryPacket],
        remote: list[MemoryPacket],
    ) -> list[MemoryPacket]:
        """合并本地与远程记忆，按 task_id 去重（last-write-wins）。

        同一 task_id 的记忆，保留 ``synced_at`` 时间戳最大的一条。

        Args:
            local: 本地记忆列表。
            remote: 远程拉取的增量记忆列表。

        Returns:
            合并去重后的记忆列表。
        """
        merged: dict[str, MemoryPacket] = {}
        for pkt in local + remote:
            tid = pkt.task_id or ""
            if tid not in merged:
                merged[tid] = pkt
            else:
                # last-write-wins
                existing_ts = merged[tid].compression.get("synced_at", 0.0)
                new_ts = pkt.compression.get("synced_at", 0.0)
                if new_ts > existing_ts:
                    merged[tid] = pkt
        return list(merged.values())
