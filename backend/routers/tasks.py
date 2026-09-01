# date: 2026-06-27
# dev: myf
"""任务控制器。

提供任务创建、查询、列表与取消的 REST 端点。任务是 Agent 调度的
基本单元，归属某个会话，携带自然语言目标与执行计划。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.core.composition import TaskServiceDep
from backend.schemas import CreateTaskRequest, TaskResponse
from protocol import Task

# 任务路由器，统一前缀 /tasks，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_response(task: Task) -> TaskResponse:
    """将协议层 Task 转换为 API 响应模型。

    Args:
        task: 协议层任务对象。

    Returns:
        转换后的 TaskResponse，状态字段取枚举的字符串值。
    """
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        payload=task.payload or {},
        status=task.status.value,
        plan=task.plan or {},
        priority=task.priority,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: CreateTaskRequest,
    service: TaskServiceDep,
) -> TaskResponse:
    """创建新任务。

    在指定会话下创建一个任务，目标不得为空白字符串。
    创建成功响应 HTTP 201。

    Args:
        body: 创建任务请求体，包含目标与会话 ID。
        service: 任务服务依赖，负责任务持久化与调度。

    Returns:
        新建任务的响应对象。

    Raises:
        HTTPException: 当 goal 为空白时返回 400 INVALID_GOAL。
    """
    if not body.goal.strip():
        raise HTTPException(
            status_code=400, detail={"code": "INVALID_GOAL", "message": "goal must not be empty"}
        )
    task = await service.create_task(body.goal, body.session_id, body.payload)
    return _task_to_response(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    service: TaskServiceDep,
    session_id: str = Query(..., description="Filter tasks by session id"),
) -> list[TaskResponse]:
    """列出某会话下的全部任务。

    Args:
        service: 任务服务依赖。
        session_id: 会话 ID，必填，用于过滤任务列表。

    Returns:
        该会话下所有任务对应的响应对象列表。
    """
    tasks = await service.list_tasks(session_id)
    return [_task_to_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    service: TaskServiceDep,
) -> TaskResponse:
    """查询单个任务详情。

    Args:
        task_id: 待查询的任务唯一标识。
        service: 任务服务依赖。

    Returns:
        对应任务的响应对象。

    Raises:
        HTTPException: 任务不存在时返回 404 NOT_FOUND。
    """
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
    """取消指定任务。

    尝试将任务状态变更为已取消；仅处于可取消状态的任务可被取消。

    Args:
        task_id: 待取消的任务唯一标识。
        service: 任务服务依赖。

    Returns:
        包含 ``cancelled: True`` 的字典，表示取消成功。

    Raises:
        HTTPException: 当任务不存在或当前状态不可取消时返回
            409 NOT_CANCELLABLE。
    """
    cancelled = await service.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail={"code": "NOT_CANCELLABLE", "message": f"task {task_id} cannot be cancelled"},
        )
    return {"cancelled": True}
