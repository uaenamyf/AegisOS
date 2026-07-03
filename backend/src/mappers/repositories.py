# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建仓储类——SessionRepository / TaskRepository（CRUD，SQLAlchemy AsyncSession）
from __future__ import annotations

from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.src.mappers.converters import entity_to_task, task_to_entity
from backend.src.mappers.entities import SessionEntity, TaskEntity
from protocol import Task, TaskStatus


def _rowcount(result: Any) -> int:
    """Return the affected row count from a DML result (typed as Result at rest)."""
    return cast(CursorResult[Any], result).rowcount


class SessionRepository:
    """CRUD repository for session aggregates."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self, session_id: str, user_id: str, context: dict[str, Any] | None = None
    ) -> SessionEntity:
        entity = SessionEntity(id=session_id, user_id=user_id, context=context or {})
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def get(self, session_id: str) -> SessionEntity | None:
        async with self._session_factory() as session:
            return await session.get(SessionEntity, session_id)

    async def update_status(self, session_id: str, status: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                update(SessionEntity).where(SessionEntity.id == session_id).values(status=status)
            )
            await session.commit()
            return _rowcount(result) > 0

    async def delete(self, session_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(SessionEntity).where(SessionEntity.id == session_id)
            )
            await session.commit()
            return _rowcount(result) > 0


class TaskRepository:
    """CRUD repository for task aggregates."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, task: Task, session_id: str) -> TaskEntity:
        entity = task_to_entity(task, session_id)
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def get(self, task_id: str) -> TaskEntity | None:
        async with self._session_factory() as session:
            return await session.get(TaskEntity, task_id)

    async def list_by_session(self, session_id: str) -> list[TaskEntity]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TaskEntity).where(TaskEntity.session_id == session_id)
            )
            return list(result.scalars().all())

    async def update_status(self, task_id: str, status: TaskStatus | str) -> bool:
        value = status.value if isinstance(status, TaskStatus) else str(status)
        async with self._session_factory() as session:
            result = await session.execute(
                update(TaskEntity).where(TaskEntity.id == task_id).values(status=value)
            )
            await session.commit()
            return _rowcount(result) > 0

    async def update_result(self, task_id: str, result: dict[str, Any]) -> bool:
        async with self._session_factory() as session:
            existing = await session.get(TaskEntity, task_id)
            if existing is None:
                return False
            merged: dict[str, Any] = dict(existing.result or {})
            merged.update(result)
            await session.execute(
                update(TaskEntity).where(TaskEntity.id == task_id).values(result=merged)
            )
            await session.commit()
            return True

    async def delete(self, task_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(delete(TaskEntity).where(TaskEntity.id == task_id))
            await session.commit()
            return _rowcount(result) > 0

    async def to_task(self, entity: TaskEntity) -> Task:
        return entity_to_task(entity)
