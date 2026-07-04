# date: 2026-06-27
# dev: myf
# changelog: 新建 SSE 事件流控制器 GET /events（text/event-stream）
"""SSE 事件流控制器。

提供 ``GET /events`` 端点，以 Server-Sent Events（SSE）方式
向客户端持续推送事件总线中的事件，支持按主题过滤。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.core.composition import EventBusDep

# SSE 路由器，标签用于 OpenAPI 文档分组
router = APIRouter(tags=["events"])


@router.get("/events")
async def stream_events(
    event_bus: EventBusDep,
    stream: str = Query("", description="Optional topic filter (e.g. graph.update)"),
) -> StreamingResponse:
    """以 SSE 形式持续推送事件。

    建立长连接后，以 0.5 秒间隔轮询事件总线，将增量事件按
    ``event: <topic>\\ndata: <json>\\n\\n`` 格式推送至客户端。
    可选按主题过滤，仅推送匹配主题的事件。

    Args:
        event_bus: 事件总线依赖，提供近期事件读取。
        stream: 可选的主题过滤器，为空表示推送全部主题事件。

    Returns:
        ``StreamingResponse``，媒体类型为 ``text/event-stream``，
        持续输出 SSE 帧。
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 帧生成器。

        以增量方式轮询事件总线并产出 SSE 格式字符串。

        Yields:
            符合 SSE 规范的事件帧字符串。
        """
        seen = 0  # 已推送事件偏移量，用于增量推送
        while True:
            # 每次读取最多 1000 条近期事件
            events = event_bus.recent_events(limit=1000)
            new_events = events[seen:]  # 仅取尚未推送的增量部分
            seen = len(events)
            for event in new_events:
                # 主题过滤：指定了 stream 时跳过不匹配的事件
                if stream and event.topic != stream:
                    continue
                payload = asdict(event)
                yield f"event: {event.topic}\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.5)  # 轮询间隔，避免 CPU 空转

    return StreamingResponse(event_generator(), media_type="text/event-stream")
