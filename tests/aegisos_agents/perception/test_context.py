# date: 2026-08-01
# dev: 123 chen
"""上下文模块测试 —— TokenBudget + ContextManager。"""
import pytest
from aegisos_agents.perception.context.window import TokenBudget
from aegisos_agents.perception.context.manager import Context, ContextManager
from aegisos_agents.memory.memory_store import MemoryStore
from protocol.memory import MemoryPacket


# ---- TokenBudget 测试 ----

def test_token_estimate():
    """estimate 按字符数/4 估算。"""
    tb = TokenBudget()
    assert tb.estimate("hello world") > 0
    assert tb.estimate("") == 1  # 最小为 1


def test_estimate_packets_summaries():
    """estimate_packets 汇总多条记忆的 token。"""
    tb = TokenBudget()
    pkts = [
        MemoryPacket(summary="short"),
        MemoryPacket(summary="longer summary text here"),
    ]
    total = tb.estimate_packets(pkts)
    assert total > 0
    assert total > tb.estimate("short")


def test_trim_within_budget():
    """未超预算时原样返回。"""
    tb = TokenBudget()
    pkts = [MemoryPacket(task_id="t1", summary="hello", recent=True)]
    orig = len(pkts)
    result = tb.trim(pkts, budget=99999)
    assert len(result) == orig


def test_trim_over_budget_keeps_decision_and_recent():
    """超预算时保留 decision 和 recent 记忆。"""
    tb = TokenBudget()
    pkts = []
    for i in range(10):
        pkts.append(MemoryPacket(task_id=f"t{i}", summary=f"noise step {i}"))
    pkts.append(MemoryPacket(task_id="keep", kind="decision", summary="important decision"))
    result = tb.trim(pkts, budget=1)  # 强制触发裁剪
    kinds = [m.kind for m in result]
    assert "decision" in kinds or any(m.task_id == "keep" for m in result)


def test_trim_empty_list():
    """空列表裁剪返回空列表。"""
    tb = TokenBudget()
    assert tb.trim([]) == []


def test_trim_produces_digest():
    """裁剪超预算时产生 truncation digest。"""
    tb = TokenBudget()
    pkts = [
        MemoryPacket(task_id="t1", summary="a" * 100, working={"k": "v"}),
        MemoryPacket(task_id="t2", summary="b" * 100, working={"k": "v"}),
        MemoryPacket(task_id="t3", summary="c" * 100, working={"k": "v"}),
        MemoryPacket(task_id="t4", summary="d" * 100, working={"k": "v"}),
    ]
    # 没有 decision/recent 标记，全部进入 rest → 头尾保留+中间 digest
    result = tb.trim(pkts, budget=1)  # 强制裁剪
    kinds = [m.kind for m in result]
    assert "digest" in kinds  # 产生了摘要


# ---- ContextManager 测试 ----

@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def mgr(store):
    return ContextManager(store)


def test_open_close_lifecycle(mgr):
    """open → 操作 → close 生命周期。"""
    ctx = mgr.open("s1")
    assert ctx.session_id == "s1"
    mgr.close("s1")
    assert mgr.isolate("s1") is None


def test_pack_session_context(mgr, store):
    """pack 从工作记忆拉取并打包上下文。"""
    mgr.open("s1")
    store.write(MemoryPacket(session_id="s1", summary="step1", working={"a": 1}))
    store.write(MemoryPacket(session_id="s1", summary="step2", working={"b": 2}))
    ctx = mgr.pack("s1", budget=4096)
    assert ctx.session_id == "s1"
    assert len(ctx.working_packets) >= 1
    assert ctx.token_usage > 0
    assert ctx.budget_remaining >= 0


def test_switch_session(mgr, store):
    """switch 切换会话上下文。"""
    mgr.open("s1")
    store.write(MemoryPacket(session_id="s1", summary="s1 data"))
    mgr.open("s2")
    store.write(MemoryPacket(session_id="s2", summary="s2 data"))
    ctx = mgr.switch("s1", "s2")
    assert ctx.session_id == "s2"


def test_isolate_session(mgr, store):
    """isolate 隔离单个会话的完整上下文。"""
    mgr.open("s1")
    store.write(MemoryPacket(session_id="s1", summary="isolated", working={"x": 1}))
    ctx = mgr.isolate("s1")
    assert ctx is not None
    assert ctx.session_id == "s1"
    assert len(ctx.working_packets) >= 1
    assert ctx.truncated is False


def test_pack_truncated_flag(mgr, store):
    """超预算时 truncated 标记应为 True。"""
    mgr.open("s1")
    for i in range(20):
        store.write(
            MemoryPacket(session_id="s1", summary="x" * 200, working={"i": i})
        )
    ctx = mgr.pack("s1", budget=1)  # 强制裁剪
    assert ctx.truncated is True
