from aegisos_agents.memory.working.store import WorkingMemory
from protocol.memory import MemoryPacket


def test_working_add_and_get_preserves_order():
    """写入两条记忆后读取应保持写入时序。"""
    wm = WorkingMemory()
    wm.add(MemoryPacket(session_id="s1", summary="step1"))
    wm.add(MemoryPacket(session_id="s1", summary="step2"))
    stack = wm.get("s1")
    assert [m.summary for m in stack] == ["step1", "step2"]


def test_working_isolates_sessions():
    """不同会话的工作记忆应相互隔离。"""
    wm = WorkingMemory()
    wm.add(MemoryPacket(session_id="s1", summary="a"))
    wm.add(MemoryPacket(session_id="s2", summary="b"))
    assert len(wm.get("s1")) == 1
    assert len(wm.get("s2")) == 1
    assert wm.get("s1")[0].summary == "a"


def test_working_clear_recovers_session():
    """clear 后该会话工作记忆应被回收。"""
    wm = WorkingMemory()
    wm.add(MemoryPacket(session_id="s1", summary="a"))
    wm.clear("s1")
    assert wm.get("s1") == []


def test_working_get_missing_returns_empty():
    """读取不存在的会话应返回空列表而非抛异常。"""
    wm = WorkingMemory()
    assert wm.get("nope") == []
