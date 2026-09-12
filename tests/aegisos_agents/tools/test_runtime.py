# date: 2026-08-03
# dev: 123 chen
"""Runtime 模块测试 — AgentLifecycle + RuntimeSupervisor。"""
import time

import pytest

from aegisos_agents.tools.runtime.lifecycle import AgentLifecycle, AgentState
from aegisos_agents.tools.runtime.supervisor import RuntimeSupervisor

# ---- AgentLifecycle 测试 ----

@pytest.fixture
def lifecycle():
    return AgentLifecycle()


def test_start_sets_running(lifecycle):
    """start → RUNNING。"""
    state = lifecycle.start("agent_1", "task_1")
    assert state == AgentState.RUNNING


def test_status_after_start(lifecycle):
    """启动后 status 正确反映。"""
    lifecycle.start("agent_1", "task_1")
    status = lifecycle.status("agent_1")
    assert status["state"] == "running"
    assert status["task_id"] == "task_1"


def test_complete_transition(lifecycle):
    """Running → Completed。"""
    lifecycle.start("agent_1", "task_1")
    state = lifecycle.complete("agent_1", {"result": "ok"})
    assert state == AgentState.COMPLETED


def test_suspend_resume_roundtrip(lifecycle):
    """Running → Suspended → Running 往返。"""
    lifecycle.start("agent_1", "task_1")
    assert lifecycle.suspend("agent_1", "memory pressure") == AgentState.SUSPENDED
    status = lifecycle.status("agent_1")
    assert status["suspend_reason"] == "memory pressure"
    assert lifecycle.resume("agent_1") == AgentState.RUNNING


def test_fail_transition(lifecycle):
    """Running → Failed。"""
    lifecycle.start("agent_1", "task_1")
    state = lifecycle.fail("agent_1", "unexpected error")
    assert state == AgentState.FAILED
    status = lifecycle.status("agent_1")
    assert status["error"] == "unexpected error"


def test_heartbeat_updates_timestamp(lifecycle):
    """heartbeat 刷新时间戳并返回 Heartbeat 对象。"""
    lifecycle.start("agent_1", "task_1")
    hb = lifecycle.heartbeat("agent_1")
    assert hb.status == "running"


def test_check_timeout(lifecycle):
    """超时检测：心跳过期后标记 TIMEOUT。"""
    lifecycle.start("agent_1", "task_1")
    # 0.01s 超时确保触发（Windows monotonic 精度约 15ms，先睡 30ms 留出余量）
    time.sleep(0.03)
    assert lifecycle.check_timeout("agent_1", max_sec=0.01) is True
    assert lifecycle.status("agent_1")["state"] == "timeout"


def test_invalid_transition_raises(lifecycle):
    """非法状态转换抛 ValueError。"""
    lifecycle.start("agent_1", "task_1")
    lifecycle.complete("agent_1")
    with pytest.raises(ValueError):
        lifecycle.suspend("agent_1")  # Completed → Suspended 非法


def test_status_unknown_agent(lifecycle):
    """查询未注册 Agent 返回 unknown。"""
    assert lifecycle.status("ghost")["state"] == "unknown"


# ---- RuntimeSupervisor 测试 ----

@pytest.fixture
def supervisor():
    return RuntimeSupervisor()


def test_supervisor_spawn(supervisor):
    """spawn → RUNNING。"""
    state = supervisor.spawn("agent_1", "task_1")
    assert state == AgentState.RUNNING


def test_list_active(supervisor):
    """list_active 返回运行中 Agent 列表。"""
    supervisor.spawn("a1", "t1")
    supervisor.spawn("a2", "t2")
    supervisor.suspend("a2", "testing")
    active = supervisor.list_active()
    assert "a1" in active
    assert "a2" not in active


def test_list_suspended(supervisor):
    """list_suspended 返回挂起 Agent 列表。"""
    supervisor.spawn("a1", "t1")
    supervisor.spawn("a2", "t2")
    supervisor.suspend("a1", "reason")
    assert supervisor.list_suspended() == ["a1"]


def test_kill_agent(supervisor):
    """kill → Failed。"""
    supervisor.spawn("a1", "t1")
    state = supervisor.kill("a1")
    assert state == AgentState.FAILED
    assert supervisor.list_failed() == ["a1"]


def test_stats_aggregates_all(supervisor):
    """stats 聚合各状态数量。"""
    supervisor.spawn("a1", "t1")
    supervisor.spawn("a2", "t2")
    supervisor.suspend("a2", "pause")
    supervisor.complete("a1")
    s = supervisor.stats()
    assert s["completed"] == 1
    assert s["suspended"] == 1
    assert s["total"] == 2
