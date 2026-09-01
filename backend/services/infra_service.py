# date: 2026-08-27
# dev: ox-alpha
"""Infra 服务层 —— 封装 R5/R6 基础设施，供 REST 端点调用。

薄封装：不直接暴露 infrastructure 内部对象，只暴露 Pydantic-safe 响应。
"""

from __future__ import annotations

from collections import deque
from typing import Any

from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier
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

    def configure_nodes(self, configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """替换本地演示节点配置并重建调度器。"""
        profiles = [NodeProfile.model_validate(config) for config in configs]
        if not profiles:
            raise ValueError("at least one node profile is required")

        registry = NodeRegistry()
        for profile in profiles:
            registry.register_node(_ConfiguredDemoNode(profile))
        registry.tick()
        self.registry = registry
        self.dispatcher = ExecutionDispatcher(
            registry,
            enable_cascade=True,
            confidence_threshold=self.dispatcher.confidence_threshold,
        )
        return registry.snapshot()

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


class _ConfiguredDemoNode:
    """演示配置节点：保留参数并返回可重复的本地推理结果。"""

    def __init__(self, profile: NodeProfile) -> None:
        self.profile = profile

    def health(self, timeout_s: float = 3.0) -> bool:
        return self.profile.enabled

    def infer(self, prompt: str, *, system: str = "", **kwargs: Any) -> InferenceResult:
        tier = Tier(self.profile.tier).value
        return InferenceResult(
            ok=True,
            text=f"[{self.profile.model_id or self.profile.node_id}] {prompt[:200]}",
            node_id=self.profile.node_id,
            tier=tier,
            model_id=self.profile.model_id or self.profile.node_id,
            latency_ms=12.0,
            usage={"prompt_tokens": len(prompt), "completion_tokens": 0},
        )
