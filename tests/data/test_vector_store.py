from data.models.vector_store import InMemoryVectorStore


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
