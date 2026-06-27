# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 tasks 控制器 POST/GET /tasks、POST /tasks/{id}/cancel
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.composition import TaskServiceDep
from backend.controllers.schemas import CreateTaskRequest, TaskResponse
from protocol import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status.value,
        plan=task.plan or {},
        priority=task.priority,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: CreateTaskRequest,
    service: TaskServiceDep,
) -> TaskResponse:
    if not body.goal.strip():
        raise HTTPException(
            status_code=400, detail={"code": "INVALID_GOAL", "message": "goal must not be empty"}
        )
    task = await service.create_task(body.goal, body.session_id)
    return _task_to_response(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    service: TaskServiceDep,
    session_id: str = Query(..., description="Filter tasks by session id"),
) -> list[TaskResponse]:
    tasks = await service.list_tasks(session_id)
    return [_task_to_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    service: TaskServiceDep,
) -> TaskResponse:
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"task {task_id} not found"}
        )
    return _task_to_response(task)


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    service: TaskServiceDep,
) -> dict[str, Any]:
    cancelled = await service.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail={"code": "NOT_CANCELLABLE", "message": f"task {task_id} cannot be cancelled"},
        )
    return {"cancelled": True}
