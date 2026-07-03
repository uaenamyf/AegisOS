# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建网关路由聚合器——/api/v1 前缀 + 鉴权依赖，挂载 REST 与 SSE 控制器
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.src.controllers.api import router as api_router
from backend.src.controllers.sse.events import router as sse_router
from backend.src.gateway.auth import verify_api_key

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])
router.include_router(api_router)
router.include_router(sse_router)

__all__ = ["router"]
