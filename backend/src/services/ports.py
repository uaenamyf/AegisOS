# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 DI 端口实现——PersistencePortImpl / SessionPortImpl / TaskUpdatePortImpl，委托仓储
from __future__ import annotations

import uuid
from typing import Any

from backend.src.mappers.converters import entity_to_session_dict
from backend.src.mappers.repositories import SessionRepository, TaskRepository
from protocol import TaskStatus


class PersistencePortImpl:
    """Implements ``agents.api.ports.PersistencePort`` over ``TaskRepository``."""

    def __init__(self, task_repo: TaskRepository) -> None:
        self._repo = task_repo

    async def save_task_result(self, task_id: str, result: dict[str, Any]) -> bool:
        return await self._repo.update_result(task_id, result)

    async def save_artifact(self, task_id: str, name: str, content: bytes) -> str:
        artifact_id = uuid.uuid4().hex
        await self._repo.update_result(
            task_id, {"artifact": {"id": artifact_id, "name": name, "size": len(content)}}
        )
        return artifact_id


class SessionPortImpl:
    """Implements ``agents.api.ports.SessionPort`` over ``SessionRepository``."""

    def __init__(self, session_repo: SessionRepository) -> None:
        self._repo = session_repo

    async def get_session(self, session_id: str) -> dict[str, Any]:
        entity = await self._repo.get(session_id)
        return entity_to_session_dict(entity) if entity else {}

    async def get_user_context(self, session_id: str) -> dict[str, Any]:
        entity = await self._repo.get(session_id)
        if entity is None:
            return {}
        return {"user_id": entity.user_id, "context": entity.context or {}}


class TaskUpdatePortImpl:
    """Implements ``agents.api.ports.TaskUpdatePort`` over ``TaskRepository``."""

    def __init__(self, task_repo: TaskRepository) -> None:
        self._repo = task_repo

    async def update_status(self, task_id: str, status: TaskStatus | str) -> bool:
        return await self._repo.update_status(task_id, status)
