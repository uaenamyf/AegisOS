# date: 2026-07-07
# dev: myf
# changelog: R5.4 AgentHooks 发布事件到 EventBus 测试
"""R5.4 AgentHooks 发布事件到 EventBus 测试。

验证 CyberAgentHooks 注入 eventbus 后，回调中发布对应 EventType 到总线。
"""
from __future__ import annotations

import asyncio

from aegisos_agents.planning.engine.eventbus import EventBus
from observability.inspect.monitor.tracing import CyberAgentHooks
from protocol.event import EventType


class _FakeAgent:
    """模拟 SDK Agent，含 name 与 instructions 属性。"""

    def __init__(self, name: str = "TestAgent") -> None:
        self.name = name
        self.instructions = "test instructions"


class _FakeTool:
    """模拟 SDK Tool，含 name 属性。"""

    def __init__(self, name: str = "nmap_scan") -> None:
        self.name = name


class _FakeOutput:
    """模拟 Pydantic 输出，含 model_dump。"""

    def model_dump(self) -> dict:
        return {"result": "ok"}


def _run_async(coro):
    """同步运行异步协程。"""
    return asyncio.run(coro)


def test_on_start_publishes_agent_start_event():
    """on_start 回调应发布 AgentStart 事件到 EventBus。"""
    bus = EventBus()
    hooks = CyberAgentHooks(agent_name="ReconAgent", eventbus=bus, task_id="t1")

    _run_async(hooks.on_start(context=None, agent=_FakeAgent("ReconAgent")))

    events = bus.history(topic=EventType.AgentStart)
    assert len(events) == 1
    assert events[0].task_id == "t1"
    assert events[0].source.node_id == "ReconAgent"


def test_on_end_publishes_agent_finish_event():
    """on_end 回调应发布 AgentFinish 事件到 EventBus。"""
    bus = EventBus()
    hooks = CyberAgentHooks(agent_name="ReconAgent", eventbus=bus, task_id="t1")

    _run_async(hooks.on_end(context=None, agent=_FakeAgent(), output=_FakeOutput()))

    events = bus.history(topic=EventType.AgentFinish)
    assert len(events) == 1
    assert "output" in events[0].payload


def test_on_tool_start_publishes_tool_call_event():
    """on_tool_start 回调应发布 ToolCall 事件到 EventBus。"""
    bus = EventBus()
    hooks = CyberAgentHooks(agent_name="ReconAgent", eventbus=bus)

    _run_async(hooks.on_tool_start(context=None, agent=_FakeAgent(), tool=_FakeTool()))

    events = bus.history(topic=EventType.ToolCall)
    assert len(events) == 1
    assert events[0].payload["tool"] == "nmap_scan"


def test_on_tool_end_publishes_tool_finish_event():
    """on_tool_end 回调应发布 ToolFinish 事件到 EventBus。"""
    bus = EventBus()
    hooks = CyberAgentHooks(agent_name="ReconAgent", eventbus=bus)

    _run_async(
        hooks.on_tool_end(
            context=None, agent=_FakeAgent(), tool=_FakeTool(), result="scan done"
        )
    )

    events = bus.history(topic=EventType.ToolFinish)
    assert len(events) == 1
    assert "result" in events[0].payload


def test_no_eventbus_does_not_publish():
    """无 eventbus 时回调应正常完成且不抛异常（向后兼容）。"""
    hooks = CyberAgentHooks(agent_name="ReconAgent")

    # 不应抛异常
    _run_async(hooks.on_start(context=None, agent=_FakeAgent()))
    _run_async(hooks.on_end(context=None, agent=_FakeAgent(), output="done"))

    # events 列表仍记录
    assert len(hooks.events) == 2


def test_install_hooks_with_eventbus_publishes():
    """CyberOrchestrator.install_hooks(eventbus=bus) 后链路执行发布事件。"""
    from aegisos_agents.planning.orchestrator import CyberOrchestrator
    from backend.mocks.cyber_provider import _CyberMockProvider

    bus = EventBus()
    orchestrator = CyberOrchestrator(mock=_CyberMockProvider())
    orchestrator.install_hooks(eventbus=bus, task_id="red-chain-task")

    # 执行红队链，SDK Runner 触发 on_start/on_end
    orchestrator.run_red_chain("10.0.0.0/24")

    # 应收到至少 2 个 AgentStart 事件（recon + vuln_correlator + exploit_planner）
    starts = bus.history(topic=EventType.AgentStart)
    assert len(starts) >= 2
    # 应收到至少 2 个 AgentFinish 事件
    finishes = bus.history(topic=EventType.AgentFinish)
    assert len(finishes) >= 2
    # 所有事件 task_id 应为 red-chain-task
    for e in starts + finishes:
        assert e.task_id == "red-chain-task"
