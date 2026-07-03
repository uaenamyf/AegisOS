# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 memory 控制器 GET/POST /memory/{session}
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.src.composition import MemoryServiceDep
from backend.src.controllers.schemas import MemoryResponse, WriteMemoryRequest
from protocol import MemoryPacket

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{session_id}", response_model=MemoryResponse)
async def read_memory(
    session_id: str,
    service: MemoryServiceDep,
) -> MemoryResponse:
    packet = await service.read_memory(session_id)
    return MemoryResponse(
        working=packet.working,
        semantic=packet.semantic,
        episodic=packet.episodic,
        archive=packet.archive,
        summary=packet.summary,
        session_id=packet.session_id,
    )


@router.post("/{session_id}")
async def write_memory(
    session_id: str,
    body: WriteMemoryRequest,
    service: MemoryServiceDep,
) -> dict[str, Any]:
    packet = MemoryPacket(
        working=body.working,
        semantic=body.semantic,
        episodic=body.episodic,
        archive=body.archive,
        summary=body.summary,
        task_id=body.task_id,
    )
    ok = await service.write_memory(session_id, packet)
    if not ok:
        raise HTTPException(
            status_code=500, detail={"code": "WRITE_FAILED", "message": "memory write failed"}
        )
    return {"written": True}
