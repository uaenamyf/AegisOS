import pytest

from data.models.vector_store import InMemoryVectorStore, QdrantVectorStore


def test_qdrant_store_missing_client_raises():
    """未安装 qdrant-client 时应抛 RuntimeError（惰性加载）。"""
    vs = QdrantVectorStore(url="http://localhost:6333")
    with pytest.raises(RuntimeError, match="qdrant-client"):
        vs.search([1.0], top_k=1)


def test_add_and_search_ranked():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0], {"task_id": "t1"})
    vs.add("v2", [0.0, 1.0], {"task_id": "t2"})
    hits = vs.search([1.0, 0.0], top_k=2)
    assert [h[0] for h in hits] == ["v1", "v2"]
    assert hits[0][2] > hits[1][2]
    assert hits[0][1] == {"task_id": "t1"}


def test_search_respects_top_k_and_empty_query():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0])
    vs.add("v2", [0.9, 0.1])
    assert len(vs.search([1.0, 0.0], top_k=1)) == 1
    assert vs.search([]) == []


def test_delete_and_count_and_all():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0], {"task_id": "t1"})
    vs.add("v2", [0.0, 1.0], {"task_id": "t2"})
    assert vs.count() == 2
    vs.delete("v1")
    assert vs.count() == 1
    assert [x[0] for x in vs.all()] == ["v2"]
