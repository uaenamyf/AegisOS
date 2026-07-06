# date: 2026-07-06
# dev: myf
"""WorkflowEngine 单元测试。

覆盖：线性链顺序执行、并行汇聚、条件分支跳过、失败传播、循环依赖检测、
事件发布、初始 context 合并。
"""
from __future__ import annotations

from protocol.event import EventType

from aegisos_agents.planning.engine.eventbus import EventBus
from aegisos_agents.planning.engine.workflow import (
    WorkflowEngine,
    WorkflowNode,
    WorkflowStatus,
)


def test_linear_chain_executes_in_order():
    """A → B → C 线性链应按顺序执行，产出逐级传递。"""
    calls: list[str] = []

    def make_exec(name: str):
        def _exec(upstream: dict) -> str:
            calls.append(name)
            return f"{name}_done"
        return _exec

    nodes = {
        "a": WorkflowNode("a", make_exec("a")),
        "b": WorkflowNode("b", make_exec("b"), dependencies=["a"]),
        "c": WorkflowNode("c", make_exec("c"), dependencies=["b"]),
    }
    result = WorkflowEngine().run(nodes)

    assert result.success
    assert calls == ["a", "b", "c"]
    assert result.node_outputs["a"] == "a_done"
    assert result.node_outputs["c"] == "c_done"
    assert all(
        result.node_statuses[nid] == WorkflowStatus.Succeeded
        for nid in ("a", "b", "c")
    )


def test_parallel_fan_out_and_gather():
    """A → (B, C) → D 并行扇出后汇聚到 D，B/C 应并行执行。"""
    nodes = {
        "a": WorkflowNode("a", lambda u: "a"),
        "b": WorkflowNode("b", lambda u: "b", dependencies=["a"]),
        "c": WorkflowNode("c", lambda u: "c", dependencies=["a"]),
        "d": WorkflowNode(
            "d",
            lambda u: f"{u['b']}+{u['c']}",
            dependencies=["b", "c"],
        ),
    }
    result = WorkflowEngine().run(nodes)

    assert result.success
    assert result.node_outputs["d"] == "b+c"
    assert result.node_statuses["b"] == WorkflowStatus.Succeeded
    assert result.node_statuses["c"] == WorkflowStatus.Succeeded


def test_condition_skips_node():
    """condition 返回 False 的节点应被跳过（Skipped）。"""
    nodes = {
        "a": WorkflowNode("a", lambda u: {"val": 5}),
        "b": WorkflowNode(
            "b",
            lambda u: u["a"]["val"] * 2,
            dependencies=["a"],
            condition=lambda u: u["a"]["val"] > 10,  # False → 跳过
        ),
    }
    result = WorkflowEngine().run(nodes)

    assert result.node_statuses["a"] == WorkflowStatus.Succeeded
    assert result.node_statuses["b"] == WorkflowStatus.Skipped
    assert "b" not in result.node_outputs
    # Skipped 不影响整体成功
    assert result.success


def test_failure_propagates_to_dependents_as_skipped():
    """Failed 节点的下游应被标记 Skipped（不执行）。"""
    def _boom(u: dict) -> str:
        raise RuntimeError("node b failed")

    nodes = {
        "a": WorkflowNode("a", lambda u: "a"),
        "b": WorkflowNode("b", _boom, dependencies=["a"]),
        "c": WorkflowNode("c", lambda u: "c", dependencies=["b"]),
    }
    result = WorkflowEngine().run(nodes)

    assert not result.success
    assert result.node_statuses["a"] == WorkflowStatus.Succeeded
    assert result.node_statuses["b"] == WorkflowStatus.Failed
    assert result.node_statuses["c"] == WorkflowStatus.Skipped
    assert "RuntimeError" in result.errors["b"]
    assert "c" not in result.node_outputs


def test_cycle_detection_raises():
    """存在循环依赖时应抛 ValueError。"""
    nodes = {
        "a": WorkflowNode("a", lambda u: "a", dependencies=["b"]),
        "b": WorkflowNode("b", lambda u: "b", dependencies=["a"]),
    }
    import pytest

    with pytest.raises(ValueError, match="Cycle"):
        WorkflowEngine().run(nodes)


def test_context_merged_into_upstream():
    """初始 context 应合并到 upstream，供节点读取外部输入。"""
    nodes = {
        "a": WorkflowNode(
            "a", lambda u: u.get("target", "default")
        ),
    }
    result = WorkflowEngine().run(nodes, context={"target": "10.0.0.0/24"})

    assert result.success
    assert result.node_outputs["a"] == "10.0.0.0/24"


def test_eventbus_receives_start_and_finish_events():
    """注入 EventBus 后应收到 AgentStart + AgentFinish 事件。"""
    bus = EventBus()
    engine = WorkflowEngine(eventbus=bus)
    nodes = {"a": WorkflowNode("a", lambda u: "done")}
    engine.run(nodes, task_id="task-1")

    history = bus.history()
    assert len(history) == 2
    assert history[0].event_type == EventType.AgentStart
    assert history[0].task_id == "task-1"
    assert history[1].event_type == EventType.AgentFinish
    assert history[1].payload["phase"] == "succeeded"


def test_failed_node_emits_failed_event():
    """失败节点应发布带 error 的 AgentFinish 事件。"""
    bus = EventBus()
    engine = WorkflowEngine(eventbus=bus)

    def _bad(u: dict) -> str:
        raise ValueError("exec failed")

    nodes = {"a": WorkflowNode("a", _bad)}
    engine.run(nodes, task_id="task-2")

    finish_events = bus.history(topic=EventType.AgentFinish)
    assert len(finish_events) == 1
    assert finish_events[0].payload["phase"] == "failed"
    assert "exec failed" in finish_events[0].payload["error"]
