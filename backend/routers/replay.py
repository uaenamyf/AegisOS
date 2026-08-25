# date: 2026-06-27
# dev: myf
"""会话回放控制器。

提供 ``GET /replay/{session_id}`` 端点，回放指定会话的事件时间线，
用于调试与执行复盘。
"""

from __future__ import annotations

from pydantic import BaseModel
_asdict = lambda obj: obj.model_dump() if isinstance(obj, BaseModel) else obj
from typing import Any

from fastapi import APIRouter

from backend.core.composition import EventBusDep
from protocol import Event

# 回放路由器，统一前缀 /replay，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/replay", tags=["replay"])


@router.get("/{session_id}")
async def replay_session(
    session_id: str,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    """回放指定会话的事件时间线。

    从事件总线读取近期事件，过滤出属于该会话的事件并按时间顺序返回。

    Args:
        session_id: 会话唯一标识。
        event_bus: 事件总线依赖，提供近期事件读取。

    Returns:
        包含 ``session_id``、``timeline`` 与 ``event_count`` 字段的
        字典。``timeline`` 为事件字典列表，``event_count`` 为事件数。
    """
    events = [_asdict(e) for e in event_bus.recent_events() if _belongs_to_session(e, session_id)]
    return {
        "session_id": session_id,
        "timeline": events,
        "event_count": len(events),
    }


def _belongs_to_session(event: Event, session_id: str) -> bool:
    """判断事件是否属于指定会话。

    当事件 payload 中的 ``session_id`` 字段等于给定会话 ID，
    或事件的 ``task_id`` 等于会话 ID 时，判定为属于该会话。

    Args:
        event: 待判定的事件对象。
        session_id: 目标会话唯一标识。

    Returns:
        属于该会话返回 True，否则返回 False。
    """
    payload = event.payload or {}
    return payload.get("session_id") == session_id or event.task_id == session_id
