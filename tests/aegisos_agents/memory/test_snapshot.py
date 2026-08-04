# date: 2026-08-01
# dev: myf
"""快照模块测试 —— capture/restore/prune/统计。"""
import pytest
from aegisos_agents.memory.snapshot.manager import SnapshotManager


@pytest.fixture
def mgr():
    return SnapshotManager()


def test_capture_and_restore_roundtrip(mgr):
    """capture→restore 往返数据一致。"""
    state = {"episodic_total": 42, "topology": {"nodes": 5, "edges": 8}}
    sid = mgr.capture("phase1_done", state)
    restored = mgr.restore(sid)
    assert restored is not None
    assert restored["label"] == "phase1_done"
    assert restored["episodic_total"] == 42
    assert restored["topology"]["nodes"] == 5


def test_capture_without_state(mgr):
    """无 state 时可正常 capture（仅记录标签与时间戳）。"""
    sid = mgr.capture("empty_snapshot")
    restored = mgr.restore(sid)
    assert restored is not None
    assert restored["label"] == "empty_snapshot"
    assert "timestamp" in restored


def test_restore_nonexistent_returns_none(mgr):
    """恢复不存在的快照返回 None。"""
    assert mgr.restore("nonexistent") is None


def test_list_snapshots(mgr):
    """列举快照 ID 列表。"""
    mgr.capture("s1")
    mgr.capture("s2")
    snaps = mgr.list_snapshots()
    assert len(snaps) == 2


def test_prune_keeps_last_k(mgr):
    """prune 保留最近 K 个快照。"""
    for i in range(15):
        mgr.capture(f"snap_{i}", {"idx": i})
    mgr.prune(keep=5)
    remaining = mgr.list_snapshots()
    assert len(remaining) == 5
    restored = mgr.restore(remaining[-1])
    assert restored["idx"] == 14


def test_stats(mgr):
    """stats 返回快照统计。"""
    mgr.capture("s1", {"nodes": 3})
    mgr.capture("s2", {"nodes": 5})
    s = mgr.stats()
    assert s["total_snapshots"] == 2
