# date: 2026-08-01
# dev: myf
"""检索模块测试 —— 三通道混合检索 + RRF 融合。"""
import pytest
from aegisos_agents.memory.semantic.store import SemanticMemory
from aegisos_agents.memory.vector.store import VectorMemory
from aegisos_agents.memory.episodic.store import EpisodicMemory
from aegisos_agents.memory.retrieval.engine import RetrievalEngine, ScoredPacket
from protocol.memory import MemoryPacket


@pytest.fixture
def engine():
    """构建带种子数据的检索引擎。"""
    sem = SemanticMemory(seed=True)
    vec = VectorMemory()
    epi = EpisodicMemory()
    # 情景：2 条经验
    epi.add(MemoryPacket(task_id="e1", kind="decision", summary="lateral move via ssh"))
    epi.add(MemoryPacket(task_id="e2", kind="normal", summary="scan network ports"))
    # 向量：1 条
    vec.add(MemoryPacket(task_id="v1", embedding=[1.0, 0.0, 0.0], summary="block smb port"))
    return RetrievalEngine(vec, sem, epi)


def test_retrieve_keyword_channel_hits(engine):
    """关键词通道：summary 子串匹配生效。"""
    results = engine.retrieve("lateral", channels=["keyword"], top_k=5)
    assert len(results) >= 1
    ids = {s.packet.task_id for s in results}
    assert "e1" in ids


def test_retrieve_vector_channel_hits(engine):
    """向量通道：余弦相似度检索生效。"""
    results = engine.retrieve("block", query_embedding=[0.9, 0.1, 0.0], channels=["vector"], top_k=5)
    assert len(results) >= 1
    ids = {s.packet.task_id for s in results}
    assert "v1" in ids


def test_retrieve_graph_channel_hits(engine):
    """图通道：ATT&CK tactic 关联检索生效。"""
    results = engine.retrieve("lateral", channels=["graph"], top_k=5)
    ids = {s.packet.task_id for s in results}
    assert any(tid in ids for tid in ("T1210", "T1021"))


def test_retrieve_rrf_fusion_dedup(engine):
    """RRF 融合三通道结果并进行去重。"""
    results = engine.retrieve("lateral", query_embedding=[0.9, 0.1, 0.0], top_k=10)
    ids = [s.packet.task_id for s in results]
    assert len(ids) == len(set(ids))
    assert len(results) >= 2


def test_retrieve_empty_query_returns_empty(engine):
    """空查询返回空列表。"""
    results = engine.retrieve("", top_k=5)
    assert results == []


def test_retrieve_scored_packet_structure(engine):
    """ScoredPacket 结构校验。"""
    results = engine.retrieve("lateral", top_k=1)
    assert len(results) == 1
    s = results[0]
    assert isinstance(s, ScoredPacket)
    assert isinstance(s.packet, MemoryPacket)
    assert isinstance(s.score, float)
    assert isinstance(s.channels, list)
    assert s.score > 0
