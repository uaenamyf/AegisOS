# date: 2026-09-04
# dev: OpenSquilla
# changelog: R7 新建——运行时模式控制器（GET/POST /system/mode）
"""运行时模式控制器 —— 查询/切换攻防编排器运行模式（mock / 真实 LLM）。

端点：
- GET  /api/v1/system/mode  → 当前模式描述（供前端徽标展示）
- POST /api/v1/system/mode  → 切换模式（body: {"mode": "mock"|"real"}）
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core import runtime_mode
from backend.core.auth import verify_api_key

router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(verify_api_key)])


class SetModeRequest(BaseModel):
    """切换模式请求体。"""

    mode: Literal["mock", "real"] = Field(..., description="目标模式：mock=预置响应 / real=真实 LLM")


@router.get("/mode")
async def get_mode() -> dict[str, Any]:
    """返回当前运行时模式描述（模式/模型/提供商/Key 可用性）。"""
    return runtime_mode.describe()


@router.post("/mode")
async def set_mode(body: SetModeRequest) -> dict[str, Any]:
    """切换运行时模式并返回新描述。"""
    try:
        runtime_mode.set_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_MODE", "message": str(exc)},
        ) from exc
    return runtime_mode.describe()
