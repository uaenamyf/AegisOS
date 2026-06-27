# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 SSE 事件流控制器 GET /events（text/event-stream）
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.composition import EventBusDep

router = APIRouter(tags=["events"])


@router.get("/events")
async def stream_events(
    event_bus: EventBusDep,
    stream: str = Query("", description="Optional topic filter (e.g. graph.update)"),
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        seen = 0
        while True:
            events = event_bus.recent_events(limit=1000)
            new_events = events[seen:]
            seen = len(events)
            for event in new_events:
                if stream and event.topic != stream:
                    continue
                payload = asdict(event)
                yield f"event: {event.topic}\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
