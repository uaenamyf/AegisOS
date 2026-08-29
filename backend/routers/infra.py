# date: 2026-08-27
# dev: ox-alpha
"""Infra 控制器 —— 暴露端边云基础设施的 REST API。

端点：
- GET  /api/v1/infra/nodes          → 节点列表+在线状态
- POST /api/v1/infra/dispatch       → 派发任务
- GET  /api/v1/infra/dispatch/history → 派发历史
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import verify_api_key
from backend.services.infra_service import InfraService

router = APIRouter(prefix="/infra", tags=["infra"], dependencies=[Depends(verify_api_key)])


# ---- Schema ----

class DispatchRequest(BaseModel):
    """派发任务请求体。"""

    goal: str = Field(..., description="任务目标描述")
    latency_budget: float = Field(default=1.0, ge=0.1, le=30.0, description="延迟预算（秒）")
    privacy: str = Field(default="standard", description="隐私级别：local/standard/unrestricted")
    capability: str | None = Field(default=None, description="能力过滤")
    system_prompt: str = Field(default="", description="系统提示")  # noqa: PIE110


# ---- Endpoints ----

def _get_service() -> InfraService:
    from backend.main import _infra_service

    if _infra_service is None:
        raise HTTPException(status_code=503, detail={"code": "SERVICE_UNAVAILABLE", "message": "infra service not initialized"})
    return _infra_service


@router.get("/nodes")
async def list_nodes() -> list[dict[str, Any]]:
    """列出所有端边云节点及其在线状态。"""
    return _get_service().list_nodes()


@router.post("/dispatch")
async def dispatch_task(body: DispatchRequest) -> dict[str, Any]:
    """派发推理任务到端边云三层。

    Returns:
        含 ok/text/tier/privacy_note/attempts 的派发结果。
    """
    return _get_service().dispatch(
        goal=body.goal,
        latency_budget=body.latency_budget,
        privacy=body.privacy,
        capability=body.capability,
        system_prompt=body.system_prompt,
    )


@router.get("/dispatch/history")
async def dispatch_history(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """返回最近 N 条派发历史记录。"""
    return _get_service().dispatch_history(limit)