# date: 2026-06-27
# dev: myf
"""Backend 路由聚合包——挂载所有 REST/SSE/WS 控制器。"""
from __future__ import annotations

from fastapi import APIRouter

from backend.routers import (
    agents,
    attack,
    chat,
    defense,
    drill,
    graph,
    memory,
    metrics,
    range,
    replay,
    sessions,
    tasks,
    threat,
    tools,
)

router = APIRouter()
router.include_router(sessions.router)
router.include_router(tasks.router)
# R23: 普通对话真实推理端点
router.include_router(chat.router)
router.include_router(agents.router)
router.include_router(memory.router)
router.include_router(graph.router)
router.include_router(tools.router)
router.include_router(metrics.router)
router.include_router(replay.router)
# date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 挂载攻防端点路由
router.include_router(range.router)
router.include_router(attack.router)
router.include_router(drill.router)
router.include_router(defense.router)
router.include_router(threat.router)

__all__ = ["router"]
