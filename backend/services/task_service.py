# date: 2026-06-27
# dev: myf
"""Task 服务层：实现任务 CRUD，并驱动后台 Agent 执行与结果回写。"""

from __future__ import annotations

import asyncio
from typing import Any

from aegisos_agents.api import RuntimeAPI
from aegisos_agents.memory.memory_store import MemoryStore
from backend.repositories.repositories import TaskRepository
from protocol import Event, EventType, NodeRef, Task, TaskStatus
from protocol.memory import MemoryPacket


class TaskService:
    """实现 ``backend.api.TaskAPI``，委托 ``TaskRepository`` 与 ``RuntimeAPI``。

    Attributes:
        _repo: 任务仓储，负责任务数据的持久化操作。
        _runtime: agent 运行时 API，负责任务的实际执行。
        _memory: 可选记忆存储，任务执行结果写入短期/情景记忆（普通任务记忆闭环）。
    """

    def __init__(
        self,
        repo: TaskRepository,
        runtime: RuntimeAPI,
        event_bus: Any = None,
        memory: MemoryStore | None = None,
    ) -> None:
        self._repo = repo
        self._runtime = runtime
        self._event_bus = event_bus
        self._memory = memory

    async def create_task(
        self,
        goal: str,
        session_id: str,
        payload: dict[str, object] | None = None,
        plan: dict[str, object] | None = None,
        dependency: list[str] | None = None,
        priority: int = 0,
    ) -> Task:
        """创建并提交任务。

        将任务提交后交给后台 Agent 执行，执行结果、状态和生命周期事件
        通过现有仓储与事件总线写回。

        Args:
            goal: 任务目标描述。
            session_id: 关联的会话 ID。

        Returns:
            提交并持久化后的 ``Task`` 对象。
        """
        task = Task(
            goal=goal,
            payload=payload or {},
            plan=plan or {},
            dependency=dependency or [],
            priority=priority,
        )
        # 委托 agents 运行时执行任务（当前为 mock），运行时可能就地修改
        # task 的 status/plan，因此在提交之后再持久化。
        submitted = self._runtime.submit(task)
        await self._repo.create(submitted, session_id)
        asyncio.create_task(self._execute(submitted, session_id))
        return submitted

    async def _execute(self, task: Task, session_id: str = "") -> None:
        """在任务持久化后执行 Agent，并发布可观测生命周期事件。"""
        agent_id = self._select_agent(task)
        self._publish(
            Event(
                event_type=EventType.AgentStart,
                task_id=task.task_id,
                source=NodeRef(agent_id, "agent", agent_id),
                payload={"agent_id": agent_id, "goal": task.goal, "session_id": session_id},
            )
        )
        try:
            output = await asyncio.to_thread(self._runtime.run, agent_id, task)
            result = output if isinstance(output, dict) else {"output": output}
            await self._repo.update_result(task.task_id, result)
            await self._repo.update_status(task.task_id, TaskStatus.Succeeded)
            # R-mem: 任务成功完成即写入记忆——普通任务链路纳入认知闭环，
            # 供后续 recall 唤醒复用（见 MEMORY_REFACTOR_REPORT 问题 6）。
            self._write_task_memory(task, agent_id, session_id, result, succeeded=True)
            self._publish(
                Event(
                    event_type=EventType.AgentFinish,
                    task_id=task.task_id,
                    source=NodeRef(agent_id, "agent", agent_id),
                    payload={"agent_id": agent_id, "output": result, "session_id": session_id},
                )
            )
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc), "agent_id": agent_id}
            await self._repo.update_result(task.task_id, result)
            await self._repo.update_status(task.task_id, TaskStatus.Failed)
            self._write_task_memory(task, agent_id, session_id, result, succeeded=False)
            self._publish(
                Event(
                    event_type=EventType.AgentFinish,
                    task_id=task.task_id,
                    source=NodeRef(agent_id, "agent", agent_id),
                    payload={"agent_id": agent_id, "output": result, "status": "failed", "session_id": session_id},
                )
            )

    def _write_task_memory(
        self,
        task: Task,
        agent_id: str,
        session_id: str,
        result: dict[str, Any],
        *,
        succeeded: bool,
    ) -> None:
        """把任务执行结论写入共享记忆存储（MemoryStore 单例）。

        决策类任务（kind="decision"）会自动路由到情景记忆，变成可被
        ``recall()`` 唤醒的长期经验；其余写入工作记忆。无记忆时不抛错。
        """
        if self._memory is None:
            return
        try:
            self._memory.write(
                MemoryPacket(
                    session_id=session_id,
                    task_id=task.task_id,
                    kind="decision" if succeeded else "normal",
                    summary=(
                        f"[task] {agent_id} {'完成' if succeeded else '失败'}: {task.goal}"
                    ),
                    working={
                        "agent_id": agent_id,
                        "goal": task.goal,
                        "status": "succeeded" if succeeded else "failed",
                    },
                    episodic={"task": task.task_id, "agent_id": agent_id} if succeeded else {},
                )
            )
        except Exception:  # noqa: BLE001 —— 记忆写入失败不应阻断主任务
            pass

    @staticmethod
    def _select_agent(task: Task) -> str:
        """按显式 payload 或目标语义选择默认演示 Agent。"""
        requested = task.payload.get("agent_id") or task.payload.get("agent")
        if requested:
            return str(requested)
        goal = task.goal.lower()
        if any(word in goal for word in ("检测", "告警", "入侵", "detect", "alert")):
            return "detector"
        if any(word in goal for word in ("审查", "复核", "一致", "review", "audit")):
            return "reviewer-defense"
        return "recon"

    def _publish(self, event: Event) -> None:
        """向已装配的事件总线发布事件；无事件总线时保持兼容。"""
        if self._event_bus is not None:
            self._event_bus.publish(event)

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
