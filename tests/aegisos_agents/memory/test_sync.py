# date: 2026-08-01
# dev: myf
"""同步模块测试 —— push/pull/merge + 多节点隔离。"""

import time

import pytest

from aegisos_agents.memory.sync.sync import MemorySync
from protocol.memory import MemoryPacket


@pytest.fixture
def sync():
    return MemorySync()


def make_pkt(task_id: str) -> MemoryPacket:
    return MemoryPacket(
        task_id=task_id,
        summary=f"sync test {task_id}",
        compression={"synced_at": time.monotonic()},
    )


def test_register_and_list_nodes(sync):
    """注册节点后可列举。"""
    sync.register_node("edge_01", "edge")
    sync.register_node("cloud_01", "cloud")
    nodes = sync.list_nodes()
    assert len(nodes) == 2
    roles = {n["role"] for n in nodes}
    assert roles == {"edge", "cloud"}


def test_push_and_pull_roundtrip(sync):
    """push→pull 往返数据一致。"""
    sync.register_node("edge_01", "edge")
    pkts = [make_pkt("t1"), make_pkt("t2")]
    count = sync.push("edge_01", pkts)
    assert count == 2
    pulled = sync.pull("edge_01")
    assert len(pulled) == 2
    ids = {p.task_id for p in pulled}
    assert ids == {"t1", "t2"}


# date: 2026-08-06
# dev: czy
# changelog: 改为显式 synced_at 时间戳，消除对 time.sleep 实时差值的依赖（Windows 粗粒度定时器下偶发时序竞态）
def test_pull_since_timestamp(sync):
    """since 时间戳过滤增量。"""
    sync.register_node("edge_01", "edge")
    old_pkt = MemoryPacket(task_id="old", summary="old", compression={"synced_at": 100.0})
    new_pkt = MemoryPacket(task_id="new", summary="new", compression={"synced_at": 200.0})
    sync.push("edge_01", [old_pkt, new_pkt])
    incremental = sync.pull("edge_01", since_timestamp=150.0)
    assert len(incremental) == 1
    assert incremental[0].task_id == "new"


def test_pull_nonexistent_node_returns_empty(sync):
    """拉取未注册节点返回空列表。"""
    assert sync.pull("ghost") == []


def test_merge_dedup_by_task_id(sync):
    """merge 按 task_id 去重，保留时间戳最新的。"""
    local = [make_pkt("t1"), make_pkt("t2")]
    remote = [make_pkt("t2"), make_pkt("t3")]
    merged = sync.merge(local, remote)
    ids = {p.task_id for p in merged}
    assert ids == {"t1", "t2", "t3"}
    assert len(merged) == 3


def test_unregister_node(sync):
    """注销节点后 push 应忽略。"""
    sync.register_node("edge_01", "edge")
    sync.unregister_node("edge_01")
    assert sync.push("edge_01", [make_pkt("t1")]) == 0
    assert sync.list_nodes() == []
