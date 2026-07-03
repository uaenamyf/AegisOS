# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 DI 端口定义，供智能体回调后端能力（持久化/会话/任务状态），由后端实现并注入
"""Agents domain DI ports — reverse-injection interfaces for backend capabilities.

These ports are consumed by the agents domain (runtime/action) and implemented
by the backend (backend/services/agent/ports.py). This achieves Dependency
Inversion (DIP): agents depend on its own domain abstraction, backend depends
on agents.api.ports (forward) and implements it — no reverse import of backend
from agents. See developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md §3.2.

Wiring happens in backend/composition.py (composition root).
"""

from __future__ import annotations

from typing import Protocol

from protocol import TaskStatus


class PersistencePort(Protocol):
    """Persistence capability exposed to agents for task results and artifacts."""

    def save_task_result(self, task_id: str, result: dict) -> bool: ...
    def save_artifact(self, task_id: str, name: str, content: bytes) -> str: ...


class SessionPort(Protocol):
    """Session/user context capability exposed to agents."""

    def get_session(self, session_id: str) -> dict: ...
    def get_user_context(self, session_id: str) -> dict: ...


class TaskUpdatePort(Protocol):
    """Task status write-back capability exposed to agents."""

    def update_status(self, task_id: str, status: TaskStatus) -> bool: ...


__all__ = ["PersistencePort", "SessionPort", "TaskUpdatePort"]
