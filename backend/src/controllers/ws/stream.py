# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 WebSocket 流端点 /ws/v1/stream（双向实时，Message 信封）
from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import asdict

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.src.composition import EventBusDep
from protocol import Message

router = APIRouter(tags=["ws"])


async def _try_receive(websocket: WebSocket, timeout: float = 0.1) -> str | None:
    """Try to receive a text frame without blocking the stream loop."""
    try:
        return await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
    except TimeoutError:
        return None


@router.websocket("/ws/v1/stream")
async def ws_stream(
    websocket: WebSocket,
    event_bus: EventBusDep,
    session: str = Query("", description="Session id to scope the stream"),
) -> None:
    await websocket.accept()
    seen = 0
    try:
        while True:
            events = event_bus.recent_events(limit=1000)
            new_events = events[seen:]
            seen = len(events)
            for event in new_events:
                if session:
                    payload = event.payload or {}
                    if payload.get("session_id") != session and event.task_id != session:
                        continue
                await websocket.send_text(
                    json.dumps({"type": event.topic, "data": asdict(event)}, default=str)
                )
            raw = await _try_receive(websocket)
            if raw is not None:
                try:
                    msg = Message.from_dict(json.loads(raw))
                    await websocket.send_text(
                        json.dumps({"type": "ack", "message_id": msg.message_id})
                    )
                except Exception:
                    await websocket.send_text(json.dumps({"type": "error", "message": "bad frame"}))
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
