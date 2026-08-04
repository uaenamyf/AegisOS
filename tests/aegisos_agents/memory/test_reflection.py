# date: 2026-08-01
# dev: myf
"""反思模块测试 —— 三维评估评分 + 排序 + 冷热判断。"""
import pytest
from aegisos_agents.memory.reflection.engine import ReflectionEngine
from protocol.memory import MemoryPacket


@pytest.fixture
def engine():
    return ReflectionEngine()


def make_pkt(task_id: str, summary: str) -> MemoryPacket:
    return MemoryPacket(task_id=task_id, kind="decision", summary=summary)


def test_evaluate_returns_float(engine):
    """evaluate 返回 [0, 1] 内的浮点评分。"""
    pkt = make_pkt("t1", "block port 445")
    score = engine.evaluate(pkt)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_tag_outcome_success_scores_higher(engine):
    """标记为 success 的记忆评分应高于 failure。"""
    pkt_success = make_pkt("t1", "block port 445")
    pkt_failure = make_pkt("t2", "failed scan")
    engine.tag_outcome("t1", "success")
    engine.tag_outcome("t2", "failure")
    assert engine.evaluate(pkt_success) > engine.evaluate(pkt_failure)


def test_rank_sorts_by_score_desc(engine):
    """rank 按评分降序排列。"""
    pkts = [make_pkt(f"t{i}", f"summary {i}") for i in range(5)]
    engine.tag_outcome("t0", "success")
    engine.tag_outcome("t4", "failure")
    ranked = engine.rank(pkts)
    assert ranked[0][1] >= ranked[-1][1]
    assert ranked[0][0].task_id == "t0"


def test_record_reference_increments(engine):
    """record_reference 应递增引用计数。"""
    assert engine.get_reference_count("t1") == 0
    engine.record_reference("t1")
    assert engine.get_reference_count("t1") == 1
    engine.record_reference("t1")
    assert engine.get_reference_count("t1") == 2


def test_is_cold(engine):
    """引用为 0 的记忆判断为冷。"""
    assert engine.is_cold("t1") is True
    engine.record_reference("t1")
    assert engine.is_cold("t1") is False


def test_stats_returns_dict(engine):
    """stats 返回评估统计信息。"""
    engine.tag_outcome("t1", "success")
    engine.tag_outcome("t2", "failure")
    engine.tag_outcome("t3", "unknown")
    s = engine.stats()
    assert "total_evaluated" in s
    assert s["total_evaluated"] == 3
    assert s["success_count"] == 1
    assert s["failure_count"] == 1
