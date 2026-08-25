# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""靶场管理路由。

提供靶场会话的启动、拓扑查询端点，对应 Phase F 的 F1/F2。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.composition import CyberDefenseServiceDep
from backend.schemas import RangeResponse, StartRangeRequest, TopologyResponse

router = APIRouter(tags=["cyber-defense"])


@router.post("/range/start", response_model=RangeResponse)
async def start_range(
    body: StartRangeRequest,
    service: CyberDefenseServiceDep,
) -> RangeResponse:
    """启动靶场会话。

    Args:
        body: 请求体，含目标网络范围和可选标签。
        service: 攻防服务依赖。

    Returns:
        靶场会话信息（含 range_id、拓扑）。
    """
    session = service.start_range(body.target_range, body.label)
    return RangeResponse(**session)


@router.get("/range/{range_id}", response_model=RangeResponse)
async def get_range(
    range_id: str,
    service: CyberDefenseServiceDep,
) -> RangeResponse:
    """获取靶场会话信息。

    Args:
        range_id: 靶场会话 ID。
        service: 攻防服务依赖。

    Raises:
        HTTPException: 靶场不存在返回 404。

    Returns:
        靶场会话信息。
    """
    session = service.get_range(range_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"range {range_id} not found"},
        )
    return RangeResponse(**session)


@router.get("/range/{range_id}/topology", response_model=TopologyResponse)
async def get_topology(
    range_id: str,
    service: CyberDefenseServiceDep,
) -> TopologyResponse:
    """获取靶场网络拓扑。

    Args:
        range_id: 靶场会话 ID。
        service: 攻防服务依赖。

    Raises:
        HTTPException: 靶场不存在返回 404。

    Returns:
        网络拓扑（节点 + 边）。
    """
    try:
        topology = service.get_topology(range_id)
    except KeyError as err:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"range {range_id} not found"},
        ) from err
    return TopologyResponse(**topology)
