# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建转换器——protocol Task <-> TaskEntity、session dict <-> SessionEntity
from __future__ import annotations

from typing import Any

from backend.src.mappers.entities import SessionEntity, TaskEntity
from protocol import Task, TaskStatus


def task_to_entity(task: Task, session_id: str) -> TaskEntity:
    """Convert a protocol ``Task`` into a persistable ``TaskEntity``."""
    return TaskEntity(
        id=task.task_id,
        session_id=session_id,
        goal=task.goal,
        status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
        plan=task.plan or {},
        result={},
    )


def entity_to_task(entity: TaskEntity) -> Task:
    """Reconstruct a protocol ``Task`` from a ``TaskEntity`` row."""
    return Task(
        task_id=entity.id,
        goal=entity.goal,
        status=TaskStatus(entity.status),
        plan=entity.plan or {},
        priority=0,
    )


def session_dict_to_entity(data: dict[str, Any]) -> SessionEntity:
    """Convert a session dict into a persistable ``SessionEntity``."""
    return SessionEntity(
        id=data["id"],
        user_id=data.get("user_id", ""),
        status=data.get("status", "active"),
        context=data.get("context", {}),
    )


def entity_to_session_dict(entity: SessionEntity) -> dict[str, Any]:
    """Reconstruct a plain session dict from a ``SessionEntity`` row."""
    return {
        "id": entity.id,
        "user_id": entity.user_id,
        "status": entity.status,
        "context": entity.context or {},
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }
