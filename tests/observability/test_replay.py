# date: 2026-07-07
# dev: myf
# changelog: H5.2 ReplayPlayer 单元测试——Timeline 过滤/攻击链视图/播放器步进
"""H5.2 攻击链回放 Timeline + ReplayPlayer 单元测试。"""
from __future__ import annotations

import time

from protocol.event import Event, EventType
from protocol.message import NodeRef

from observability.inspect.replay import (
    ReplayPlayer,
    Timeline,
    create_replay_from_eventbus,
)
from aegisos_agents.planning.engine.eventbus import EventBus


def _make_event(
    event_type: EventType,
    agent: str,
    phase: str = "",
    task_id: str = "t1",
    ts: float | None = None,
) -> Event:
    return Event(
        event_type=event_type,
        task_id=task_id,
        source=NodeRef(agent, "agent", agent),
        payload={"phase": phase} if phase else {},
        timestamp=ts if ts is not None else time.time(),
    )


def test_timeline_orders_events_by_time():
    """Timeline 应按时间戳排序。"""
    base = time.time()
    events = [
        _make_event(EventType.AgentFinish, "B", "succeeded", ts=base + 0.2),
        _make_event(EventType.AgentStart, "A", ts=base),
        _make_event(EventType.AgentStart, "B", ts=base + 0.1),
        _make_event(EventType.AgentFinish, "A", "succeeded", ts=base + 0.15),
    ]
    timeline = Timeline(events)
    entries = timeline.entries()
    assert len(entries) == 4
    # 应按时间升序
    assert entries[0].agent_name == "A"
    assert entries[0].event.event_type == EventType.AgentStart
    assert entries[-1].agent_name == "B"
    assert entries[-1].event.event_type == EventType.AgentFinish


def test_timeline_filter_by_task_id():
    """按 task_id 过滤应只返回匹配事件。"""
    events = [
        _make_event(EventType.AgentStart, "A", task_id="t1"),
        _make_event(EventType.AgentStart, "B", task_id="t2"),
    ]
    timeline = Timeline(events)
    filtered = timeline.filter(task_id="t1")
    assert len(filtered) == 1
    assert filtered[0].agent_name == "A"


def test_timeline_filter_by_topic():
    """按 EventType 过滤应只返回匹配类型。"""
    events = [
        _make_event(EventType.AgentStart, "A"),
        _make_event(EventType.ToolCall, "A"),
    ]
    timeline = Timeline(events)
    filtered = timeline.filter(topic=EventType.ToolCall)
    assert len(filtered) == 1
    assert filtered[0].event.event_type == EventType.ToolCall


def test_attack_chain_view_pairs_start_finish():
    """攻击链视图应配对 AgentStart/Finish 计算延迟。"""
    base = time.time()
    events = [
        _make_event(EventType.AgentStart, "ReconAgent", ts=base),
        _make_event(EventType.AgentFinish, "ReconAgent", "succeeded", ts=base + 0.1),
        _make_event(EventType.AgentStart, "VulnAgent", ts=base + 0.2),
        _make_event(EventType.AgentFinish, "VulnAgent", "succeeded", ts=base + 0.35),
    ]
    timeline = Timeline(events)
    steps = timeline.get_attack_chain_view()
    assert len(steps) == 2
    assert steps[0]["agent_name"] == "ReconAgent"
    assert steps[0]["latency_ms"] is not None
    assert steps[0]["latency_ms"] > 0
    assert steps[1]["agent_name"] == "VulnAgent"


def test_replay_player_step_sequential():
    """播放器步进应按序返回条目。"""
    events = [
        _make_event(EventType.AgentStart, "A"),
        _make_event(EventType.AgentFinish, "A", "succeeded"),
        _make_event(EventType.AgentStart, "B"),
    ]
    timeline = Timeline(events)
    player = ReplayPlayer(timeline)
    assert player.total == 3
    assert player.is_finished is False

    e1 = player.step()
    assert e1 is not None
    assert e1.agent_name == "A"

    e2 = player.step()
    assert e2 is not None

    e3 = player.step()
    assert e3 is not None

    e4 = player.step()
    assert e4 is None
    assert player.is_finished is True


def test_replay_player_reset():
    """reset 应回到起点。"""
    events = [_make_event(EventType.AgentStart, "A")]
    timeline = Timeline(events)
    player = ReplayPlayer(timeline)
    player.step()
    assert player.position == 1
    player.reset()
    assert player.position == 0


def test_replay_deterministic_callback():
    """replay 应逐事件回调不等待。"""
    events = [
        _make_event(EventType.AgentStart, "A"),
        _make_event(EventType.AgentFinish, "A", "succeeded"),
    ]
    timeline = Timeline(events)
    player = ReplayPlayer(timeline)
    visited: list[str] = []
    player.replay(lambda e: visited.append(e.agent_name))
    assert visited == ["A", "A"]


def test_create_replay_from_eventbus():
    """create_replay_from_eventbus 应从 EventBus 历史创建时间线。"""
    bus = EventBus()
    bus.publish(_make_event(EventType.AgentStart, "A", task_id="t1"))
    bus.publish(_make_event(EventType.AgentFinish, "A", "succeeded", task_id="t1"))
    timeline = create_replay_from_eventbus(bus, task_id="t1")
    assert len(timeline.entries()) == 2
