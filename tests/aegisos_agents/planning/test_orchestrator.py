# date: 2026-07-06
# dev: myf
"""Orchestrator 单元测试。

覆盖：一站式 execute（红队链）、execute_plan（紫队并行）、上游产出注入、
事件发布、context 传递、plan 与 tasks 数量不一致报错。
"""
from __future__ import annotations

from aegisos_agents.planning.engine.eventbus import EventBus
from aegisos_agents.planning.engine.workflow import WorkflowStatus
from aegisos_agents.planning.orchestrator import Orchestrator
from protocol.event import EventType
from protocol.scheduler import Plan, Task


class _StubRuntime:
    """记录调用的桩 runtime，供断言 agent_id 与 upstream 传递。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, agent_id: str, task: Task) -> dict:
        upstream = task.plan.get("upstream", {}) if task.plan else {}
        self.calls.append((agent_id, dict(upstream)))
        return {"agent_id": agent_id, "output": f"{agent_id}_done"}


def test_execute_cyber_red_chain():
    """execute 一站式编排红队链，4 节点应按序执行。"""
    runtime = _StubRuntime()
    orchestrator = Orchestrator()

    result = orchestrator.execute(
        goal="攻击 10.0.0.0/24",
        runtime=runtime,
        scenario="cyber_red",
        context={"target_range": "10.0.0.0/24"},
    )

    assert result.success
    # 4 个节点都成功
    assert len(result.node_outputs) == 4
    # 按拓扑序执行：recon 最先，无上游
    assert runtime.calls[0][0] == "recon"
    assert runtime.calls[0][1].get("target_range") == "10.0.0.0/24"
    # vuln_correlator 的上游应含 recon 的产出
    assert runtime.calls[1][0] == "vuln_correlator"
    assert "recon" in runtime.calls[1][1]
    # 最后是 lateral_move
    assert runtime.calls[-1][0] == "lateral_move"


def test_execute_plan_cyber_purple_parallel():
    """execute_plan 紫队并行：critic 与 reviewer 无依赖，可并行。"""
    runtime = _StubRuntime()
    planner_plan = Orchestrator()._planner.plan("紫队", scenario="cyber_purple")
    orchestrator = Orchestrator()

    result = orchestrator.execute_plan(planner_plan, runtime)

    assert result.success
    assert set(result.node_outputs.keys()) == {"critic", "reviewer"}
    # 两者都无上游依赖
    assert all(upstream == {} for _, upstream in runtime.calls)


def test_eventbus_receives_lifecycle_events():
    """注入 EventBus 后应收到每个节点的 Start + Finish 事件。"""
    runtime = _StubRuntime()
    bus = EventBus()
    orchestrator = Orchestrator(eventbus=bus)

    orchestrator.execute(
        goal="test",
        runtime=runtime,
        scenario="cyber_purple",  # 2 节点 = 4 事件
    )

    starts = bus.history(topic=EventType.AgentStart)
    finishes = bus.history(topic=EventType.AgentFinish)
    assert len(starts) == 2
    assert len(finishes) == 2
    assert all(e.payload["phase"] == "succeeded" for e in finishes)


def test_upstream_outputs_passed_to_downstream():
    """下游 executor 的 upstream 应包含上游所有节点的产出。"""
    runtime = _StubRuntime()
    orchestrator = Orchestrator()

    result = orchestrator.execute(
        goal="链式",
        runtime=runtime,
        scenario="generic",  # analyze -> execute -> verify
    )

    assert result.success
    # execute 的 upstream 应含 analyze 产出
    execute_call = next(c for c in runtime.calls if c[0] == "execute")
    verify_call = next(c for c in runtime.calls if c[0] == "verify")
    assert "analyze" in execute_call[1]
    assert "execute" in verify_call[1]


def test_failed_node_skips_downstream():
    """runtime.run 抛异常时，下游应被 Skipped。"""
    class _FailingRuntime:
        def run(self, agent_id: str, task: Task) -> dict:
            if agent_id == "execute":
                raise RuntimeError("exec failed")
            return {"ok": True}

    orchestrator = Orchestrator()

    result = orchestrator.execute(
        goal="test",
        runtime=_FailingRuntime(),
        scenario="generic",  # analyze -> execute(失败) -> verify(跳过)
    )

    assert not result.success
    assert result.node_statuses["analyze"] == WorkflowStatus.Succeeded
    assert result.node_statuses["execute"] == WorkflowStatus.Failed
    assert result.node_statuses["verify"] == WorkflowStatus.Skipped
    assert "RuntimeError" in result.errors["execute"]


def test_execute_plan_mismatch_raises():
    """plan.dag 与 plan.tasks 数量不一致应抛 ValueError。"""
    bad_plan = Plan(goal="x", dag={"a": [], "b": ["a"]}, tasks=[Task(goal="only one")])
    orchestrator = Orchestrator()

    import pytest

    with pytest.raises(ValueError, match="dag nodes"):
        orchestrator.execute_plan(bad_plan, _StubRuntime())
