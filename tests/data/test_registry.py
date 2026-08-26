import pytest

from data.models.registry import create_graph_store, create_vector_store
from data.models.vector_store import InMemoryVectorStore


def test_create_vector_store_in_memory():
    vs = create_vector_store("in_memory")
    assert isinstance(vs, InMemoryVectorStore)


def test_create_graph_store_in_memory():
    gs = create_graph_store("in_memory")
    assert 30 <= len(gs.all_techniques()) <= 40  # 默认 seed


def test_create_unknown_mode_raises():
    with pytest.raises(ValueError):
        create_vector_store("unknown")
    with pytest.raises(ValueError):
        create_graph_store("unknown")
