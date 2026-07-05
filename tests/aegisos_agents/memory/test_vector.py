from aegisos_agents.memory.vector.store import VectorMemory
from protocol.memory import MemoryPacket


def test_vector_search_returns_most_similar_first():
    """余弦相似度最高的应排在首位。"""
    vm = VectorMemory()
    vm.add(MemoryPacket(task_id="v1", embedding=[1.0, 0.0], summary="east"))
    vm.add(MemoryPacket(task_id="v2", embedding=[0.0, 1.0], summary="north"))
    # 查询向量与 v1 同向，应排第一
    result = vm.search([1.0, 0.0], top_k=2)
    assert result[0].task_id == "v1"


def test_vector_search_respects_top_k():
    """返回条数不应超过 top_k。"""
    vm = VectorMemory()
    vm.add(MemoryPacket(task_id="v1", embedding=[1.0, 0.0]))
    vm.add(MemoryPacket(task_id="v2", embedding=[0.9, 0.1]))
    vm.add(MemoryPacket(task_id="v3", embedding=[0.0, 1.0]))
    assert len(vm.search([1.0, 0.0], top_k=2)) == 2


def test_vector_empty_embedding_not_indexed():
    """空 embedding 的记忆不应被索引。"""
    vm = VectorMemory()
    vm.add(MemoryPacket(task_id="v0", embedding=[]))
    vm.add(MemoryPacket(task_id="v1", embedding=[1.0]))
    assert len(vm) == 1
    assert vm.search([1.0]) != []


def test_vector_empty_query_returns_empty():
    """空查询向量应返回空列表。"""
    vm = VectorMemory()
    vm.add(MemoryPacket(task_id="v1", embedding=[1.0]))
    assert vm.search([]) == []


def test_vector_zero_vector_similarity_is_zero():
    """零向量的相似度应定义为 0，不抛异常。"""
    vm = VectorMemory()
    vm.add(MemoryPacket(task_id="v1", embedding=[0.0, 0.0]))
    result = vm.search([1.0, 0.0])
    assert len(result) == 1  # 仍返回，相似度为 0
