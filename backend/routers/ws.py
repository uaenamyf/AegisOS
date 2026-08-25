# date: 2026-06-27
# dev: myf
"""WebSocket 实时流控制器。

提供 ``/ws/v1/stream`` WebSocket 端点，支持双向实时通信：
服务端持续推送事件总线中的事件，客户端可发送 Message 信封
消息，服务端回执确认。支持按会话 ID 过滤推送事件。
"""

from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.core.composition import EventBusDep
from protocol import Message


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj

# WebSocket 路由器，标签用于 OpenAPI 文档分组
router = APIRouter(tags=["ws"])


async def _try_receive(websocket: WebSocket, timeout: float = 0.1) -> str | None:
    """尝试在非阻塞模式下接收一帧文本。

    以短超时方式等待接收，避免阻塞事件推送循环。

    Args:
        websocket: 已连接的 WebSocket 实例。
        timeout: 等待超时时间（秒），默认 0.1 秒。

    Returns:
        成功收到文本帧时返回该字符串；超时未收到数据时返回 None。
    """
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
    """WebSocket 双向实时流端点。

    接受连接后，持续推送事件总线增量事件（可按会话过滤），
    同时以非阻塞方式接收客户端发送的 Message 信封消息并回执。
    客户端断开时优雅关闭连接。

    Args:
        websocket: WebSocket 连接实例。
        event_bus: 事件总线依赖，提供近期事件读取。
        session: 可选的会话 ID，用于过滤推送事件。为空时推送全部事件。
    """
    await websocket.accept()
    seen = 0  # 已推送事件偏移量
    try:
        while True:
            # 每次读取最多 1000 条近期事件
            events = event_bus.recent_events(limit=1000)
            new_events = events[seen:]  # 仅取尚未推送的增量部分
            seen = len(events)
            for event in new_events:
                # 会话过滤：指定 session 时仅推送属于该会话的事件
                if session:
                    payload = event.payload or {}
                    if payload.get("session_id") != session and event.task_id != session:
                        continue
                await websocket.send_text(
                    json.dumps({"type": event.topic, "data": _asdict(event)}, default=str)
                )
            # 非阻塞接收客户端消息，不阻塞推送循环
            raw = await _try_receive(websocket)
            if raw is not None:
                try:
                    msg = Message.from_dict(json.loads(raw))
                    # 解析成功回执消息 ID
                    await websocket.send_text(
                        json.dumps({"type": "ack", "message_id": msg.message_id})
                    )
                except Exception:
                    # 解析失败返回错误帧
                    await websocket.send_text(json.dumps({"type": "error", "message": "bad frame"}))
    except WebSocketDisconnect:
        # 客户端主动断开，正常退出循环
        pass
    finally:
        # 兜底关闭连接，忽略可能已关闭的异常
        with contextlib.suppress(Exception):
            await websocket.close()
