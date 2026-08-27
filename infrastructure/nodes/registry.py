# date: 2026-08-27
# dev: ox-alpha
"""节点注册中心与心跳探活（R5 —— 端边云任务线）。

兑现 `infrastructure/api/__init__.py` 中 `NodeRegistryAPI` Protocol 的三个签名
（register_node / discover_nodes / heartbeat），这是全仓库第一处把该 Protocol
从"仅签名"变为"有实现实体"。

职责：
    - 注册：维护端/边/云三层节点的运行时档案与在线状态。
    - 探活：后台线程按 heartbeat_interval_s 逐节点调用 health()；
      连续 fail_threshold 次失败标记 offline，经 EventBus 广播 NodeStatusChange 事件。
    - 查询：discover_nodes() 返回在线节点（供 R6 派发器过滤），snapshot() 返回全量状态。

设计要点：
    - 假时钟兼容：tick() 方法供测试手动驱动一轮心跳，不依赖真实 sleep。
    - 恢复冷却：offline→online 后 consecutive_failures 清零，防止瞬时抖动。
    - 事件隔离：广播失败不阻塞探活循环（eventbus.handler 异常已被 EventBus 自身隔离）。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from infrastructure.nodes.descriptor import NodeProfile, Tier
from protocol.event import Event, EventType, NodeRef


@dataclass
class _NodeEntry:
    """注册表内部条目：节点实例 + 心跳状态。"""

    profile: NodeProfile
    node: Any  # has health(timeout_s) -> bool
    last_ok_ts: float = 0.0
    consecutive_failures: int = 0
    status: str = "probe"  # probe | online | offline


class _NoopEventBus:
    """无事件总线时静默丢弃事件（不抛异常）。"""

    def publish(self, event: Event) -> None:
        pass

    def subscribe(self, topic: EventType, handler: Any) -> Any:
        return lambda: None


class NodeRegistry:
    """端边云节点注册中心：入表 + 心跳 + 状态广播。

    Attributes:
        heartbeat_interval_s: 心跳探测周期（秒）。
        fail_threshold: 连续失败此次数后标记 offline。
    """

    def __init__(
        self,
        heartbeat_interval_s: float = 15.0,
        fail_threshold: int = 2,
        eventbus: Any = None,
    ) -> None:
        self._entries: dict[str, _NodeEntry] = {}
        self._lock = threading.Lock()
        self.heartbeat_interval_s = heartbeat_interval_s
        self.fail_threshold = fail_threshold
        self._eventbus = eventbus if eventbus is not None else _NoopEventBus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ---- 注册 ----

    def register_node(self, node: Any) -> None:
        """注册或覆盖一个节点。

        Args:
            node: 具有 health(timeout_s) -> bool 和 profile 属性的节点实例。
        """
        profile: NodeProfile = node.profile
        entry = _NodeEntry(profile=profile, node=node, status="probe")
        with self._lock:
            self._entries[profile.node_id] = entry

    # ---- 查询 ----

    def discover_nodes(self, tier: str = "") -> list[dict]:
        """返回在线节点列表（供 R6 派发器过滤离线节点）。

        Args:
            tier: 可选过滤层级（device/edge/cloud），空字符串表示不过滤。

        Returns:
            每个元素为 {node_id, tier, status, ...} 字典。
        """
        result: list[dict] = []
        with self._lock:
            for entry in self._entries.values():
                if tier and str(entry.profile.tier) != tier:
                    continue
                result.append({
                    "node_id": entry.profile.node_id,
                    "tier": str(entry.profile.tier),
                    "status": entry.status,
                    "model_id": entry.profile.model_id,
                    "capabilities": entry.profile.capabilities,
                })
        return result

    def snapshot(self) -> list[dict]:
        """返回所有节点全量状态快照。

        Returns:
            每个元素含 node_id/tier/status/last_ok_ts/consecutive_failures/model_id。
        """
        result: list[dict] = []
        with self._lock:
            for entry in self._entries.values():
                result.append({
                    "node_id": entry.profile.node_id,
                    "tier": str(entry.profile.tier),
                    "status": entry.status,
                    "last_ok_ts": entry.last_ok_ts,
                    "consecutive_failures": entry.consecutive_failures,
                    "model_id": entry.profile.model_id,
                    "capabilities": entry.profile.capabilities,
                })
        return result

    # ---- 心跳 ----

    def heartbeat(self, node_id: str) -> dict:
        """对指定节点执行一次探活（供外部按需调用）。

        Returns:
            {node_id, ok, status, consecutive_failures}。
        """
        with self._lock:
            entry = self._entries.get(node_id)
            if entry is None:
                return {"node_id": node_id, "ok": False, "status": "unknown", "consecutive_failures": 0}
        return self._probe_one(entry)

    def tick(self) -> None:
        """执行一轮心跳（遍历所有节点各探活一次）。"""
        with self._lock:
            entries = list(self._entries.values())
        for entry in entries:
            self._probe_one(entry)

    def _probe_one(self, entry: _NodeEntry) -> dict:
        """对单个节点探活 + 状态机迁移 + 事件广播。"""
        import time as _time
        ok = False
        try:
            ok = entry.node.health(timeout_s=3.0)
        except Exception:  # noqa: BLE001
            ok = False

        old_status = entry.status
        now = _time.time()

        if ok:
            entry.last_ok_ts = now
            if entry.status == "offline":
                entry.status = "online"
                entry.consecutive_failures = 0
            elif entry.status == "probe":
                entry.status = "online"
                entry.consecutive_failures = 0
            else:
                entry.consecutive_failures = 0
        else:
            entry.consecutive_failures += 1
            if entry.consecutive_failures >= self.fail_threshold and entry.status != "offline":
                entry.status = "offline"

        if old_status != entry.status:
            self._broadcast_status_change(entry)

        return {
            "node_id": entry.profile.node_id,
            "ok": ok,
            "status": entry.status,
            "consecutive_failures": entry.consecutive_failures,
        }

    def _broadcast_status_change(self, entry: _NodeEntry) -> None:
        """广播 NodeStatusChange 事件（失败静默，不阻塞探活循环）。"""
        try:
            event = Event(
                event_type=EventType.NodeStatusChange,
                task_id="",
                source=NodeRef(
                    node_id=entry.profile.node_id,
                    node_type=str(entry.profile.tier),
                ),
                payload={
                    "node_id": entry.profile.node_id,
                    "tier": str(entry.profile.tier),
                    "status": entry.status,
                    "consecutive_failures": entry.consecutive_failures,
                },
            )
            self._eventbus.publish(event)
        except Exception:  # noqa: BLE001
            pass

    # ---- 后台线程 ----

    def start_heartbeat_thread(self) -> None:
        """启动后台心跳线程（daemon，15s 间隔）。"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

    def stop_heartbeat_thread(self) -> None:
        """停止后台心跳线程。"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _heartbeat_loop(self) -> None:
        """后台循环：间隔 heartbeat_interval_s 秒执行一轮 tick。"""
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self.heartbeat_interval_s)


__all__ = ["NodeRegistry", "_NodeEntry"]