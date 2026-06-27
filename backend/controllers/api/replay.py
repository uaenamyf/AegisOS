# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 replay 控制器 GET /replay/{session}（回放事件时间线）
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from backend.composition import EventBusDep
from protocol import Event

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get("/{session_id}")
async def replay_session(
    session_id: str,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    events = [asdict(e) for e in event_bus.recent_events() if _belongs_to_session(e, session_id)]
    return {
        "session_id": session_id,
        "timeline": events,
        "event_count": len(events),
    }


def _belongs_to_session(event: Event, session_id: str) -> bool:
    payload = event.payload or {}
    return payload.get("session_id") == session_id or event.task_id == session_id
