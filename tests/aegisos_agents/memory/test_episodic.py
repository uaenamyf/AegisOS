from aegisos_agents.memory.episodic.store import EpisodicMemory
from protocol.memory import MemoryPacket


def test_episodic_add_and_all():
    """追加的经验应全部出现在 all() 中且保持顺序。"""
    em = EpisodicMemory()
    em.add(MemoryPacket(task_id="t1", kind="decision", summary="decide A"))
    em.add(MemoryPacket(task_id="t2", kind="normal", summary="scanned"))
    assert len(em) == 2
    assert [m.task_id for m in em.all()] == ["t1", "t2"]


def test_episodic_by_task_found():
    """按 task_id 应能精确回查单条经验。"""
    em = EpisodicMemory()
    em.add(MemoryPacket(task_id="t1", summary="decide A"))
    em.add(MemoryPacket(task_id="t2", summary="scanned"))
    found = em.by_task("t2")
    assert found is not None
    assert found.summary == "scanned"


def test_episodic_by_task_missing_returns_none():
    """回查不存在的 task_id 应返回 None。"""
    em = EpisodicMemory()
    assert em.by_task("nope") is None
