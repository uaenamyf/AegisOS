# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""蓝队防御路由。

提供蓝队防御链执行端点，对应 Phase F 的 F4。
"""

from __future__ import annotations

from fastapi import APIRouter

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
