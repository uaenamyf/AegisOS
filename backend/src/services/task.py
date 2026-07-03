# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 TaskService（实现 backend.api.TaskAPI，调用 agents.api.RuntimeAPI mock）
from __future__ import annotations

from agents.api import RuntimeAPI
from backend.src.mappers.repositories import TaskRepository
from protocol import Task, TaskStatus


class TaskService:
    """Implements ``backend.src.api.TaskAPI`` backed by ``TaskRepository`` + ``RuntimeAPI``."""

    def __init__(self, repo: TaskRepository, runtime: RuntimeAPI) -> None:
        self._repo = repo
        self._runtime = runtime

    async def create_task(self, goal: str, session_id: str) -> Task:
        task = Task(goal=goal)
        # Delegate execution to the agents runtime (mock for now) — it may
        # mutate the task in place (status/plan), so persist *after* submit.
        submitted = self._runtime.submit(task)
        await self._repo.create(submitted, session_id)
        return submitted

    async def get_task(self, task_id: str) -> Task | None:
        entity = await self._repo.get(task_id)
        if entity is None:
            return None
        return await self._repo.to_task(entity)

    async def list_tasks(self, session_id: str) -> list[Task]:
        entities = await self._repo.list_by_session(session_id)
        return [await self._repo.to_task(e) for e in entities]

    async def cancel_task(self, task_id: str) -> bool:
        entity = await self._repo.get(task_id)
        if entity is None:
            return False
        current = TaskStatus(entity.status)
        if current in (
            TaskStatus.Succeeded,
            TaskStatus.Failed,
            TaskStatus.Cancelled,
            TaskStatus.RolledBack,
        ):
            return False
        return await self._repo.update_status(task_id, TaskStatus.Cancelled)
