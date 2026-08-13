# date: 2026-08-01
# dev: myf
"""检查点模块测试 —— 保存/恢复/每 N 步自动/prune 截断。"""

import pytest

from aegisos_agents.memory.checkpoint.manager import CheckpointManager
from aegisos_agents.memory.memory_store import MemoryStore


@pytest.fixture
def mgr():
    store = MemoryStore()
    return CheckpointManager(store)


def test_save_and_restore_roundtrip(mgr):
    """save→restore 往返数据一致。"""
    state = {"step": 3, "completed": ["t1", "t2"], "working_summary": "scan done"}
    mgr.save("s1", state, label="after_scan")
    restored = mgr.restore("s1")
    assert restored is not None
    assert restored["step"] == 3
    assert restored["completed"] == ["t1", "t2"]
    assert restored["label"] == "after_scan"


def test_restore_nonexistent_session_returns_none(mgr):
    """恢复不存在的会话返回 None。"""
    assert mgr.restore("nonexistent") is None


def test_list_checkpoints(mgr):
    """列举检查点按保存顺序排列。"""
    mgr.save("s1", {"step": 1})
    mgr.save("s1", {"step": 2})
    cps = mgr.list_checkpoints("s1")
    assert len(cps) == 2
    assert cps[0]["step"] == 1
    assert cps[1]["step"] == 2


def test_prune_keeps_last_k(mgr):
    """prune 保留最近 K 个检查点。"""
    for i in range(10):
        mgr.save("s1", {"step": i})
    mgr.prune("s1", keep_last=3)
    remaining = mgr.list_checkpoints("s1")
    assert len(remaining) == 3
    steps = [c["step"] for c in remaining]
    assert steps == [7, 8, 9]


def test_maybe_save_triggers_at_interval(mgr):
    """maybe_save 每 N 步触发保存。"""
    for i in range(1, 6):
        result = mgr.maybe_save("s1", {"step": i}, interval=5)
        if i == 5:
            assert result is not None
        else:
            assert result is None
    cps = mgr.list_checkpoints("s1")
    assert len(cps) == 1
    assert cps[0]["step"] == 5


def test_maybe_save_respects_multiple_intervals(mgr):
    """maybe_save 多次区间均应触发。"""
    for i in range(1, 11):
        mgr.maybe_save("s1", {"step": i}, interval=3)
    cps = mgr.list_checkpoints("s1")
    assert len(cps) == 3
    steps = [c["step"] for c in cps]
    assert steps == [3, 6, 9]
