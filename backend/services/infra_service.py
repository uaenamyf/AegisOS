# date: 2026-08-27
# dev: ox-alpha
"""Infra 服务层 —— 封装 R5/R6 基础设施，供 REST 端点调用。

薄封装：不直接暴露 infrastructure 内部对象，只暴露 Pydantic-safe 响应。
"""

from __future__ import annotations

from collections import deque
from typing import Any

from infrastructure.nodes.descriptor import InferenceResult
from infrastructure.nodes.dispatcher import ExecutionDispatcher
from infrastructure.nodes.registry import NodeRegistry
from protocol.scheduler import Task


class InfraService:
    """封装 NodeRegistry 与 ExecutionDispatcher，提供面向 API 的操作。

    Attributes:
        registry: 节点注册中心（全局单例）。
        dispatcher: 执行派发器（全局单例）。
        _history: 派发历史环形缓冲（最近 100 条）。
    """

    def __init__(
        self,
        registry: NodeRegistry,
        dispatcher: ExecutionDispatcher,
    ) -> None:
        self.registry = registry
        self.dispatcher = dispatcher
        self._history: deque[dict[str, Any]] = deque(maxlen=100)

    def list_nodes(self) -> list[dict[str, Any]]:
        """返回所有节点快照（在线状态 + 档案）。"""
        return self.registry.snapshot()

    def dispatch(
        self,
        goal: str,
        latency_budget: float = 1.0,
        privacy: str = "standard",
        capability: str | None = None,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """构造 Task 并派发，返回 InferenceResult 摘要。

        Returns:
            含 ok/text/tier/privacy_note/attempts 的字典。
        """
        task = Task(goal=goal, latency_budget=latency_budget, privacy=privacy)
        result: InferenceResult = self.dispatcher.dispatch(
            task,
            goal,
            required_capability=capability,
            system_prompt=system_prompt,
        )

        entry = {
            "ok": result.ok,
            "text": result.text[:200] if result.text else "",
            "tier": result.tier,
            "node_id": result.node_id,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "privacy_note": result.privacy_note,
            "attempts": result.attempts,
            "goal": goal,
            "privacy": task.privacy,
        }
        self._history.appendleft(entry)
        return entry

    def dispatch_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """返回最近 N 条派发记录。"""
        return list(self._history)[:limit]