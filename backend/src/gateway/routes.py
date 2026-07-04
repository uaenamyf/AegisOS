# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建网关路由聚合器——/api/v1 前缀 + 鉴权依赖，挂载 REST 与 SSE 控制器
"""网关路由聚合器。

本模块创建带 ``/api/v1`` 前缀的 :class:`fastapi.APIRouter`，并对所有子路由
强制应用 :func:`verify_api_key` 鉴权依赖。随后挂载 REST 控制器与 SSE 事件
控制器，形成统一的受保护 API 入口。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.src.controllers.api import router as api_router
from backend.src.controllers.sse.events import router as sse_router
from backend.src.gateway.auth import verify_api_key

# 创建带统一前缀与鉴权依赖的网关路由；所有挂载其下的路由均需通过 API Key 校验。
router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])
# 挂载 REST 控制器（会话/任务/Agent 等同步接口）。
router.include_router(api_router)
# 挂载 SSE 事件控制器（流式事件推送）。
router.include_router(sse_router)

__all__ = ["router"]
