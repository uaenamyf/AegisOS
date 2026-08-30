# date: 2026-07-05
# dev: myf
"""MockEventBusAPI — agents.api.EventBusAPI 的内存占位实现。"""

from __future__ import annotations

import contextlib
from typing import Any

from protocol import Event


class MockEventBusAPI:
    """``agents.api.EventBusAPI`` 的占位实现，基于内存的 topic/handler 注册表。"""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Any]] = {}
        self._event_log: list[Event] = []

    def publish(self, event: Event) -> None:
        """发布事件：记入日志并调用订阅该 topic 的所有处理器。"""
        self._event_log.append(event)
        for handler in self._subscriptions.get(event.topic, []):
            with contextlib.suppress(Exception):
                handler(event)

    def subscribe(self, topic: str, handler: Any) -> None:
        """订阅指定 topic（接口对齐：无返回值）。"""
        self._subscriptions.setdefault(topic, []).append(handler)

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅（mock 实现总是返回成功）。"""
        return True

    def recent_events(self, limit: int = 100) -> list[Event]:
        """返回最近 ``limit`` 条事件。"""
        return list(self._event_log[-limit:])
