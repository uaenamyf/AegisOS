# date: 2026-07-07
# dev: myf
# changelog: H5.1 新建实时监控——MetricsCollector 指标采集 + AlertRule 告警规则 + DashboardData 面板数据
"""实时监控 —— 指标采集、告警规则、监控面板数据。

本模块实现 :class:`MetricsCollector`，订阅 :class:`EventBus` 的事件，
自动采集 Agent 执行指标（延迟/成功率/Token 用量/调用次数），并支持
告警规则匹配与监控面板数据生成。

设计要点：
    - **指标类型**：counter（计数器）、gauge（瞬时值）、histogram（分布）。
    - **自动采集**：订阅 EventBus，``AgentStart`` 记录开始时间，
      ``AgentFinish`` 计算延迟与成功率，``ToolCall``/``ToolFinish`` 计工具次数。
    - **告警规则**：``AlertRule(metric_name, threshold, comparator)``，
      指标超阈值时触发告警（如延迟 > 5s、成功率 < 0.8）。
    - **面板数据**：``get_dashboard()`` 返回 JSON 可序列化字典，
      供前端 MonitorView 渲染。

与现有架构的关系：
    - 实现 :class:`observability.api.MonitorAPI` Protocol。
    - 订阅 :class:`aegisos_agents.planning.engine.eventbus.EventBus` 的事件。
    - 复用 ``protocol.event.EventType`` 的 8 种事件类型。
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from protocol.event import Event, EventType


class MetricType(str, Enum):
    """指标类型枚举。"""

    COUNTER = "counter"    # 计数器：单调递增（如调用次数）
    GAUGE = "gauge"        # 瞬时值：可增可减（如当前并发数）
    HISTOGRAM = "histogram"  # 分布：记录多个值供统计（如延迟分布）


@dataclass
class Metric:
    """单个指标数据点。

    Attributes:
        name: 指标名（如 ``"agent.latency"``）。
        value: 指标值。
        metric_type: 指标类型。
        tags: 标签字典（如 ``{"agent": "ReconAgent"}``）。
        timestamp: 采集时间戳。
    """

    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AlertRule:
    """告警规则。

    当指标值满足比较条件时触发告警。

    Attributes:
        rule_id: 规则唯一标识。
        metric_name: 关联的指标名。
        threshold: 阈值。
        comparator: 比较运算符（``">"`` / ``"<"`` / ``">="`` / ``"<="`` / ``"=="``）。
        message: 告警消息模板。
        severity: 严重级别（``info`` / ``warning`` / ``critical``）。
    """

    rule_id: str
    metric_name: str
    threshold: float
    comparator: str = ">"
    message: str = ""
    severity: str = "warning"

    def matches(self, value: float) -> bool:
        """检查指标值是否满足告警条件。

        Args:
            value: 当前指标值。

        Returns:
            True 表示满足告警条件。
        """
        if self.comparator == ">":
            return value > self.threshold
        if self.comparator == "<":
            return value < self.threshold
        if self.comparator == ">=":
            return value >= self.threshold
        if self.comparator == "<=":
            return value <= self.threshold
        if self.comparator == "==":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """触发的告警实例。

    Attributes:
        rule_id: 触发的规则 ID。
        metric_name: 关联指标名。
        value: 触发时的指标值。
        threshold: 规则阈值。
        severity: 严重级别。
        message: 告警消息。
        timestamp: 触发时间戳。
    """

    rule_id: str
    metric_name: str
    value: float
    threshold: float
    severity: str = "warning"
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "rule_id": self.rule_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class MetricsCollector:
    """实时指标采集器 —— 订阅 EventBus 自动采集 Agent 执行指标。

    实现 :class:`observability.api.MonitorAPI` Protocol。订阅 EventBus 后，
    自动从事件中提取指标；也可通过 :meth:`record_metric` 手动记录。

    Attributes:
        _metrics: 指标名 -> 指标值列表（按时间顺序）。
        _counters: 计数器指标名 -> 累计值。
        _histograms: 直方图指标名 -> 值分布列表。
        _alerts: 触发的告警列表。
        _rules: 告警规则列表。
        _agent_start_times: Agent 开始时间记录（用于计算延迟）。
        _unsub: EventBus 取消订阅函数。
    """

    def __init__(self) -> None:
        """初始化采集器。"""
        self._metrics: dict[str, list[Metric]] = defaultdict(list)
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._alerts: list[Alert] = []
        self._rules: list[AlertRule] = []
        self._agent_start_times: dict[str, float] = {}
        self._unsub: Callable[[], None] | None = None

    def subscribe_to(self, eventbus: Any) -> None:
        """订阅 EventBus 的 Agent 生命周期事件。

        订阅 ``AgentStart`` / ``AgentFinish`` / ``ToolCall`` / ``ToolFinish``，
        自动采集延迟、成功率、调用次数指标。

        Args:
            eventbus: :class:`EventBus` 实例。
        """
        # 取消旧订阅
        if self._unsub is not None:
            self._unsub()

        unsubs: list[Callable[[], None]] = []
        unsubs.append(eventbus.subscribe(EventType.AgentStart, self._on_agent_start))
        unsubs.append(eventbus.subscribe(EventType.AgentFinish, self._on_agent_finish))
        unsubs.append(eventbus.subscribe(EventType.ToolCall, self._on_tool_call))
        unsubs.append(eventbus.subscribe(EventType.ToolFinish, self._on_tool_finish))

        def _unsub_all() -> None:
            for u in unsubs:
                u()

        self._unsub = _unsub_all

    def _on_agent_start(self, event: Event) -> None:
        """AgentStart 事件回调：记录开始时间。"""
        agent_name = event.source.node_id
        self._agent_start_times[agent_name] = event.timestamp
        self._increment_counter("agent.start_count", {"agent": agent_name})

    def _on_agent_finish(self, event: Event) -> None:
        """AgentFinish 事件回调：计算延迟与成功率。"""
        agent_name = event.source.node_id
        start_time = self._agent_start_times.pop(agent_name, None)
        if start_time is not None:
            latency = event.timestamp - start_time
            self._record_histogram("agent.latency_ms", latency * 1000, {"agent": agent_name})
        # 成功率：phase=succeeded 计成功，phase=failed 计失败
        phase = event.payload.get("phase", "")
        if phase == "succeeded":
            self._increment_counter("agent.success_count", {"agent": agent_name})
        elif phase == "failed":
            self._increment_counter("agent.failure_count", {"agent": agent_name})
        # 计算成功率 gauge
        success = self._counters.get("agent.success_count", 0)
        failure = self._counters.get("agent.failure_count", 0)
        total = success + failure
        if total > 0:
            self.record_metric("agent.success_rate", success / total, MetricType.GAUGE, {"agent": agent_name})

    def _on_tool_call(self, event: Event) -> None:
        """ToolCall 事件回调：计工具调用次数。"""
        tool_name = event.payload.get("tool", "unknown")
        self._increment_counter("tool.call_count", {"tool": tool_name})

    def _on_tool_finish(self, event: Event) -> None:
        """ToolFinish 事件回调。"""
        tool_name = event.payload.get("tool", "unknown")
        self._increment_counter("tool.finish_count", {"tool": tool_name})

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: dict[str, str] | None = None,
    ) -> None:
        """手动记录一个指标值。

        Args:
            name: 指标名。
            value: 指标值。
            metric_type: 指标类型。
            tags: 标签字典。
        """
        metric = Metric(name=name, value=value, metric_type=metric_type, tags=tags or {})
        self._metrics[name].append(metric)
        if metric_type == MetricType.HISTOGRAM:
            self._histograms[name].append(value)
        # 检查告警规则
        self._check_alerts(name, value)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """添加告警规则。

        Args:
            rule: 告警规则。
        """
        self._rules.append(rule)

    def _check_alerts(self, metric_name: str, value: float) -> None:
        """检查指标是否触发任何告警规则。

        Args:
            metric_name: 指标名。
            value: 当前值。
        """
        for rule in self._rules:
            if rule.metric_name == metric_name and rule.matches(value):
                alert = Alert(
                    rule_id=rule.rule_id,
                    metric_name=metric_name,
                    value=value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    message=rule.message or f"{metric_name} {rule.comparator} {rule.threshold} (current: {value})",
                )
                self._alerts.append(alert)

    def _increment_counter(self, name: str, tags: dict[str, str] | None = None) -> None:
        """递增计数器指标。

        Args:
            name: 计数器名。
            tags: 标签字典。
        """
        self._counters[name] += 1
        self.record_metric(name, self._counters[name], MetricType.COUNTER, tags)

    def _record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """记录直方图值。

        Args:
            name: 直方图名。
            value: 采样值。
            tags: 标签字典。
        """
        self.record_metric(name, value, MetricType.HISTOGRAM, tags)

    def get_metrics(self, query: dict | None = None) -> list[Metric]:
        """查询指标历史。

        Args:
            query: 可选过滤条件，支持 ``{"name": "..."}`` 和 ``{"tags": {...}}``。

        Returns:
            匹配的指标列表。
        """
        result: list[Metric] = []
        name_filter = (query or {}).get("name")
        tags_filter = (query or {}).get("tags", {})
        for name, metrics in self._metrics.items():
            if name_filter and name != name_filter:
                continue
            for m in metrics:
                if all(m.tags.get(k) == v for k, v in tags_filter.items()):
                    result.append(m)
        return result

    def get_alerts(self) -> list[Alert]:
        """返回所有触发的告警。

        Returns:
            告警列表（按触发时间排序）。
        """
        return list(self._alerts)

    def alert(self, rule_id: str, ctx: dict) -> None:
        """手动触发告警（兼容 MonitorAPI）。

        Args:
            rule_id: 规则 ID。
            ctx: 告警上下文。
        """
        self._alerts.append(
            Alert(
                rule_id=rule_id,
                metric_name=ctx.get("metric", ""),
                value=ctx.get("value", 0.0),
                threshold=ctx.get("threshold", 0.0),
                severity=ctx.get("severity", "warning"),
                message=ctx.get("message", ""),
            )
        )

    def get_dashboard(self) -> dict[str, Any]:
        """生成监控面板数据（JSON 可序列化）。

        Returns:
            含 ``summary`` / ``agents`` / ``tools`` / ``alerts`` / ``latency`` 的字典。
        """
        # Agent 汇总
        agents: dict[str, dict[str, Any]] = {}
        for name, metrics in self._metrics.items():
            if not name.startswith("agent."):
                continue
            for m in metrics:
                agent_name = m.tags.get("agent", "unknown")
                if agent_name not in agents:
                    agents[agent_name] = {
                        "start_count": 0,
                        "success_count": 0,
                        "failure_count": 0,
                        "success_rate": 0.0,
                        "latency_ms_avg": 0.0,
                        "latency_ms_max": 0.0,
                    }
                if name == "agent.start_count":
                    agents[agent_name]["start_count"] = int(m.value)
                elif name == "agent.success_count":
                    agents[agent_name]["success_count"] = int(m.value)
                elif name == "agent.failure_count":
                    agents[agent_name]["failure_count"] = int(m.value)
                elif name == "agent.success_rate":
                    agents[agent_name]["success_rate"] = round(m.value, 4)
        # 延迟统计
        latency_hist = self._histograms.get("agent.latency_ms", [])
        for m in self._metrics.get("agent.latency_ms", []):
            agent_name = m.tags.get("agent", "unknown")
            if agent_name in agents:
                agents[agent_name]["latency_ms_avg"] = round(
                    sum(latency_hist) / len(latency_hist) if latency_hist else 0, 2
                )
                agents[agent_name]["latency_ms_max"] = round(max(latency_hist) if latency_hist else 0, 2)
                break
        # 工具汇总
        tools: dict[str, int] = {}
        for m in self._metrics.get("tool.call_count", []):
            tool_name = m.tags.get("tool", "unknown")
            tools[tool_name] = int(m.value)
        return {
            "summary": {
                "total_agents": len(agents),
                "total_calls": int(self._counters.get("agent.start_count", 0)),
                "total_success": int(self._counters.get("agent.success_count", 0)),
                "total_failure": int(self._counters.get("agent.failure_count", 0)),
                "total_alerts": len(self._alerts),
            },
            "agents": agents,
            "tools": tools,
            "alerts": [a.to_dict() for a in self._alerts],
            "latency": {
                "avg_ms": round(sum(latency_hist) / len(latency_hist), 2) if latency_hist else 0,
                "max_ms": round(max(latency_hist), 2) if latency_hist else 0,
                "min_ms": round(min(latency_hist), 2) if latency_hist else 0,
                "samples": len(latency_hist),
            },
        }

    def reset(self) -> None:
        """清空所有指标与告警。"""
        self._metrics.clear()
        self._counters.clear()
        self._histograms.clear()
        self._alerts.clear()
        self._agent_start_times.clear()
