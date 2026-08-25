# date: 2026-07-06
# dev: myf
"""CyberRuntime 单元测试。

覆盖：run_red_chain / run_blue_chain / run_purple_review 路由、submit 状态变更、
stop / heartbeat 返回值、未知 agent_id 兜底。
"""
from __future__ import annotations

from aegisos_agents.planning.orchestrator import CyberRuntime
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol import Heartbeat, Task, TaskStatus


def test_run_red_chain():
    """run('red_chain', task) 应委托 CyberOrchestrator.run_red_chain。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    task = Task(goal="attack", plan={"target_range": "10.0.0.0/24"})

    result = runtime.run("red_chain", task)

    assert result["agent_id"] == "red_chain"
    assert result["status"] == "completed"
    output = result["output"]
    assert len(output["assets"]) >= 2
    assert len(output["findings"]) >= 1
    assert output["chain"]["chain_id"] == "chain-1"


def test_run_blue_chain():
    """run('blue_chain', task) 应委托 CyberOrchestrator.run_blue_chain。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    events = [{"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    task = Task(goal="defend", plan={"event_stream": events})

    result = runtime.run("blue_chain", task)

    output = result["output"]
    assert len(output["alerts"]) >= 1
    assert output["plan"]["plan_id"] == "rp-1"
    assert len(output["plan"]["actions"]) >= 1


def test_run_purple_review():
    """run('purple_review', task) 应委托 CyberOrchestrator.run_purple_review。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())

    # 先跑红蓝链拿到产物
    red = runtime.run("red_chain", Task(goal="r", plan={"target_range": "10.0.0.0/24"}))
    blue = runtime.run(
        "blue_chain",
        Task(goal="b", plan={"event_stream": [{"event": "brute-force"}]}),
    )

    # 紫队校验：把红蓝产出作为输入
    task = Task(
        goal="purple",
        plan={
            "attack_chain": red["output"]["chain"],
            "response_plan": blue["output"]["plan"],
            "alerts": blue["output"]["alerts"],
        },
    )
    result = runtime.run("purple_review", task)

    output = result["output"]
    assert output["critique"]["valid"] is True
    assert output["review"]["consistent"] is True


def test_submit_marks_task_running():
    """submit 应将任务状态标记为 Running 并填充 plan。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    task = Task(goal="x")

    runtime.submit(task)

    assert task.status == TaskStatus.Running
    assert "steps" in task.plan


def test_stop_returns_true():
    """stop 应返回 True（当前总是成功）。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    assert runtime.stop("recon") is True


def test_heartbeat_returns_healthy():
    """heartbeat 应返回 healthy 状态。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    hb = runtime.heartbeat("recon")

    assert isinstance(hb, Heartbeat)
    assert hb.status == "healthy"
    assert hb.node.node_id == "recon"


def test_unknown_agent_id_returns_placeholder():
    """未知 agent_id 应返回占位结果（不抛异常）。"""
    runtime = CyberRuntime(mock=_CyberMockProvider())
    task = Task(goal="x")

    result = runtime.run("nonexistent", task)

    assert result["status"] == "completed"
    assert "no handler" in result["output"]
