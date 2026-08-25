# date: 2026-07-06
# dev: myf
"""EventBus 单元测试。

覆盖：订阅接收、多订阅顺序、主题过滤、空主题无投递、handler 异常隔离、
历史查询与过滤、死信队列、取消订阅。
"""
from __future__ import annotations

from aegisos_agents.planning.engine.eventbus import EventBus
from protocol.event import Event, EventType
from protocol.message import NodeRef


def test_subscribe_and_receive_event():
    """订阅者应收到对应 topic 的事件。"""
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(EventType.AgentStart, received.append)

    event = Event(
        event_type=EventType.AgentStart,
        task_id="t1",
        source=NodeRef("agent-1", "agent"),
        payload={"step": "recon"},
    )
    bus.publish(event)

    assert len(received) == 1
    assert received[0].event_id == event.event_id
    assert received[0].task_id == "t1"


def test_multiple_subscribers_receive_in_order():
    """同 topic 多订阅者应按订阅顺序依次收到同一事件。"""
    bus = EventBus()
    order: list[str] = []
    bus.subscribe(EventType.AgentFinish, lambda e: order.append("first"))
    bus.subscribe(EventType.AgentFinish, lambda e: order.append("second"))
    bus.subscribe(EventType.AgentFinish, lambda e: order.append("third"))

    bus.publish(Event(event_type=EventType.AgentFinish))

    assert order == ["first", "second", "third"]


def test_topic_filtering_no_cross_topic_delivery():
    """发布 AgentStart 不应投递给 ToolCall 订阅者（低熵稀疏）。"""
    bus = EventBus()
    starts: list[Event] = []
    tool_calls: list[Event] = []
    bus.subscribe(EventType.AgentStart, starts.append)
    bus.subscribe(EventType.ToolCall, tool_calls.append)

    bus.publish(Event(event_type=EventType.AgentStart))
    bus.publish(Event(event_type=EventType.ToolCall))

    assert len(starts) == 1
    assert len(tool_calls) == 1
    assert starts[0].event_type == EventType.AgentStart
    assert tool_calls[0].event_type == EventType.ToolCall


def test_unsubscribe_removes_handler():
    """取消订阅后不再收到事件。"""
    bus = EventBus()
    received: list[Event] = []
    unsub = bus.subscribe(EventType.AgentStart, received.append)

    bus.publish(Event(event_type=EventType.AgentStart))
    assert len(received) == 1

    unsub()
    bus.publish(Event(event_type=EventType.AgentStart))
    assert len(received) == 1  # 取消后未再收到


def test_handler_exception_isolated_to_dead_letter():
    """单个 handler 异常不中断后续 handler，并记入死信队列。"""
    bus = EventBus()
    survived: list[Event] = []

    def _bad_handler(e: Event) -> None:
        raise RuntimeError("handler boom")

    bus.subscribe(EventType.AgentStart, _bad_handler)
    bus.subscribe(EventType.AgentStart, survived.append)

    bus.publish(Event(event_type=EventType.AgentStart, task_id="t1"))

    # 后续 handler 仍被调用
    assert len(survived) == 1
    # 死信队列记录了异常
    dead = bus.dead_letters()
    assert len(dead) == 1
    assert dead[0][0].task_id == "t1"
    assert "handler boom" in dead[0][1]


def test_history_filtered_by_topic_and_task():
    """历史查询支持按 topic 与 task_id 过滤。"""
    bus = EventBus()
    bus.publish(Event(event_type=EventType.AgentStart, task_id="t1"))
    bus.publish(Event(event_type=EventType.AgentFinish, task_id="t1"))
    bus.publish(Event(event_type=EventType.AgentStart, task_id="t2"))

    assert len(bus.history()) == 3
    assert len(bus.history(topic=EventType.AgentStart)) == 2
    assert len(bus.history(topic=EventType.AgentStart, task_id="t2")) == 1


def test_history_trims_to_limit():
    """历史超过上限后应丢弃最旧事件。"""
    bus = EventBus(history_limit=3)
    for i in range(5):
        bus.publish(Event(event_type=EventType.AgentStart, task_id=f"t{i}"))

    history = bus.history()
    assert len(history) == 3
    # 最旧的 t0/t1 被丢弃
    assert history[0].task_id == "t2"
    assert history[-1].task_id == "t4"


def test_clear_resets_history_and_dead_letters():
    """clear 应清空历史与死信，但保留订阅者。"""
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(EventType.AgentStart, received.append)

    def _bad(e: Event) -> None:
        raise ValueError("x")

    bus.subscribe(EventType.AgentStart, _bad)
    bus.publish(Event(event_type=EventType.AgentStart))
    assert len(bus.history()) == 1
    assert len(bus.dead_letters()) == 1

    bus.clear()
    assert bus.history() == []
    assert bus.dead_letters() == []

    # 订阅者仍在
    bus.publish(Event(event_type=EventType.AgentStart))
    assert len(received) == 2  # clear 前后各一条
