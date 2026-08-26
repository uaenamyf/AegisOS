# date: 2026-08-01
# dev: myf
"""归档模块测试 —— 冷热分层 + 回热 + 关键词检索。"""

import pytest

from aegisos_agents.memory.archive.store import ArchiveStore
from aegisos_agents.memory.episodic.store import EpisodicMemory
from protocol.memory import MemoryPacket


@pytest.fixture
def store():
    return ArchiveStore()


def make_pkt(task_id: str, summary: str = "") -> MemoryPacket:
    return MemoryPacket(task_id=task_id, kind="decision", summary=summary)


def test_archive_returns_count(store):
    """archive 返回归档条数。"""
    count = store.archive([make_pkt("t1", "old exp"), make_pkt("t2", "old exp 2")])
    assert count == 2
    assert store.size() == 2


def test_recall_by_task_id(store):
    """按 task_id 精确回查归档记忆。"""
    store.archive([make_pkt("t1", "old lateral move")])
    pkt = store.recall("t1")
    assert pkt is not None
    assert pkt.summary == "old lateral move"


def test_recall_missing_returns_none(store):
    """回查不存在的归档记忆返回 None。"""
    assert store.recall("nope") is None


def test_defrost_moves_to_episodic(store):
    """回热：从 archive 移除并追加到 episodic。"""
    epi = EpisodicMemory()
    pkt = make_pkt("t1", "valuable old exp")
    store.archive([pkt])
    assert store.size() == 1
    success = store.defrost("t1", epi)
    assert success is True
    assert store.size() == 0
    assert len(epi) == 1
    assert epi.by_task("t1") is not None


def test_search_keyword_in_archive(store):
    """归档记忆支持关键词检索。"""
    store.archive(
        [
            make_pkt("t1", "lateral movement via smb"),
            make_pkt("t2", "port scan detection"),
        ]
    )
    results = store.search("lateral")
    assert len(results) == 1
    assert results[0].task_id == "t1"


def test_search_no_match_returns_empty(store):
    """关键词无匹配返回空列表。"""
    store.archive([make_pkt("t1", "scan")])
    assert store.search("nonexistent") == []
