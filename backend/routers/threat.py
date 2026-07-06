# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""威胁情报路由。

提供 ATT&CK 威胁情报查询端点，对应 Phase F 的 F5（端点部分）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.core.composition import get_cyber_defense_service
from backend.schemas import ThreatIntelResponse
from backend.services.cyber_defense_service import CyberDefenseService

router = APIRouter(prefix="/threat", tags=["cyber-defense"])


@router.get("/attack-techniques", response_model=list[ThreatIntelResponse])
async def get_attack_techniques(
    tactic: str | None = Query(None, description="Filter by ATT&CK tactic"),
    service: CyberDefenseService = Depends(get_cyber_defense_service),
) -> list[ThreatIntelResponse]:
    """查询 ATT&CK 威胁情报。

    返回预置的 ATT&CK 技战术映射，支持按战术过滤。

    Args:
        tactic: 可选的战术过滤（如 Execution / Persistence）。
        service: 攻防服务依赖。

    Returns:
        威胁情报条目列表。
    """
    techniques = service.get_attack_techniques(tactic)
    return [ThreatIntelResponse(**t) for t in techniques]
