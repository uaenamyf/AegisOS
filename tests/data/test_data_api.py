import typing

from data.api import (
    GraphStoreAPI,
    VectorStoreAPI,
    create_graph_store,
    create_vector_store,
    load_attck_dataset,
)


def test_api_exposes_protocols():
    """GraphStoreAPI / VectorStoreAPI 应为 typing.Protocol 子类。"""
    assert isinstance(GraphStoreAPI, typing.Protocol)
    assert isinstance(VectorStoreAPI, typing.Protocol)


def test_api_factories_return_compatible_stores():
    gs = create_graph_store("in_memory")
    vs = create_vector_store("in_memory")
    gs.all_techniques()
    vs.count()
    assert len(load_attck_dataset()) >= 30
