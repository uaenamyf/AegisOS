from aegisos_agents.memory.semantic.store import SemanticMemory
from data.api import create_graph_store
from protocol.memory import MemoryPacket


def test_semantic_seeds_attack_knowledge():
    """默认构造应预置 ATT&CK 种子知识。"""
    sm = SemanticMemory()
    assert len(sm) > 0
    # T1210 横向移动应在种子中
    assert sm.get("T1210") is not None
    assert sm.get("T1210").semantic["tactic"] == "lateral-movement"


def test_semantic_get_missing_returns_none():
    """查询不存在的概念 ID 应返回 None。"""
    sm = SemanticMemory(seed=False)
    assert sm.get("T9999") is None


def test_semantic_search_by_keyword_hits():
    """关键词检索应在 semantic 字段值与 summary 中命中。"""
    sm = SemanticMemory(seed=False)
    sm.add(
        "C1",
        MemoryPacket(
            task_id="C1",
            summary="CVE-2021-44228 log4j",
            semantic={"concept_id": "C1", "name": "Log4Shell"},
        ),
    )
    # 命中 summary
    assert len(sm.search("log4j")) == 1
    # 命中 semantic 字段值
    assert len(sm.search("log4shell")) == 1


def test_semantic_search_no_match_returns_empty():
    """无命中时返回空列表。"""
    sm = SemanticMemory(seed=False)
    sm.add("C1", MemoryPacket(task_id="C1", summary="alpha"))
    assert sm.search("zzz") == []


def test_semantic_graph_backend_delegates():
    """提供 graph_backend 时 get/search/all/len 应委托后端。"""
    backend = create_graph_store("in_memory", seed_attck=False)
    sm = SemanticMemory(seed=False, graph_backend=backend)
    sm.add(
        "T0000",
        MemoryPacket(
            task_id="T0000",
            summary="probe",
            semantic={"technique_id": "T0000", "name": "Probe", "tactic": "test"},
        ),
    )
    assert sm.get("T0000") is not None
    assert len(sm.search("probe")) == 1
    assert len(sm) == 1


def test_semantic_graph_backend_seeds_when_empty():
    """graph_backend 为空且 seed=True 时应从数据集预载。"""
    backend = create_graph_store("in_memory", seed_attck=False)
    sm = SemanticMemory(seed=True, graph_backend=backend)
    assert len(sm) >= 30
