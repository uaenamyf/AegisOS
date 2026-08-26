# date: 2026-07-07
# dev: myf
# changelog: H5.1 MetricsCollector 单元测试——指标采集/告警/面板/EventBus 订阅
"""H5.1 实时监控 MetricsCollector 单元测试。"""
from __future__ import annotations

import time

from aegisos_agents.planning.engine.eventbus import EventBus
from observability.inspect.monitor import (
    AlertRule,
    MetricsCollector,
    MetricType,
)
from protocol.event import Event, EventType
from protocol.message import NodeRef


def _make_event(event_type: EventType, agent: str, phase: str = "", task_id: str = "t1") -> Event:
    return Event(
        event_type=event_type,
        task_id=task_id,
        source=NodeRef(agent, "agent", agent),
        payload={"phase": phase} if phase else {},
        timestamp=time.time(),
    )


def test_record_metric_stores_history():
    """手动记录的指标应存入历史。"""
    mc = MetricsCollector()
    mc.record_metric("test.metric", 42.0, MetricType.GAUGE, {"tag": "x"})
    metrics = mc.get_metrics({"name": "test.metric"})
    assert len(metrics) == 1
    assert metrics[0].value == 42.0


def test_subscribe_to_eventbus_collects_agent_metrics():
    """订阅 EventBus 后 AgentStart/Finish 应自动采集延迟与成功率。"""
    bus = EventBus()
    mc = MetricsCollector()
    mc.subscribe_to(bus)

    base = time.time()
    # AgentStart
    bus.publish(_make_event(EventType.AgentStart, "ReconAgent", task_id="t1"))
    time.sleep(0.01)
    # AgentFinish（succeeded）
    finish = _make_event(EventType.AgentFinish, "ReconAgent", "succeeded", "t1")
    finish.timestamp = base + 0.05
    bus.publish(finish)

    dashboard = mc.get_dashboard()
    assert "ReconAgent" in dashboard["agents"]
    assert dashboard["agents"]["ReconAgent"]["success_count"] >= 1
    assert dashboard["agents"]["ReconAgent"]["latency_ms_max"] > 0


def test_alert_rule_triggers_on_threshold():
    """指标超阈值应触发告警。"""
    mc = MetricsCollector()
    mc.add_alert_rule(
        AlertRule(
            rule_id="high_latency",
            metric_name="agent.latency_ms",
            threshold=1000.0,
            comparator=">",
            severity="critical",
            message="latency too high",
        )
    )
    mc.record_metric("agent.latency_ms", 2000.0)
    alerts = mc.get_alerts()
    assert len(alerts) == 1
    assert alerts[0].rule_id == "high_latency"
    assert alerts[0].severity == "critical"


def test_alert_rule_no_trigger_below_threshold():
    """指标未超阈值不应触发告警。"""
    mc = MetricsCollector()
    mc.add_alert_rule(
        AlertRule(rule_id="r1", metric_name="x", threshold=100.0, comparator=">")
    )
    mc.record_metric("x", 50.0)
    assert len(mc.get_alerts()) == 0


def test_dashboard_summary_structure():
    """面板数据应含 summary/agents/tools/alerts/latency。"""
    mc = MetricsCollector()
    mc.record_metric("agent.start_count", 5, MetricType.COUNTER, {"agent": "A"})
    dashboard = mc.get_dashboard()
    assert "summary" in dashboard
    assert "agents" in dashboard
    assert "tools" in dashboard
    assert "alerts" in dashboard
    assert "latency" in dashboard


def test_tool_call_counting():
    """ToolCall 事件应计工具调用次数。"""
    bus = EventBus()
    mc = MetricsCollector()
    mc.subscribe_to(bus)
    bus.publish(
        Event(
            event_type=EventType.ToolCall,
            source=NodeRef("ReconAgent", "agent"),
            payload={"tool": "nmap_scan"},
        )
    )
    dashboard = mc.get_dashboard()
    assert dashboard["tools"].get("nmap_scan", 0) >= 1


def test_reset_clears_all():
    """reset 应清空指标与告警。"""
    mc = MetricsCollector()
    mc.record_metric("x", 1.0)
    mc.add_alert_rule(AlertRule(rule_id="r", metric_name="x", threshold=0, comparator=">"))
    mc.record_metric("x", 5.0)
    assert len(mc.get_metrics()) > 0
    assert len(mc.get_alerts()) > 0
    mc.reset()
    assert mc.get_metrics() == []
    assert mc.get_alerts() == []
