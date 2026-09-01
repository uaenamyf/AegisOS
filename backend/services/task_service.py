# date: 2026-06-27
# dev: myf
"""Task 服务层：实现任务的创建、查询、列表与取消，委托运行时执行。"""

from __future__ import annotations

from aegisos_agents.api import RuntimeAPI
from backend.repositories.repositories import TaskRepository
from protocol import Task, TaskStatus


class TaskService:
    """实现 ``backend.api.TaskAPI``，委托 ``TaskRepository`` 与 ``RuntimeAPI``。

    Attributes:
        _repo: 任务仓储，负责任务数据的持久化操作。
        _runtime: agent 运行时 API，负责任务的实际执行。
    """

    def __init__(self, repo: TaskRepository, runtime: RuntimeAPI) -> None:
        self._repo = repo
        self._runtime = runtime

    async def create_task(
        self, goal: str, session_id: str, payload: dict[str, object] | None = None
    ) -> Task:
        """创建并提交任务。

        将任务委托给 agents 运行时执行（当前为 mock），运行时可能就地修改
        任务的状态和计划，因此持久化在提交之后进行。

        Args:
            goal: 任务目标描述。
            session_id: 关联的会话 ID。

        Returns:
            提交并持久化后的 ``Task`` 对象。
        """
        task = Task(goal=goal, payload=payload or {})
        # 委托 agents 运行时执行任务（当前为 mock），运行时可能就地修改
        # task 的 status/plan，因此在提交之后再持久化。
        submitted = self._runtime.submit(task)
        await self._repo.create(submitted, session_id)
        return submitted

    async def get_task(self, task_id: str) -> Task | None:
        """获取指定任务。

        Args:
            task_id: 任务唯一标识符。

        Returns:
            ``Task`` 对象；若任务不存在则返回 ``None``。
        """
        entity = await self._repo.get(task_id)
        if entity is None:
            return None
        return await self._repo.to_task(entity)

    async def list_tasks(self, session_id: str) -> list[Task]:
        """列出指定会话下的所有任务。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            该会话下的任务列表。
        """
        entities = await self._repo.list_by_session(session_id)
        return [await self._repo.to_task(e) for e in entities]

    async def cancel_task(self, task_id: str) -> bool:
        """取消指定任务。

        若任务已处于终态（成功、失败、已取消、已回滚），则不可取消。

        Args:
            task_id: 任务唯一标识符。

        Returns:
            取消成功返回 ``True``；任务不存在或已处于终态则返回 ``False``。
        """
        entity = await self._repo.get(task_id)
        if entity is None:
            return False
        current = TaskStatus(entity.status)  # 解析当前任务状态
        # 已处于终态的任务不可取消
        if current in (
            TaskStatus.Succeeded,
            TaskStatus.Failed,
            TaskStatus.Cancelled,
            TaskStatus.RolledBack,
        ):
            return False
        return await self._repo.update_status(task_id, TaskStatus.Cancelled)
