"""R5 节点注册中心与心跳探活 —— 单元测试（假时钟，不真 sleep）。"""

from __future__ import annotations

import time

import pytest

from infrastructure.nodes.descriptor import NodeProfile, Tier
from infrastructure.nodes.registry import NodeRegistry, _NodeEntry
from protocol.event import Event, EventType


# ---- 可控假节点 ----
class FakeNode:
    """可控 health() 返回值的假节点，用于驱动状态迁移。"""

    def __init__(self, profile: NodeProfile, healthy: bool = True):
        self.profile = profile
        self._healthy = healthy
        self.health_calls: int = 0

    def health(self, timeout_s: float = 3.0) -> bool:
        self.health_calls += 1
        return self._healthy

    def set_healthy(self, v: bool) -> None:
        self._healthy = v


def _device_profile(node_id: str = "d1") -> NodeProfile:
    return NodeProfile(
        node_id=node_id, tier=Tier.DEVICE, base_url="http://localhost:11434",
        model_id="tiny", capabilities=["chat"],
    )


def _edge_profile(node_id: str = "e1") -> NodeProfile:
    return NodeProfile(
        node_id=node_id, tier=Tier.EDGE, base_url="http://10.0.0.2:8900",
        model_id="medium", capabilities=["chat", "reasoning"],
    )


def _cloud_profile(node_id: str = "c1") -> NodeProfile:
    return NodeProfile(
        node_id=node_id, tier=Tier.CLOUD, base_url="https://api.example.com",
        provider="openai_api", model_id="large",
        capabilities=["chat", "reasoning", "long_context"],
    )


# ---- 固定装置 ----

@pytest.fixture
def registry() -> NodeRegistry:
    r = NodeRegistry(heartbeat_interval_s=15.0, fail_threshold=2)
    # 不启动后台线程（测试用手动 tick）
    return r


# ---- 正常注册与查询 ----

def test_register_and_discover_all(registry: NodeRegistry):
    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    result = registry.discover_nodes()
    assert len(result) == 1
    assert result[0]["node_id"] == "d1"
    assert result[0]["status"] == "probe"


def test_register_and_discover_by_tier(registry: NodeRegistry):
    registry.register_node(FakeNode(_device_profile("d1")))
    registry.register_node(FakeNode(_edge_profile("e1")))
    assert len(registry.discover_nodes("device")) == 1
    assert len(registry.discover_nodes("edge")) == 1
    assert len(registry.discover_nodes("cloud")) == 0


def test_register_duplicate_overwrites(registry: NodeRegistry):
    n1 = FakeNode(_device_profile("d1"), healthy=True)
    n2 = FakeNode(_device_profile("d1"), healthy=False)
    registry.register_node(n1)
    registry.register_node(n2)
    # 第二次注册覆盖实例
    result = registry.discover_nodes()
    assert len(result) == 1


# ---- 心跳状态迁移 ----

def test_heartbeat_probe_marks_online(registry: NodeRegistry):
    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    registry.tick()  # 首次探活 → online
    snapshot = registry.snapshot()
    assert snapshot[0]["status"] == "online"
    assert snapshot[0]["consecutive_failures"] == 0


def test_heartbeat_offline_after_consecutive_failures(registry: NodeRegistry):
    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    registry.tick()  # online
    d.set_healthy(False)
    registry.tick()  # fail_1
    snapshot = registry.snapshot()
    assert snapshot[0]["status"] == "online"  # 还没到阈值
    assert snapshot[0]["consecutive_failures"] == 1
    registry.tick()  # fail_2 → offline
    snapshot = registry.snapshot()
    assert snapshot[0]["status"] == "offline"
    assert snapshot[0]["consecutive_failures"] == 2


def test_heartbeat_recovery(registry: NodeRegistry):
    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    registry.tick()  # online
    d.set_healthy(False)
    registry.tick()  # fail_1
    registry.tick()  # fail_2 → offline
    d.set_healthy(True)
    registry.tick()  # recovery → online
    snapshot = registry.snapshot()
    assert snapshot[0]["status"] == "online"
    assert snapshot[0]["consecutive_failures"] == 0


# ---- 事件广播 ----

def test_heartbeat_event_broadcast_on_status_change(registry: NodeRegistry):
    from aegisos_agents.planning.engine.eventbus.impl import EventBus

    events: list[Event] = []
    eventbus = EventBus()
    registry = NodeRegistry(heartbeat_interval_s=15.0, fail_threshold=2, eventbus=eventbus)

    def handler(event: Event) -> None:
        events.append(event)

    eventbus.subscribe(EventType.NodeStatusChange, handler)

    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    registry.tick()  # probe → online

    d.set_healthy(False)
    registry.tick()  # fail_1
    registry.tick()  # fail_2 → offline → event

    assert len(events) >= 1
    assert events[-1].payload.get("status") == "offline"


# ---- 快照 ----

def test_snapshot_includes_all_fields(registry: NodeRegistry):
    registry.register_node(FakeNode(_device_profile("d1")))
    registry.tick()
    snap = registry.snapshot()
    assert snap[0]["node_id"] == "d1"
    assert snap[0]["tier"] == "device"
    assert snap[0]["status"] in ("online", "offline", "probe")
    assert "last_ok_ts" in snap[0]
    assert "consecutive_failures" in snap[0]


# ---- 批量注册 ----

def test_register_multiple_and_tick_all(registry: NodeRegistry):
    registry.register_node(FakeNode(_device_profile("d1"), healthy=True))
    registry.register_node(FakeNode(_edge_profile("e1"), healthy=True))
    registry.register_node(FakeNode(_cloud_profile("c1"), healthy=True))
    registry.tick()
    snap = registry.snapshot()
    assert len(snap) == 3
    assert all(s["status"] == "online" for s in snap)


# ---- 心跳计数 ----

def test_health_calls_increment(registry: NodeRegistry):
    d = FakeNode(_device_profile("d1"), healthy=True)
    registry.register_node(d)
    registry.tick()
    registry.tick()
    assert d.health_calls == 2