# date: 2026-09-13
# dev: OpenSquilla
# changelog: 新增确定性文本嵌入器 + auto_embed 向量通道测试

"""轻量确定性文本嵌入：激活向量检索通道。"""

from __future__ import annotations

from aegisos_agents.memory.memory_store import MemoryStore
from aegisos_agents.memory.vector.embedding import HashingEmbedder, embed_text
from protocol.memory import MemoryPacket


def test_embed_text_deterministic_dim_and_norm():
    """嵌入是确定性的、固定维度、L2 单位范数（零范数除外）。"""
    e = HashingEmbedder(dim=64, ngram=2)
    v1 = e.embed("isolate smb port 445")
    v2 = e.embed("isolate smb port 445")
    assert v1 == v2  # 确定性
    assert len(v1) == 64  # 维度固定
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6  # L2 归一化


def test_embed_similar_texts_are_closer():
    """语义相近文本的余弦相似度应高于无关文本（离线近似）。"""
    emb = embed_text
    close = _cosine(emb("block smb port"), emb("block smb port 445"))
    far = _cosine(emb("block smb port"), emb("deploy web dashboard")) or 0.0
    assert close > far, f"close={close} far={far}"


def _cosine(a, b):
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    return dot


def test_auto_embed_off_by_default_preserves_existing():
    """默认 auto_embed=False：无显式 embedding 的记忆不进向量通道。"""
    m = MemoryStore()
    m.write(MemoryPacket(task_id="n1", summary="plain text no embedding"))
    assert len(m.vector) == 0  # 保持既有行为


def test_auto_embed_on_activates_vector_channel():
    """auto_embed=True：写入决策自动生成向量并可经 recall 唤醒。"""
    m = MemoryStore(auto_embed=True)
    m.write(
        MemoryPacket(
            task_id="d1", kind="decision", summary="isolate smb port 445 on host"
        )
    )
    assert len(m.vector) == 1  # 决策被索引进向量通道
    assert len(m.vector.all()[0].embedding) > 0  # 确有嵌入
    hits = m.recall("isolate smb port")
    assert any(x.task_id == "d1" for x in hits)  # 向量通道可召回