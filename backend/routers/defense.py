# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""蓝队防御路由。

提供蓝队防御链执行端点，对应 Phase F 的 F4。
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.core.composition import CyberDefenseServiceDep
from backend.schemas import (
    BlueDefenseRequest,
    BlueDefenseResponse,
    PurpleReviewRequest,
    PurpleReviewResponse,
)

router = APIRouter(prefix="/defense", tags=["cyber-defense"])


@router.post("", response_model=BlueDefenseResponse)
async def blue_defense(
    body: BlueDefenseRequest,
    service: CyberDefenseServiceDep,
) -> BlueDefenseResponse:
    """执行蓝队防御链。

    委托 CyberOrchestrator 执行 detector→triage→threat_hunt→ir_planner 链。

    Args:
        body: 请求体，含事件流。
        service: 攻防服务依赖。

    Returns:
        蓝队防御结果（告警、假设、响应计划）。
    """
    result = service.blue_defense(body.event_stream)
    return BlueDefenseResponse(**result)


@router.post("/stream")
async def blue_defense_stream(
    body: BlueDefenseRequest,
    service: CyberDefenseServiceDep,
) -> StreamingResponse:
    """蓝队防御链 SSE 流式执行（渐进展示）。

    事件序列：``stage_start``（detect/triage/hunt/ir 各一次）→
    ``stage_done``（各步产出）→ ``done``（完整结果）；失败时
    ``defense_error``。

    Args:
        body: 请求体，含事件流。
        service: 攻防服务依赖。

    Returns:
        ``text/event-stream`` 响应。
    """

    async def event_generator():
        try:
            async for event in service.stream_blue_defense(body.event_stream):
                yield (
                    f"event: {event['event']}\n"
                    f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                )
        except Exception as exc:  # noqa: BLE001 —— 兜底转 SSE 错误事件，避免连接悬挂
            yield (
                "event: defense_error\n"
                f"data: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{range_id}", response_model=BlueDefenseResponse)
async def get_defense(
    range_id: str,
    service: CyberDefenseServiceDep,
) -> BlueDefenseResponse:
    """获取指定靶场的防御响应。

    Args:
        range_id: 靶场会话 ID。
        service: 攻防服务依赖。

    Returns:
        防御响应计划。
    """
    result = service.get_defense(range_id)
    if result is None:
        result = service.blue_defense()
    return BlueDefenseResponse(**result)


@router.post("/purple-review", response_model=PurpleReviewResponse)
async def purple_review(
    body: PurpleReviewRequest,
    service: CyberDefenseServiceDep,
) -> PurpleReviewResponse:
    """执行紫队对抗校验。

    校验红队攻击链的合理性并审查跨产出一致性。

    Args:
        body: 请求体，含攻击链、响应计划、告警。
        service: 攻防服务依赖。

    Returns:
        紫队校验结果（critique + review）。
    """
    result = service.purple_review(
        body.attack_chain, body.response_plan, body.alerts
    )
    return PurpleReviewResponse(**result)
