# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""红队攻击路由。

提供红队攻击链执行端点，对应 Phase F 的 F3。
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.core.composition import CyberDefenseServiceDep
from backend.schemas import RedAttackRequest, RedAttackResponse

router = APIRouter(prefix="/attack", tags=["cyber-defense"])


@router.post("", response_model=RedAttackResponse)
async def red_attack(
    body: RedAttackRequest,
    service: CyberDefenseServiceDep,
) -> RedAttackResponse:
    """执行红队攻击链。

    委托 CyberOrchestrator 执行 recon→vuln_correlator→exploit_planner 链。

    Args:
        body: 请求体，含目标网络范围。
        service: 攻防服务依赖。

    Returns:
        红队攻击结果（资产、漏洞、攻击链）。
    """
    result = service.red_attack(body.target_range)
    return RedAttackResponse(**result)


@router.post("/stream")
async def red_attack_stream(
    body: RedAttackRequest,
    service: CyberDefenseServiceDep,
) -> StreamingResponse:
    """红队攻击链 SSE 流式执行（渐进展示）。

    事件序列：``stage_start``（recon/vuln/exploit 各一次）→ ``stage_done``
    （各步产出）→ ``done``（完整结果）；失败时 ``attack_error``。

    Args:
        body: 请求体，含目标网络范围。
        service: 攻防服务依赖。

    Returns:
        ``text/event-stream`` 响应。
    """

    async def event_generator():
        try:
            async for event in service.stream_red_attack(body.target_range):
                yield (
                    f"event: {event['event']}\n"
                    f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                )
        except Exception as exc:  # noqa: BLE001 —— 兜底转 SSE 错误事件，避免连接悬挂
            yield (
                "event: attack_error\n"
                f"data: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chain/{range_id}", response_model=RedAttackResponse)
async def get_attack_chain(
    range_id: str,
    service: CyberDefenseServiceDep,
) -> RedAttackResponse:
    """获取指定靶场的攻击链 DAG。

    如果靶场已有缓存的攻击链则返回之，否则触发新的攻击链执行。

    Args:
        range_id: 靶场会话 ID。
        service: 攻防服务依赖。

    Returns:
        攻击链 DAG。
    """
    result = service.get_attack_chain(range_id)
    if result is None:
        result = service.red_attack("10.0.0.0/24")
    return RedAttackResponse(**result)
