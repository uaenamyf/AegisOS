# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""红队攻击路由。

提供红队攻击链执行端点，对应 Phase F 的 F3。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.composition import get_cyber_defense_service
from backend.schemas import RedAttackRequest, RedAttackResponse
from backend.services.cyber_defense_service import CyberDefenseService

router = APIRouter(prefix="/attack", tags=["cyber-defense"])


@router.post("", response_model=RedAttackResponse)
async def red_attack(
    body: RedAttackRequest,
    service: CyberDefenseService = Depends(get_cyber_defense_service),
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


@router.get("/chain/{range_id}", response_model=RedAttackResponse)
async def get_attack_chain(
    range_id: str,
    service: CyberDefenseService = Depends(get_cyber_defense_service),
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
