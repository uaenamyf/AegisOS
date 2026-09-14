# date: 2026-09-14
# dev: OpenSquilla
# changelog: R23 新建 Chat 控制器——普通对话走真实端边云推理，替代固定 JSON 输出
"""Chat 控制器 —— 通用对话 REST 端点。

R23：普通对话（非攻防演练）不再经 ``/tasks`` 被兜底路由到 recon 等攻防
Agent（固定预置 JSON），而是走 :class:`backend.services.chat_service.ChatService`：
记忆上下文组装 → 隐私分级 → 端边云真实推理 → 返回自然语言与真实执行位置。

端点：
    - ``POST /api/v1/chat`` — 一轮对话。响应含 ``intent`` 分类，
      前端据此决定是否改走演练链路。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.core.composition import ChatServiceDep

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """对话请求体。"""

    goal: str = Field(..., description="用户输入的自然语言消息")
    session_id: str = Field("", description="会话 ID（记忆与多轮上下文键）")
    history: list[dict[str, Any]] = Field(
        default_factory=list, description="可选近期消息 [{role, content}]，用于多轮上下文"
    )


@router.post("")
async def chat(body: ChatRequest, service: ChatServiceDep) -> dict[str, Any]:
    """执行一轮通用对话，返回自然语言回复与真实执行位置。

    演练语义（``intent == "drill"``）不会在此执行——响应 ``ok=False`` 并带
    ``error="drill_required_frontend"`` 提示，由前端改走演练链路，保证
    攻防演练绝不会被当普通对话"答掉"。
    """
    goal = (body.goal or "").strip()
    if not goal:
        return {"ok": False, "error": "goal must not be empty", "intent": "chat"}
    intent = service.classify(goal)
    if intent == "drill":
        return {
            "ok": False,
            "intent": "drill",
            "error": "drill_required_frontend",
            "text": "攻防演练请通过演练链路发起（Chat 前端将自动转接）。",
            "tier": "",
            "node_id": "",
            "model_id": "",
            "provider": "",
            "latency_ms": 0,
            "privacy_note": "",
            "routed": False,
            "attempts": [],
        }
    import asyncio

    result = await asyncio.to_thread(service.chat, goal, body.session_id, body.history)
    return result


__all__ = ["router"]
