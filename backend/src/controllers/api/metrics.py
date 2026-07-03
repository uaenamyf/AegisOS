# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 metrics 控制器 GET /metrics
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from backend.src.composition import get_composition

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics() -> dict[str, Any]:
    comp = get_composition()
    return {
        "uptime_seconds": time.time(),
        "agents_registered": len(comp.agent_registry._agents),
        "events_buffered": len(comp.event_bus._event_log),
        "db_engine": str(comp.engine.url),
        "status": "ok",
    }
