# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 聚合所有 REST 子控制器路由到单一 APIRouter
from __future__ import annotations

from fastapi import APIRouter

from backend.src.controllers.api import (
    agents,
    graph,
    memory,
    metrics,
    replay,
    sessions,
    tasks,
    tools,
)

router = APIRouter()
router.include_router(sessions.router)
router.include_router(tasks.router)
router.include_router(agents.router)
router.include_router(memory.router)
router.include_router(graph.router)
router.include_router(tools.router)
router.include_router(metrics.router)
router.include_router(replay.router)

__all__ = ["router"]
