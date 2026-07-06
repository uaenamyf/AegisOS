# date: 2026-06-27
# dev: myf
"""仓储模块：基于 SQLAlchemy AsyncSession 实现会话与任务的 CRUD 操作。"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.converters import entity_to_task, task_to_entity
from backend.models.entities import SessionEntity, TaskEntity
from protocol import Task, TaskStatus


def _rowcount(result: Any) -> int:
    """从 DML 结果对象中提取受影响的行数。

    SQLAlchemy 的结果在静态类型层面是 ``Result``，但 SQLite 异步驱动
    实际返回 ``CursorResult``，此处通过 cast 安全提取 rowcount。

    Args:
        result: DML 语句执行后的结果对象。

    Returns:
        受影响的行数。
    """
    return cast(CursorResult[Any], result).rowcount


class SessionRepository:
    """会话聚合的 CRUD 仓储。

    Attributes:
        _session_factory: 异步会话工厂，用于创建数据库会话。
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self, session_id: str, user_id: str, context: dict[str, Any] | None = None
    ) -> SessionEntity:
        """创建新的会话记录。

        Args:
            session_id: 会话唯一标识符。
            user_id: 关联的用户 ID。
            context: 会话上下文数据，默认为空字典。

        Returns:
            创建并刷新后的 ``SessionEntity`` 实体。
        """
        entity = SessionEntity(id=session_id, user_id=user_id, context=context or {})
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)  # 刷新以获取服务端生成的默认值
            return entity

    async def get(self, session_id: str) -> SessionEntity | None:
        """根据会话 ID 查询会话。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            ``SessionEntity`` 实体；若不存在则返回 ``None``。
        """
        async with self._session_factory() as session:
            return await session.get(SessionEntity, session_id)

    async def update_status(self, session_id: str, status: str) -> bool:
        """更新会话状态。

        Args:
            session_id: 会话唯一标识符。
            status: 新的会话状态字符串。

        Returns:
            更新成功返回 ``True``，会话不存在则返回 ``False``。
        """
        async with self._session_factory() as session:
            result = await session.execute(
                update(SessionEntity).where(SessionEntity.id == session_id).values(status=status)
            )
            await session.commit()
            return _rowcount(result) > 0

    async def delete(self, session_id: str) -> bool:
        """删除指定会话。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            删除成功返回 ``True``，会话不存在则返回 ``False``。
        """
        async with self._session_factory() as session:
            result = await session.execute(
                delete(SessionEntity).where(SessionEntity.id == session_id)
            )
            await session.commit()
            return _rowcount(result) > 0


class TaskRepository:
    """任务聚合的 CRUD 仓储。

    Attributes:
        _session_factory: 异步会话工厂，用于创建数据库会话。
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, task: Task, session_id: str) -> TaskEntity:
        """创建新的任务记录。

        Args:
            task: protocol 层的任务对象。
            session_id: 任务所属的会话 ID。

        Returns:
            创建并刷新后的 ``TaskEntity`` 实体。
        """
        entity = task_to_entity(task, session_id)
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def get(self, task_id: str) -> TaskEntity | None:
        """根据任务 ID 查询任务。

        Args:
            task_id: 任务唯一标识符。

        Returns:
            ``TaskEntity`` 实体；若不存在则返回 ``None``。
        """
        async with self._session_factory() as session:
            return await session.get(TaskEntity, task_id)

    async def list_by_session(self, session_id: str) -> list[TaskEntity]:
        """列出指定会话下的所有任务。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            该会话下的 ``TaskEntity`` 列表。
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(TaskEntity).where(TaskEntity.session_id == session_id)
            )
            return list(result.scalars().all())

    async def update_status(self, task_id: str, status: TaskStatus | str) -> bool:
        """更新任务状态。

        Args:
            task_id: 任务唯一标识符。
            status: 新的任务状态，可为 ``TaskStatus`` 枚举或字符串。

        Returns:
            更新成功返回 ``True``，任务不存在则返回 ``False``。
        """
        # 枚举转为值字符串，字符串则直接使用
        value = status.value if isinstance(status, TaskStatus) else str(status)
        async with self._session_factory() as session:
            result = await session.execute(
                update(TaskEntity).where(TaskEntity.id == task_id).values(status=value)
            )
            await session.commit()
            return _rowcount(result) > 0

    async def update_result(self, task_id: str, result: dict[str, Any]) -> bool:
        """更新任务结果，采用合并策略而非覆盖。

        将新结果字典合并到已有结果中，保留原有字段。

        Args:
            task_id: 任务唯一标识符。
            result: 待合并的结果字典。

        Returns:
            合并成功返回 ``True``，任务不存在则返回 ``False``。
        """
        async with self._session_factory() as session:
            existing = await session.get(TaskEntity, task_id)
            if existing is None:
                return False
            merged: dict[str, Any] = dict(existing.result or {})  # 浅拷贝已有结果
            merged.update(result)  # 合并新结果
            await session.execute(
                update(TaskEntity).where(TaskEntity.id == task_id).values(result=merged)
            )
            await session.commit()
            return True

    async def delete(self, task_id: str) -> bool:
        """删除指定任务。

        Args:
            task_id: 任务唯一标识符。

        Returns:
            删除成功返回 ``True``，任务不存在则返回 ``False``。
        """
        async with self._session_factory() as session:
            result = await session.execute(delete(TaskEntity).where(TaskEntity.id == task_id))
            await session.commit()
            return _rowcount(result) > 0

    async def to_task(self, entity: TaskEntity) -> Task:
        """将 ``TaskEntity`` 转换为 protocol 层的 ``Task``。

        Args:
            entity: 数据库中的任务实体行。

        Returns:
            转换后的 protocol 层 ``Task`` 对象。
        """
        return entity_to_task(entity)
