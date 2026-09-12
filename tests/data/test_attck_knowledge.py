from data.datasets.attck.knowledge import ATTACK_RELATIONS, ATTACK_TECHNIQUES, load_attck_dataset


def test_dataset_has_original_8_seed():
    """扩充数据集必须保留原 8 条种子（兼容现有语义测试）。"""
    for tid in ["T1595", "T1592", "T1210", "T1059", "T1078", "T1046", "T1021", "T1053"]:
        assert tid in ATTACK_TECHNIQUES
        assert ATTACK_TECHNIQUES[tid]["tactic"] is not None


def test_dataset_size_between_30_and_40():
    """数据集规模约 30-40 条。"""
    assert 30 <= len(ATTACK_TECHNIQUES) <= 40


def test_relations_reference_known_techniques():
    """关系边的两端必须引用已知技战术或合法 tactic 节点。"""
    known = set(ATTACK_TECHNIQUES)
    for src, rel, dst in ATTACK_RELATIONS:
        assert rel in ("contains", "precedes", "uses", "targets")
        assert src in known or dst in known


def test_load_attck_dataset_returns_memory_packets():
    """load_attck_dataset 返回 MemoryPacket 列表，语义字段完整。"""
    packets = load_attck_dataset()
    assert len(packets) == len(ATTACK_TECHNIQUES)
    p = next(x for x in packets if x.task_id == "T1210")
    assert p.semantic["technique_id"] == "T1210"
    assert p.semantic["tactic"] == "lateral-movement"


def test_dataset_covers_collection_exfiltration_and_impact_chain():
    assert {"T1560", "T1041", "T1486"}.issubset(ATTACK_TECHNIQUES)
    assert ("T1560", "precedes", "T1041") in ATTACK_RELATIONS
    assert ("T1041", "precedes", "T1486") in ATTACK_RELATIONS
