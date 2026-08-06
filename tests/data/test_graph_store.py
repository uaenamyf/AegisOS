from protocol.cyber import Asset

from data.models.graph_store import InMemoryGraphStore


def test_seed_attck_default_loaded():
    """默认构造应预载 ATT&CK 数据集。"""
    gs = InMemoryGraphStore()
    assert 30 <= len(gs.all_techniques()) <= 40
    assert gs.get_technique("T1210") is not None


def test_upsert_get_search_techniques():
    gs = InMemoryGraphStore(seed_attck=False)
    from protocol.memory import MemoryPacket

    gs.upsert_technique(
        "T0000",
        MemoryPacket(task_id="T0000", semantic={"technique_id": "T0000", "name": "Test Tech", "tactic": "test"}),
    )
    assert gs.get_technique("T0000").semantic["name"] == "Test Tech"
    assert len(gs.search_techniques("Test")) == 1


def test_relations_and_related():
    gs = InMemoryGraphStore(seed_attck=True)
    gs.add_relation("T1595", "precedes", "T1592")
    related = gs.related_techniques("T1595")
    assert any(r.task_id == "T1592" for r in related)
    only = gs.related_techniques("T1595", relation="precedes")
    assert all(r.task_id == "T1592" for r in only)


def test_topology_save_get_list():
    gs = InMemoryGraphStore(seed_attck=False)
    assets = [Asset(asset_id="host-a", host="10.0.0.1"), Asset(asset_id="host-b", host="10.0.0.2")]
    gs.save_topology("range-1", assets, [("host-a", "reaches", "host-b")])
    got_assets, got_links = gs.get_topology("range-1")
    assert [a.asset_id for a in got_assets] == ["host-a", "host-b"]
    assert got_links == [("host-a", "reaches", "host-b")]
    assert gs.list_topologies() == ["range-1"]
