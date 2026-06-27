# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 sessions 控制器 POST/GET/DELETE /sessions
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.composition import SessionServiceDep
from backend.controllers.schemas import CreateSessionRequest, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    service: SessionServiceDep,
) -> SessionResponse:
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
    closed = await service.close_session(session_id)
    if not closed:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"session {session_id} not found"},
        )
    return {"closed": True}
