# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 metrics 控制器 GET /metrics
"""运行指标控制器。

提供 ``GET /metrics`` 端点，返回后端运行时的关键指标快照，
包括已注册 Agent 数量、缓冲事件数与数据库引擎信息，供监控使用。
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from backend.src.composition import get_composition

# 指标路由器，统一前缀 /metrics，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics() -> dict[str, Any]:
    """返回运行时指标快照。

    从全局组合根读取当前运行状态，聚合为指标字典。

    Returns:
        包含以下字段的字典：

        - ``uptime_seconds``: 进程启动时间戳（Unix 秒）。
        - ``agents_registered``: 已注册 Agent 数量。
        - ``events_buffered``: 事件总线缓冲的事件数量。
        - ``db_engine``: 数据库引擎 URL 字符串。
        - ``status``: 固定值 ``ok``，表示指标采集正常。
    """
    comp = get_composition()
    return {
        "uptime_seconds": time.time(),
        "agents_registered": len(comp.agent_registry._agents),
        "events_buffered": len(comp.event_bus._event_log),
        "db_engine": str(comp.engine.url),
        "status": "ok",
    }
