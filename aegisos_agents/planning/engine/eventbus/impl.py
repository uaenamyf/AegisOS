# date: 2026-07-06
# dev: myf
# changelog: 新建 EventBus 实现——基于 topic 的发布/订阅，支持顺序保证、异常隔离、死信队列、历史记录
"""事件总线实现 —— 基于 topic 的发布/订阅消息总线。

本模块实现 :class:`EventBus`，提供进程内的发布/订阅能力，解耦 planning 域
各子系统（planner / orchestrator / workflow / scheduler / router）。所有事件
必须使用 :class:`protocol.event.Event` 类型，topic 由 :class:`EventType` 枚举
决定（8 类，见 ``protocol/event.py``）。

设计要点：
    - **顺序保证**：同一 topic 内的事件按发布顺序 FIFO 投递给订阅者。
    - **异常隔离**：单个 handler 抛异常不影响后续 handler；异常事件入死信队列。
    - **低熵稀疏**：仅投递给显式订阅了对应 topic 的 handler，不做全广播
     （对齐 ``04_PROTOCOL_SPEC`` §16 低熵稀疏路由约束）。
    - **历史记录**：保留最近 N 条事件，供 ``observability/inspect/replay/`` 回放消费。

与现有架构的关系：
    - 本模块位于 ``aegisos_agents/planning/engine/eventbus/``，实现
      :class:`aegisos_agents.api.EventBusAPI` Protocol。
    - ``protocol/event.py`` 已定义 8 种 ``EventType``，本模块直接复用，不自造。
    - R5.4 计划项：基于 SDK ``AgentHooks`` 作为事件源 → 本模块作为事件汇。
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable

from protocol.event import Event, EventType

# 历史记录上限：避免无界增长耗尽内存；回放消费从最近窗口取
HISTORY_LIMIT = 1000


class EventBus:
    """进程内发布/订阅事件总线。

    订阅者按 topic（:class:`EventType`）注册 handler，发布事件时按 FIFO 顺序
    同步调用对应 topic 的所有 handler。handler 异常被捕获并记入死信队列，
    不影响后续 handler 执行。

    Attributes:
        _subscribers: topic -> handler 列表 的映射。
        _history: 最近发布的事件 deque（FIFO，上限 HISTORY_LIMIT）。
        _dead_letters: handler 抛异常时记录的 (event, exception) 元组列表。
    """

    def __init__(self, history_limit: int = HISTORY_LIMIT) -> None:
        """初始化事件总线。

        Args:
            history_limit: 历史记录上限，超过后丢弃最旧事件。
        """
        # defaultdict(list) 让新 topic 首次订阅时自动创建空列表
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = defaultdict(list)
        self._history: deque[Event] = deque(maxlen=history_limit)
        self._dead_letters: list[tuple[Event, str]] = []

    def subscribe(
        self,
        topic: EventType,
        handler: Callable[[Event], None],
    ) -> Callable[[], None]:
        """订阅指定 topic 的事件。

        一个 topic 可被多个 handler 订阅，发布时按订阅顺序依次调用。
        同一 handler 重复订阅同一 topic 会被多次调用（不去重，便于不同上下文
        各自管理生命周期）。

        Args:
            topic: 事件类型（对应 :class:`EventType` 的 8 个枚举值）。
            handler: 事件处理回调，签名 ``handler(event: Event) -> None``。

        Returns:
            取消订阅函数，调用后移除该 handler（便于 ``with`` 风格管理）。
        """
        self._subscribers[topic].append(handler)

        def _unsubscribe() -> None:
            """取消订阅闭包：仅移除本次注册的那个 handler 实例。"""
            # 仅移除首个匹配项，避免误删同函数的多次订阅
            handlers = self._subscribers[topic]
            try:
                handlers.remove(handler)
            except ValueError:
                # 已移除或未注册：静默忽略，保证幂等
                pass

        return _unsubscribe

    def publish(self, event: Event) -> None:
        """发布一个事件到总线。

        按 FIFO 顺序同步调用该 topic 下所有 handler。handler 异常被捕获
        并记入死信队列，不中断后续 handler。事件本身无论是否有订阅者
        都会记入历史记录。

        Args:
            event: 待发布事件，``event.event_type`` 决定 topic。
        """
        # 先入历史，再投递：保证即使所有 handler 失败，回放仍可查到
        self._history.append(event)
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - 总线必须隔离 handler 异常
                # 死信：记录事件与异常描述，不向上抛
                self._dead_letters.append((event, repr(exc)))

    def history(
        self,
        topic: EventType | None = None,
        task_id: str | None = None,
    ) -> list[Event]:
        """查询历史事件。

        支持按 topic 与 task_id 过滤，便于回放时定位特定任务的事件序列。

        Args:
            topic: 可选，仅返回该类型的事件；None 表示不过滤。
            task_id: 可选，仅返回该任务的事件；None 表示不过滤。

        Returns:
            按发布时间排序的事件列表（旧在前）。
        """
        result = list(self._history)
        if topic is not None:
            result = [e for e in result if e.event_type == topic]
        if task_id is not None:
            result = [e for e in result if e.task_id == task_id]
        return result

    def dead_letters(self) -> list[tuple[Event, str]]:
        """返回死信队列（handler 抛异常的事件与异常描述）。

        Returns:
            ``(event, exception_repr)`` 元组列表，按发生顺序排列。
        """
        return list(self._dead_letters)

    def clear(self) -> None:
        """清空历史记录与死信队列（订阅者保留）。

        主要用于测试间隔离或会话边界重置。
        """
        self._history.clear()
        self._dead_letters.clear()
