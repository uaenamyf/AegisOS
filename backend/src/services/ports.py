# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 DI 端口实现——PersistencePortImpl / SessionPortImpl / TaskUpdatePortImpl，委托仓储
"""DI 端口实现层：将 agents 定义的端口接口委托到后端仓储实现。"""

from __future__ import annotations

import uuid
from typing import Any

from backend.src.mappers.converters import entity_to_session_dict
from backend.src.mappers.repositories import SessionRepository, TaskRepository
from protocol import TaskStatus


class PersistencePortImpl:
    """实现 ``agents.api.ports.PersistencePort``，委托 ``TaskRepository`` 持久化。

    Attributes:
        _repo: 任务仓储，负责任务结果与产物的持久化。
    """

    def __init__(self, task_repo: TaskRepository) -> None:
        self._repo = task_repo

    async def save_task_result(self, task_id: str, result: dict[str, Any]) -> bool:
        """保存任务执行结果。

        Args:
            task_id: 任务唯一标识符。
            result: 任务结果字典。

        Returns:
            更新成功返回 ``True``，否则返回 ``False``。
        """
        return await self._repo.update_result(task_id, result)

    async def save_artifact(self, task_id: str, name: str, content: bytes) -> str:
        """保存任务产物（artifact）的元信息。

        产物内容本身不直接存储，仅记录其 ID、名称和大小到任务结果中。

        Args:
            task_id: 任务唯一标识符。
            name: 产物名称。
            content: 产物内容的字节流。

        Returns:
            生成的产物唯一标识符（artifact_id）。
        """
        artifact_id = uuid.uuid4().hex  # 生成产物唯一 ID
        await self._repo.update_result(
            task_id, {"artifact": {"id": artifact_id, "name": name, "size": len(content)}}
        )
        return artifact_id


class SessionPortImpl:
    """实现 ``agents.api.ports.SessionPort``，委托 ``SessionRepository`` 读取会话。

    Attributes:
        _repo: 会话仓储，负责会话数据的读取。
    """

    def __init__(self, session_repo: SessionRepository) -> None:
        self._repo = session_repo

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """获取指定会话的完整信息。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            会话信息字典；若会话不存在则返回空字典。
        """
        entity = await self._repo.get(session_id)
        return entity_to_session_dict(entity) if entity else {}

    async def get_user_context(self, session_id: str) -> dict[str, Any]:
        """获取指定会话关联的用户上下文。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            包含 ``user_id`` 和 ``context`` 的字典；若会话不存在则返回空字典。
        """
        entity = await self._repo.get(session_id)
        if entity is None:
            return {}
        return {"user_id": entity.user_id, "context": entity.context or {}}


class TaskUpdatePortImpl:
    """实现 ``agents.api.ports.TaskUpdatePort``，委托 ``TaskRepository`` 更新任务状态。

    Attributes:
        _repo: 任务仓储，负责任务状态的更新。
    """

    def __init__(self, task_repo: TaskRepository) -> None:
        self._repo = task_repo

    async def update_status(self, task_id: str, status: TaskStatus | str) -> bool:
        """更新任务状态。

        Args:
            task_id: 任务唯一标识符。
            status: 新的任务状态，可为 ``TaskStatus`` 枚举或字符串。

        Returns:
            更新成功返回 ``True``，否则返回 ``False``。
        """
        return await self._repo.update_status(task_id, status)
