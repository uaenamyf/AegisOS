# date: 2026-06-27
# dev: myf
"""会话控制器。

提供会话生命周期的 REST 端点，包括创建会话、查询会话详情
以及关闭会话。会话是 Agent 任务执行的上下文容器，归属某个用户。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.composition import SessionServiceDep
from backend.schemas import CreateSessionRequest, SessionResponse

# 会话路由器，统一前缀 /sessions，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    service: SessionServiceDep,
) -> SessionResponse:
    """创建新会话。

    依据请求体中的用户标识创建会话，并立即返回会话详情。
    创建成功响应 HTTP 201。

    Args:
        body: 创建会话请求体，包含归属用户 ID。
        service: 会话服务依赖，负责会话持久化。

    Returns:
        新建会话的响应对象。

    Raises:
        HTTPException: 当创建后立即查询不到会话时（防御性检查，
            正常不应触发），返回 500 INTERNAL。
    """
    session_id = await service.create_session(body.user_id)
    session = await service.get_session(session_id)
    if session is None:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500, detail={"code": "INTERNAL", "message": "session vanished"}
        )
    return SessionResponse(**session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: SessionServiceDep,
) -> SessionResponse:
    """查询指定会话详情。

    Args:
        session_id: 待查询的会话唯一标识。
        service: 会话服务依赖，负责会话读取。

    Returns:
        对应会话的响应对象。

    Raises:
        HTTPException: 会话不存在时返回 404 NOT_FOUND。
    """
    session = await service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"session {session_id} not found"},
        )
    return SessionResponse(**session)


@router.delete("/{session_id}")
async def close_session(
    session_id: str,
    service: SessionServiceDep,
) -> dict[str, Any]:
    """关闭指定会话。

    将会话标记为关闭，释放其关联资源。此操作幂等。

    Args:
        session_id: 待关闭的会话唯一标识。
        service: 会话服务依赖，负责会话状态变更。

    Returns:
        包含 ``closed: True`` 的字典，表示关闭成功。

    Raises:
        HTTPException: 会话不存在或无法关闭时返回 404 NOT_FOUND。
    """
    closed = await service.close_session(session_id)
    if not closed:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"session {session_id} not found"},
        )
    return {"closed": True}
