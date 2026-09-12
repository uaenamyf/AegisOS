# date: 2026-08-17
# dev: 陈子毅
"""AP4.1 AskMode / AskHandler 单元测试（人机协同核心）。

覆盖：Mock handler 返回回答、超时触发 on_timeout 降级、无人值守
AutoAskHandler 即时降级、事件总线透传（HumanInputRequired /
HumanResponse）、severity_at_least 阈值比较、新增事件类型存在性。
"""
from aegisos_agents.perception.reasoning.strategies import (
    AskMode,
    AskResponse,
    MockAskHandler,
    severity_at_least,
)
from protocol.event import EventType


class _RecordingBus:
    """记录发布事件的伪事件总线，用于断言事件透传。"""

    def __init__(self) -> None:
        self.events: list = []

    def publish(self, e) -> None:
        self.events.append(e)


def test_mock_handler_returns_answer():
    m = AskMode()
    m.set_ask_handler(MockAskHandler(response=AskResponse(answered=True, answer="确认执行")))
    r = m.ask_human("破坏性动作？", options=["确认执行", "降级"], context={})
    assert r.answered is True
    assert r.answer == "确认执行"


def test_timeout_triggers_on_timeout_degrade():
    m = AskMode()
    m.set_ask_handler(MockAskHandler(simulate_timeout=True))
    r = m.ask_human(
        "破坏性动作？",
        options=["确认执行", "降级"],
        on_timeout=lambda req: AskResponse(
            answered=False, answer="降级为仅监控", timeout=True
        ),
    )
    assert r.timeout is True
    assert r.answer == "降级为仅监控"


def test_no_handler_auto_degrades():
    # 未注入任何 handler：退化为 AutoAskHandler，立即超时降级
    m = AskMode()
    r = m.ask_human(
        "破坏性动作？",
        on_timeout=lambda req: AskResponse(
            answered=False, answer="降级为仅监控", timeout=True
        ),
    )
    assert r.timeout is True
    assert r.answer == "降级为仅监控"


def test_events_published():
    bus = _RecordingBus()
    m = AskMode()
    m.set_ask_handler(MockAskHandler(response=AskResponse(answered=True, answer="x")))
    m.set_event_bus(bus)
    m.ask_human("破坏性动作？", options=["x"], context={"k": 1})
    types = [e.event_type for e in bus.events]
    assert EventType.HumanInputRequired in types
    assert EventType.HumanResponse in types


def test_severity_at_least():
    assert severity_at_least("high", "high") is True
    assert severity_at_least("critical", "high") is True
    assert severity_at_least("low", "high") is False
    assert severity_at_least("none", "medium") is False


def test_new_event_types_exist():
    assert hasattr(EventType, "HumanInputRequired")
    assert hasattr(EventType, "HumanResponse")
    assert EventType.HumanInputRequired.value == "human.input.required"
    assert EventType.HumanResponse.value == "human.response"
