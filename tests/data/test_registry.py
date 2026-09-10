import pytest

from data.models.graph_store import Neo4jGraphStore
from data.models.registry import create_graph_store, create_vector_store
from data.models.vector_store import InMemoryVectorStore, QdrantVectorStore


def test_create_vector_store_in_memory():
    vs = create_vector_store("in_memory")
    assert isinstance(vs, InMemoryVectorStore)


def test_create_graph_store_in_memory():
    gs = create_graph_store("in_memory")
    assert 30 <= len(gs.all_techniques()) <= 40  # 默认 seed


def test_real_storage_adapters_are_lazy_and_do_not_connect_on_construction():
    graph_store = create_graph_store(
        "neo4j", uri="bolt://unreachable-demo-host:7687", user="neo4j", password="demo"
    )
    vector_store = create_vector_store(
        "qdrant", url="http://unreachable-demo-host:6333", collection="demo"
    )

    assert isinstance(graph_store, Neo4jGraphStore)
    assert isinstance(vector_store, QdrantVectorStore)
    assert graph_store._driver is None
    assert vector_store._client is None


def test_create_unknown_mode_raises():
    with pytest.raises(ValueError):
        create_vector_store("unknown")
    with pytest.raises(ValueError):
        create_graph_store("unknown")
