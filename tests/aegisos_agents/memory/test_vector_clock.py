# date: 2026-08-27
# dev: ox-alpha
"""R9 向量时钟 —— 因果序 + 并发冲突测试。

覆盖：
- compare_vc 纯函数：before / after / equal / concurrent
- push 时自动递增源节点 VC 分量并随包携带
- merge 因果覆盖（旧值不被新值覆盖）
- merge 并发冲突 LWW 兜底
- 既有 6 测试不破坏（回归）
"""

from __future__ import annotations

import time

import pytest

from aegisos_agents.memory.sync.sync import MemorySync, compare_vc
from protocol.memory import MemoryPacket


@pytest.fixture
def sync():
    return MemorySync()


# ---------- compare_vc 纯函数 ----------


def test_vc_equal():
    assert compare_vc({"a": 1, "b": 2}, {"a": 1, "b": 2}) == "equal"


def test_vc_before():
    # a 的所有分量 ≤ b，且至少一个严格 <
    assert compare_vc({"a": 1, "b": 2}, {"a": 2, "b": 2}) == "before"


def test_vc_after():
    assert compare_vc({"a": 3, "b": 2}, {"a": 1, "b": 2}) == "after"


def test_vc_concurrent():
    # a 在某分量更大，b 在另一分量更大 → 并发
    assert compare_vc({"a": 2, "b": 1}, {"a": 1, "b": 2}) == "concurrent"


def test_vc_empty_equal():
    assert compare_vc({}, {}) == "equal"


def test_vc_missing_key_treated_as_zero():
    # b 没有 "b" 分量 → 视为 0
    assert compare_vc({"a": 1, "b": 1}, {"a": 1}) == "after"


# ---------- push 自动递增 VC ----------


def test_push_increments_source_vc(sync):
    """push 到节点后，节点的 VC 分量递增。"""
    sync.register_node("edge_01", "edge")
    pkt = MemoryPacket(task_id="t1", summary="hello",
                       compression={"synced_at": 100.0})
    sync.push("edge_01", [pkt])
    pulled = sync.pull("edge_01")
    vc = pulled[0].compression.get("vector_clock", {})
    assert vc.get("edge_01", 0) >= 1


def test_push_multiple_increments_vc(sync):
    """连续 push 多次，VC 递增。"""
    sync.register_node("device_01", "device")
    for i in range(3):
        sync.push("device_01", [MemoryPacket(
            task_id=f"t{i}", summary=f"s{i}",
            compression={"synced_at": float(i)},
        )])
    pulled = sync.pull("device_01")
    vcs = [p.compression.get("vector_clock", {}).get("device_01", 0) for p in pulled]
    assert vcs == sorted(vcs)
    assert vcs[-1] >= 3


# ---------- merge 因果覆盖 ----------


def test_merge_causal_overwrite(sync):
    """因果序：旧值（VC 更小）不覆盖新值。"""
    old_pkt = MemoryPacket(
        task_id="t1", summary="old version",
        compression={"synced_at": 100.0,
                     "vector_clock": {"device": 1, "edge": 0}},
    )
    new_pkt = MemoryPacket(
        task_id="t1", summary="new version",
        compression={"synced_at": 200.0,
                     "vector_clock": {"device": 2, "edge": 0}},
    )
    merged = sync.merge([old_pkt], [new_pkt])
    assert len(merged) == 1
    assert merged[0].summary == "new version"


def test_merge_causal_no_overwrite_by_old(sync):
    """旧值不能覆盖新值，即使 synced_at 更大。"""
    # new_pkt VC 更大（因果更晚），但 synced_at 更小
    new_pkt = MemoryPacket(
        task_id="t1", summary="causally new",
        compression={"synced_at": 100.0,
                     "vector_clock": {"device": 3}},
    )
    old_pkt = MemoryPacket(
        task_id="t1", summary="causally old but late ts",
        compression={"synced_at": 999.0,
                     "vector_clock": {"device": 1}},
    )
    # local=[new], remote=[old] → old 不该覆盖 new
    merged = sync.merge([new_pkt], [old_pkt])
    assert len(merged) == 1
    assert merged[0].summary == "causally new"


# ---------- merge 并发冲突 LWW 兜底 ----------


def test_merge_concurrent_falls_back_to_lww(sync):
    """并发冲突（VC 不可比）→ 按时间戳 LWW 兜底。"""
    pkt_a = MemoryPacket(
        task_id="t1", summary="version A",
        compression={"synced_at": 100.0,
                     "vector_clock": {"device": 2, "edge": 0}},
    )
    pkt_b = MemoryPacket(
        task_id="t1", summary="version B",
        compression={"synced_at": 200.0,
                     "vector_clock": {"device": 1, "edge": 1}},
    )
    # 并发 → 取 synced_at 更大的
    merged = sync.merge([pkt_a], [pkt_b])
    assert len(merged) == 1
    assert merged[0].summary == "version B"


# ---------- 回归：既有行为不破坏 ----------


def test_merge_no_vc_falls_back_to_lww(sync):
    """没有 VC 的包（旧格式兼容）→ 仍走 LWW。"""
    local = [MemoryPacket(task_id="t1", summary="old",
                          compression={"synced_at": 100.0})]
    remote = [MemoryPacket(task_id="t1", summary="new",
                           compression={"synced_at": 200.0})]
    merged = sync.merge(local, remote)
    assert len(merged) == 1
    assert merged[0].summary == "new"
