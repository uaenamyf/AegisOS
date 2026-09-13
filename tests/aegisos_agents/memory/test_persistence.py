# date: 2026-09-13
# dev: OpenSquilla
# changelog: 新增记忆持久化测试——跨重启恢复决策经验/检查点/快照

"""记忆持久化：save/load 往返，跨实例恢复不可再生记忆。"""

from __future__ import annotations

from aegisos_agents.memory.memory_store import MemoryStore
from protocol.memory import MemoryPacket


def test_persistence_round_trip_restores_longterm(tmp_path):
    """write+checkpoint+snapshot 后 save；新实例 load 应恢复全部长期记忆。"""
    file = tmp_path / "mem.json"

    a = MemoryStore(persistence_file=str(file))
    a.write(
        MemoryPacket(
            session_id="s1",
            task_id="red_decision",
            kind="decision",
            summary="planned red chain for 10.0.0.0/24",
        )
    )
    a.checkpoint.save(
        "s1",
        {"step_index": 3, "round": 3, "drill_id": "drill_x", "convergence_code": "running"},
        label="after_round_3",
    )
    a.snapshot_cycle("drill_x", {"round": 3, "code": "running"})
    assert a.save_to_disk() is True
    assert file.exists()

    # 新实例从磁盘恢复
    b = MemoryStore(persistence_file=str(file))
    assert any(m.task_id == "red_decision" for m in b.episodic.all()), "情景记忆未恢复"
    restored = b.checkpoint.restore("s1")
    assert restored is not None and restored["step_index"] == 3, "检查点未恢复"
    snap_ids = b.snapshot.list_snapshots()
    assert snap_ids and b.snapshot.restore(snap_ids[-1]) is not None, "快照未恢复"


def test_persistence_no_file_is_noop():
    """未启用 persistence_file 的 MemoryStore：save/load 返回 False 且不落盘。"""
    a = MemoryStore()
    assert a.save_to_disk() is False
    assert a.load_from_disk() is False
    assert a.persistence is None