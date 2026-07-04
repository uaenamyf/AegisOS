# date: 2026-06-27
# dev: myf
# changelog: 新建 agents 控制器 GET /agents、GET /agents/{id}、POST /agents/{id}/invoke
"""Agent 控制器。

提供 Agent 能力发现与调用的 REST 端点，包括列出所有 Agent、
查询单个 Agent 详情以及向指定 Agent 下发执行目标。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.composition import AgentServiceDep
from backend.schemas import AgentResponse, InvokeAgentRequest
from protocol import Agent

# Agent 路由器，统一前缀 /agents，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_to_response(agent: Agent) -> AgentResponse:
    """将协议层 Agent 转换为 API 响应模型。

    Args:
        agent: 协议层 Agent 对象。

    Returns:
        转换后的 AgentResponse，状态字段取枚举的字符串值，
        capabilities 列表复制以避免外部修改。
    """
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        role=agent.role,
        status=agent.status.value,
        capabilities=list(agent.capabilities),
        trust_score=agent.trust_score,
        success_rate=agent.success_rate,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    service: AgentServiceDep,
) -> list[AgentResponse]:
    """列出所有已注册的 Agent。

    Args:
        service: Agent 服务依赖，负责 Agent 注册表读取。

    Returns:
        全部 Agent 对应的响应对象列表。
    """
    agents = await service.list_agents()
    return [_agent_to_response(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> AgentResponse:
    """查询单个 Agent 详情。

    Args:
        agent_id: 待查询的 Agent 唯一标识。
        service: Agent 服务依赖。

    Returns:
        对应 Agent 的响应对象。

    Raises:
        HTTPException: Agent 不存在时返回 404 NOT_FOUND。
    """
    agent = await service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"agent {agent_id} not found"}
        )
    return _agent_to_response(agent)


@router.post("/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str,
    body: InvokeAgentRequest,
    service: AgentServiceDep,
) -> dict[str, Any]:
    """向指定 Agent 下发执行目标。

    调用前先校验 Agent 是否存在，再下发目标与会话上下文执行。

    Args:
        agent_id: 待调用的 Agent 唯一标识。
        body: 调用请求体，包含目标与会话 ID。
        service: Agent 服务依赖，负责执行编排。

    Returns:
        包含 ``agent_id`` 与 ``result`` 字段的字典，result 为
        Agent 执行返回的结果。

    Raises:
        HTTPException: Agent 不存在时返回 404 AGENT_NOT_FOUND。
    """
    if await service.get_agent(agent_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"agent {agent_id} not found"},
        )
    result = await service.invoke(agent_id, body.goal, body.session_id)
    return {"agent_id": agent_id, "result": result}
