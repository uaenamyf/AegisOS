from aegisos_agents.memory.memory_store import MemoryStore
from data.api import create_graph_store, create_vector_store
from protocol.memory import MemoryPacket


def test_store_write_routes_to_working_and_episodic_for_decision():
    """write 决策类记忆应同时进入工作记忆与情景记忆。"""
    store = MemoryStore()
    pkt = MemoryPacket(session_id="s1", task_id="t1", kind="decision", summary="isolate host")
    store.write(pkt)
    # 工作记忆有 1 条
    assert len(store.working.get("s1")) == 1
    # 情景记忆有 1 条（决策类路由）
    assert len(store.episodic) == 1


def test_store_write_routes_vector_when_embedding_present():
    """write 携带 embedding 的记忆应索引到向量记忆。"""
    store = MemoryStore()
    store.write(MemoryPacket(task_id="v1", embedding=[1.0, 0.0], summary="vec"))
    assert len(store.vector) == 1


def test_store_write_routes_semantic_when_concept_id_present():
    """write 携带 concept_id 的 semantic 应入知识库。"""
    store = MemoryStore()
    store.write(
        MemoryPacket(
            task_id="CVE-X",
            semantic={"concept_id": "CVE-X", "name": "test vuln"},
        )
    )
    assert store.semantic.get("CVE-X") is not None


def test_store_read_aggregates_session_working_memory():
    """read 应聚合会话工作记忆，合并 working dict 与 summary。"""
    store = MemoryStore()
    store.write(MemoryPacket(session_id="s1", summary="step1", working={"a": 1}))
    store.write(MemoryPacket(session_id="s1", summary="step2", working={"b": 2}))
    pkt = store.read({"session_id": "s1"})
    assert pkt.working == {"a": 1, "b": 2}
    assert "step1" in pkt.summary and "step2" in pkt.summary


def test_store_read_empty_session_returns_empty_packet():
    """read 不存在的会话应返回带 session_id 的空包。"""
    store = MemoryStore()
    pkt = store.read({"session_id": "nope"})
    assert pkt.session_id == "nope"
    assert pkt.working == {}


def test_store_recall_wakes_relevant_episodic():
    """recall 触发词应能唤醒情景记忆中匹配的决策。"""
    store = MemoryStore()
    store.write(MemoryPacket(session_id="s1", task_id="t1", kind="decision", summary="isolate h1"))
    store.write(MemoryPacket(session_id="s1", task_id="t2", kind="normal", summary="scan h2"))
    result = store.recall("isolate")
    ids = [m.task_id for m in result]
    assert "t1" in ids
    # 决策类应排在首位
    assert result[0].kind == "decision"


def test_store_compress_reduces_working_stack():
    """compress 超预算时应压缩工作记忆栈，产生 digest 并替换栈。"""
    store = MemoryStore()
    for i in range(5):
        store.write(
            MemoryPacket(
                session_id="s1",
                task_id=f"t{i}",
                kind="normal",
                summary=f"noise step {i}",
                working={"k": i},
            )
        )
    # 标记最近步为 decision 以验证保留
    store.write(MemoryPacket(session_id="s1", task_id="keep", kind="decision", summary="keep me"))
    compressed = store.compress("s1", budget=1)  # budget=1 强制压缩
    kinds = [m.kind for m in compressed]
    assert "digest" in kinds  # 产生了摘要
    assert "decision" in kinds  # 决策被保留
    # 工作记忆栈已被压缩结果替换
    assert len(store.working.get("s1")) == len(compressed)


def test_store_retrieve_merges_recall_and_knowledge():
    """retrieve 应合并 recaller 唤醒与语义知识库检索（去重）。"""
    store = MemoryStore()
    # 写一条情景经验（含 lateral 关键词）
    store.write(MemoryPacket(task_id="e1", kind="decision", summary="lateral move via ssh"))
    # retrieve 用 keyword 触发，应同时命中情景经验与 ATT&CK 种子（T1210/T1021 含 lateral-movement）
    results = store.retrieve({"trigger": "lateral", "keyword": "lateral"})
    ids = {m.task_id for m in results}
    assert "e1" in ids  # 情景经验命中
    # 至少命中一条 ATT&CK 横向移动知识
    assert any(tid in ids for tid in ("T1210", "T1021"))


def test_store_end_session_recovers_working_keeps_episodic():
    """end_session 应回收工作记忆但保留情景记忆。"""
    store = MemoryStore()
    store.write(MemoryPacket(session_id="s1", task_id="t1", kind="decision", summary="decide"))
    store.end_session("s1")
    assert store.working.get("s1") == []
    assert len(store.episodic) == 1  # 情景记忆保留


def test_store_cognitive_loop_integration():
    """端到端认知循环：写入经验 → recall 唤醒 → compress 压缩 → 再 recall 仍可用。

    这是 B3 的核心验收：压缩工作记忆不影响情景/向量记忆的唤醒能力。
    """
    store = MemoryStore()
    # 推理后写入：一条决策经验 + 一条向量记忆
    store.write(MemoryPacket(task_id="t1", kind="decision", summary="block port 445"))
    store.write(MemoryPacket(task_id="v1", embedding=[1.0, 0.0], summary="block smb"))
    # 推理前 recall：应唤醒历史经验
    assert len(store.recall("block")) >= 1
    # 大量工作记忆后压缩
    for i in range(10):
        store.write(MemoryPacket(session_id="s1", summary=f"step {i}", working={"i": i}))
    store.compress("s1", budget=1)
    # 压缩后情景/向量记忆仍可唤醒（闭环未断）
    assert len(store.recall("block")) >= 1
    assert len(store.vector) == 1


def test_memory_store_backend_injection():
    """MemoryStore 注入 vector/graph 后端后读写检索应工作。"""
    ms = MemoryStore(
        vector_backend=create_vector_store("in_memory"),
        graph_backend=create_graph_store("in_memory", seed_attck=False),
    )
    ms.write(MemoryPacket(task_id="m1", embedding=[1.0, 0.0], summary="vec hit"))
    assert len(ms.vector) == 1
    assert ms.vector.search([1.0, 0.0])[0].task_id == "m1"
    ms.semantic.add(
        "T9999",
        MemoryPacket(
            task_id="T9999",
            summary="kb",
            semantic={"technique_id": "T9999", "name": "KB", "tactic": "test"},
        ),
    )
    assert ms.semantic.get("T9999") is not None


def test_memory_store_default_no_backend_unchanged():
    """不注入后端时行为与现状一致。"""
    ms = MemoryStore()
    ms.write(MemoryPacket(task_id="d1", embedding=[1.0], summary="default"))
    assert len(ms.vector) == 1
    assert ms.semantic.get("T1210") is not None  # 默认种子
