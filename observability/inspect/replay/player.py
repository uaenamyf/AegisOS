# date: 2026-07-07
# dev: myf
# changelog: H5.2 新建攻击链回放——Timeline 时序记录 + ReplayPlayer 基于 EventBus 事件回放
"""攻击链回放 —— 基于事件流的确定性时序回放。

本模块实现 :class:`Timeline` 和 :class:`ReplayPlayer`，将 EventBus 记录的
事件流按时间序重放，供评委演示时回顾 Agent 编排全过程。

设计要点：
    - **Timeline**：有序事件记录，支持按 task_id / topic / 时间范围过滤。
    - **ReplayPlayer**：按时间序逐事件回调，支持步进 / 跳跃 / 速度控制。
    - **确定性回放**：不重新执行 Agent，仅重放事件流（安全、可重复）。
    - **攻击链视图**：``get_attack_chain_view()`` 从事件中提取攻击链步骤，
      生成评委演示用的时序视图（含每步 Agent 名 / 产出 / 延迟）。

与现有架构的关系：
    - 实现 :class:`observability.api.ReplayAPI` Protocol。
    - 消费 :class:`aegisos_agents.planning.engine.eventbus.EventBus` 的历史事件。
    - 复用 ``protocol.event.Event`` / ``EventType``。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from protocol.event import Event, EventType


@dataclass
class TimelineEntry:
    """时间线条目 —— 单个事件的时序记录。

    Attributes:
        event: 原始事件对象。
        relative_time: 相对于回放起点的时间偏移（秒）。
        phase: 阶段标识（如 ``"recon"`` / ``"exploit"``，从 payload 提取）。
        agent_name: Agent 名称（从 source 提取）。
        status: 事件状态（``"started"`` / ``"succeeded"`` / ``"failed"`` / ``"skipped"``）。
    """

    event: Event
    relative_time: float = 0.0
    phase: str = ""
    agent_name: str = ""
    status: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
        from dataclasses import asdict

        return {
            "relative_time": round(self.relative_time, 4),
            "phase": self.phase,
            "agent_name": self.agent_name,
            "status": self.status,
            "event_type": self.event.event_type.value,
            "task_id": self.event.task_id,
            "payload": self.event.payload,
            "timestamp": self.event.timestamp,
        }


class Timeline:
    """时间线 —— 有序事件记录，支持过滤与视图生成。

    从 EventBus 历史事件或手动记录的事件构建，提供按时间序的回放视图。

    Attributes:
        _entries: 时间线条目列表（按事件时间排序）。
        _start_time: 时间线起点（首事件时间戳）。
    """

    def __init__(self, events: list[Event] | None = None) -> None:
        """从事件列表构建时间线。

        Args:
            events: 事件列表；None 创建空时间线。
        """
        self._entries: list[TimelineEntry] = []
        self._start_time: float = 0.0
        if events:
            self.load(events)

    def load(self, events: list[Event]) -> None:
        """加载事件列表到时间线。

        按 ``event.timestamp`` 排序，计算相对时间偏移。

        Args:
            events: 事件列表。
        """
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        self._start_time = sorted_events[0].timestamp if sorted_events else 0.0
        self._entries = []
        for event in sorted_events:
            self._entries.append(self._event_to_entry(event))

    def _event_to_entry(self, event: Event) -> TimelineEntry:
        """将 Event 转换为 TimelineEntry。"""
        phase = event.payload.get("phase", "")
        agent_name = event.source.node_id
        status = event.payload.get("phase", "")
        # AgentStart → started，AgentFinish 的 phase 已是 succeeded/failed/skipped
        if event.event_type == EventType.AgentStart:
            status = "started"
        return TimelineEntry(
            event=event,
            relative_time=event.timestamp - self._start_time,
            phase=phase,
            agent_name=agent_name,
            status=status,
        )

    def filter(
        self,
        task_id: str | None = None,
        topic: EventType | None = None,
        agent_name: str | None = None,
        time_range: tuple[float, float] | None = None,
    ) -> list[TimelineEntry]:
        """过滤时间线条目。

        Args:
            task_id: 按 task_id 过滤。
            topic: 按 EventType 过滤。
            agent_name: 按 Agent 名过滤。
            time_range: 按相对时间范围 ``(start, end)`` 过滤。

        Returns:
            匹配的时间线条目列表。
        """
        result = []
        for entry in self._entries:
            if task_id is not None and entry.event.task_id != task_id:
                continue
            if topic is not None and entry.event.event_type != topic:
                continue
            if agent_name is not None and entry.agent_name != agent_name:
                continue
            if time_range is not None:
                start, end = time_range
                if not (start <= entry.relative_time <= end):
                    continue
            result.append(entry)
        return result

    def entries(self) -> list[TimelineEntry]:
        """返回全部时间线条目。"""
        return list(self._entries)

    def get_attack_chain_view(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """生成攻击链时序视图（评委演示用）。

        从事件流中提取每个 Agent 的执行步骤，按时间序排列，
        每步含 Agent 名、阶段、状态、延迟。

        Args:
            task_id: 可选，按任务过滤。

        Returns:
            步骤字典列表，每个含 ``agent_name`` / ``phase`` / ``status`` /
            ``relative_time`` / ``latency_ms``。
        """
        entries = self.filter(task_id=task_id)
        # 配对 AgentStart / AgentFinish 计算延迟
        steps: list[dict[str, Any]] = []
        start_map: dict[str, TimelineEntry] = {}
        for entry in entries:
            if entry.event.event_type == EventType.AgentStart:
                start_map[entry.agent_name] = entry
            elif entry.event.event_type == EventType.AgentFinish:
                start = start_map.pop(entry.agent_name, None)
                latency_ms = (
                    round((entry.event.timestamp - start.event.timestamp) * 1000, 2)
                    if start
                    else None
                )
                steps.append(
                    {
                        "agent_name": entry.agent_name,
                        "phase": entry.phase or entry.agent_name,
                        "status": entry.status,
                        "relative_time": round(entry.relative_time, 4),
                        "latency_ms": latency_ms,
                    }
                )
        return steps


class ReplayPlayer:
    """回放播放器 —— 按时间序逐事件回调。

    支持步进、跳跃、速度控制，供前端时序回放交互。

    Attributes:
        _timeline: 关联的时间线。
        _position: 当前回放位置（条目索引）。
        _speed: 回放速度倍率（1.0 = 正常速度）。
    """

    def __init__(self, timeline: Timeline, speed: float = 1.0) -> None:
        """初始化播放器。

        Args:
            timeline: 要回放的时间线。
            speed: 回放速度倍率（默认 1.0）。
        """
        self._timeline = timeline
        self._position = 0
        self._speed = speed

    @property
    def position(self) -> int:
        """当前回放位置（条目索引）。"""
        return self._position

    @property
    def total(self) -> int:
        """总条目数。"""
        return len(self._timeline.entries())

    @property
    def is_finished(self) -> bool:
        """是否回放完毕。"""
        return self._position >= self.total

    def reset(self) -> None:
        """重置回放位置到起点。"""
        self._position = 0

    def step(self) -> TimelineEntry | None:
        """步进到下一条事件。

        Returns:
            下一个 :class:`TimelineEntry`；已到末尾返回 None。
        """
        entries = self._timeline.entries()
        if self._position >= len(entries):
            return None
        entry = entries[self._position]
        self._position += 1
        return entry

    def seek(self, position: int) -> None:
        """跳转到指定位置。

        Args:
            position: 目标条目索引。
        """
        self._position = max(0, min(position, self.total))

    def replay(self, on_event: Callable[[TimelineEntry], None]) -> None:
        """确定性回放：逐事件回调，不等待真实时间间隔。

        与 :meth:`play_timed` 的区别：不模拟时间间隔，立即逐事件回调，
        适合生成回放报告或确定性测试。

        Args:
            on_event: 事件回调函数。
        """
        self.reset()
        while not self.is_finished:
            entry = self.step()
            if entry is not None:
                on_event(entry)

    def play_timed(self, on_event: Callable[[TimelineEntry], None]) -> None:
        """定时回放：按事件间真实时间间隔（除以 speed）逐事件回调。

        适合前端时序回放演示。注意此方法会阻塞直到回放完成。

        Args:
            on_event: 事件回调函数。
        """
        self.reset()
        entries = self._timeline.entries()
        prev_time = 0.0
        for entry in entries:
            delta = entry.relative_time - prev_time
            if delta > 0:
                time.sleep(delta / self._speed)
            on_event(entry)
            prev_time = entry.relative_time


def create_replay_from_eventbus(eventbus: Any, task_id: str | None = None) -> Timeline:
    """从 EventBus 历史事件创建回放时间线。

    Args:
        eventbus: :class:`EventBus` 实例。
        task_id: 可选，按任务过滤事件。

    Returns:
        :class:`Timeline` 实例。
    """
    events = eventbus.history(task_id=task_id)
    return Timeline(events)
