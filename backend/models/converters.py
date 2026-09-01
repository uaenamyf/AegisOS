# date: 2026-06-27
# dev: myf
"""转换器模块：在 protocol 层对象与 ORM 实体之间进行双向转换。"""

from __future__ import annotations

from typing import Any

from backend.models.entities import SessionEntity, TaskEntity
from protocol import Task, TaskStatus


def task_to_entity(task: Task, session_id: str) -> TaskEntity:
    """将 protocol 层的 ``Task`` 转换为可持久化的 ``TaskEntity``。

    Args:
        task: protocol 层的任务对象。
        session_id: 任务所属的会话 ID。

    Returns:
        转换后的 ``TaskEntity`` ORM 实体。
    """
    return TaskEntity(
        id=task.task_id,
        session_id=session_id,
        goal=task.goal,
        payload=task.payload or {},
        # 兼容处理：status 可能为枚举或字符串，统一转为字符串存储
        status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
        plan=task.plan or {},
        result={},
    )


def entity_to_task(entity: TaskEntity) -> Task:
    """从 ``TaskEntity`` 行重建 protocol 层的 ``Task``。

    Args:
        entity: 数据库中的任务实体行。

    Returns:
        重建后的 protocol 层 ``Task`` 对象。
    """
    return Task(
        task_id=entity.id,
        goal=entity.goal,
        payload=entity.payload or {},
        status=TaskStatus(entity.status),  # 将状态字符串解析回枚举
        plan=entity.plan or {},
        priority=0,
    )


def session_dict_to_entity(data: dict[str, Any]) -> SessionEntity:
    """将会话字典转换为可持久化的 ``SessionEntity``。

    Args:
        data: 包含会话信息的字典，必须包含 ``id`` 键。

    Returns:
        转换后的 ``SessionEntity`` ORM 实体。
    """
    return SessionEntity(
        id=data["id"],
        user_id=data.get("user_id", ""),
        status=data.get("status", "active"),
        context=data.get("context", {}),
    )


def entity_to_session_dict(entity: SessionEntity) -> dict[str, Any]:
    """从 ``SessionEntity`` 行重建普通会话字典。

    Args:
        entity: 数据库中的会话实体行。

    Returns:
        包含会话所有字段的字典，时间戳转为 ISO 格式字符串。
    """
    return {
        "id": entity.id,
        "user_id": entity.user_id,
        "status": entity.status,
        "context": entity.context or {},
        # datetime 对象转为 ISO 格式字符串，None 时返回 None
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }
