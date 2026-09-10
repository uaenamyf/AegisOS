# date: 2026-09-10
# dev: myf
"""任务服务后台执行、结果持久化与 Agent 事件发布测试。"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.services.task_service import TaskService
from protocol import EventType, Task, TaskStatus


class FakeRepository:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.results: dict[str, dict[str, Any]] = {}

    async def create(self, task: Task, session_id: str) -> None:
        self.tasks[task.task_id] = task

    async def update_result(self, task_id: str, result: dict[str, Any]) -> bool:
        self.results.setdefault(task_id, {}).update(result)
        return True

    async def update_status(self, task_id: str, status: TaskStatus) -> bool:
        self.tasks[task_id].status = status
        return True


class FakeRuntime:
    def submit(self, task: Task) -> Task:
        task.status = TaskStatus.Running
        return task

    def run(self, agent_id: str, task: Task) -> dict[str, Any]:
        return {"agent_id": agent_id, "assets": [{"host": "10.0.0.8"}]}


class FakeEventBus:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event: Any) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_create_task_executes_and_persists_result() -> None:
    repository = FakeRepository()
    event_bus = FakeEventBus()
    service = TaskService(repository, FakeRuntime(), event_bus)

    task = await service.create_task("分析演示资产暴露面", "session-1")
    await asyncio.sleep(0.05)

    assert task.status in (TaskStatus.Running, TaskStatus.Succeeded)
    assert repository.tasks[task.task_id].status is TaskStatus.Succeeded
    assert repository.results[task.task_id]["agent_id"] == "recon"
    assert [event.event_type for event in event_bus.events] == [
        EventType.AgentStart,
        EventType.AgentFinish,
    ]
    assert event_bus.events[-1].task_id == task.task_id
