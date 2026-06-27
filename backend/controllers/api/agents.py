# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 agents 控制器 GET /agents、GET /agents/{id}、POST /agents/{id}/invoke
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.composition import AgentServiceDep
from backend.controllers.schemas import AgentResponse, InvokeAgentRequest
from protocol import Agent

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_to_response(agent: Agent) -> AgentResponse:
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
    agents = await service.list_agents()
    return [_agent_to_response(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> AgentResponse:
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
    if await service.get_agent(agent_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"agent {agent_id} not found"},
        )
    result = await service.invoke(agent_id, body.goal)
    return {"agent_id": agent_id, "result": result}
