# date: 2026-06-27
# dev: myf
# changelog: 新建 memory 控制器 GET/POST /memory/{session}
"""记忆控制器。

提供按会话读写 Agent 记忆包的 REST 端点，覆盖工作记忆、语义记忆、
情景记忆与归档等多层记忆形式，是外部系统访问 Agent 记忆的入口。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.composition import MemoryServiceDep
from backend.schemas import MemoryResponse, WriteMemoryRequest
from protocol import MemoryPacket

# 记忆路由器，统一前缀 /memory，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{session_id}", response_model=MemoryResponse)
async def read_memory(
    session_id: str,
    service: MemoryServiceDep,
) -> MemoryResponse:
    """读取指定会话的记忆包。

    Args:
        session_id: 会话唯一标识。
        service: 记忆服务依赖，负责记忆读取。

    Returns:
        对应会话的记忆响应对象，包含各层记忆内容与摘要。
    """
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
    """写入指定会话的记忆包。

    将请求体中的各层记忆内容组装为 MemoryPacket 后整体写入，
    覆盖该会话原有记忆。

    Args:
        session_id: 会话唯一标识。
        body: 写入记忆请求体，包含各层记忆内容。
        service: 记忆服务依赖，负责记忆持久化。

    Returns:
        包含 ``written: True`` 的字典，表示写入成功。

    Raises:
        HTTPException: 记忆写入失败时返回 500 WRITE_FAILED。
    """
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
