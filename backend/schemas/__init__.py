# date: 2026-06-27
# dev: myf
"""Pydantic v2 请求/响应 Schema 包。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., description="Identifier of the user owning the session")


class CreateTaskRequest(BaseModel):
    goal: str = Field(..., description="Natural-language goal for the task")
    session_id: str = Field(..., description="Owning session id")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task execution input")
    plan: dict[str, Any] = Field(default_factory=dict)
    dependency: list[str] = Field(default_factory=list)
    priority: int = 0


class InvokeAgentRequest(BaseModel):
    goal: str = Field("", description="Goal to hand to the agent")
    session_id: str = Field("", description="Owning session id for context")
    payload: dict[str, Any] = Field(default_factory=dict, description="Extra invocation payload")


class WriteMemoryRequest(BaseModel):
    working: dict[str, Any] = Field(default_factory=dict)
    semantic: dict[str, Any] = Field(default_factory=dict)
    episodic: dict[str, Any] = Field(default_factory=dict)
    archive: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    task_id: str = ""
    # date: 2026-08-01
    # dev: 123 chen
    # changelog: 新增 kind 字段，支持 MemoryStore v2 记忆路由（decision/checkpoint/snapshot）
    kind: str = "normal"  # normal | decision | digest | checkpoint | snapshot


class InvokeToolRequest(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    timeout: float = 30.0


class SessionResponse(BaseModel):
    id: str
    user_id: str
    status: str
    context: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task_id: str
    goal: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    dependency: list[str] = Field(default_factory=list)
    status: str
    plan: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    trust_score: float = 1.0
    success_rate: float = 1.0


class MemoryResponse(BaseModel):
    working: dict[str, Any] = Field(default_factory=dict)
    semantic: dict[str, Any] = Field(default_factory=dict)
    episodic: dict[str, Any] = Field(default_factory=dict)
    archive: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    session_id: str = ""


class GraphResponse(BaseModel):
    nodes: dict[str, Any] = Field(default_factory=dict)
    edges: list[Any] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str


# --- 攻防端点 Schema (date: 2026-07-06, dev: Claude Code (glm-5.2), changelog: 新建攻防场景请求/响应 Schema) ---


class StartRangeRequest(BaseModel):
    target_range: str = Field("10.0.0.0/24", description="Target network range in CIDR notation")
    label: str = Field("", description="Optional label for the range session")


class RedAttackRequest(BaseModel):
    target_range: str = Field("10.0.0.0/24", description="Target network range to attack")


class BlueDefenseRequest(BaseModel):
    event_stream: list[dict[str, Any]] = Field(
        default_factory=list, description="Raw event stream for detection"
    )


class PurpleReviewRequest(BaseModel):
    attack_chain: dict[str, Any] = Field(..., description="Red team attack chain")
    response_plan: dict[str, Any] = Field(..., description="Blue team response plan")
    alerts: list[dict[str, Any]] = Field(
        default_factory=list, description="Alert list for purple review"
    )


class RangeResponse(BaseModel):
    range_id: str
    target_range: str
    label: str
    status: str
    topology: dict[str, Any] = Field(default_factory=dict)


class TopologyResponse(BaseModel):
    target_range: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class AssetResponse(BaseModel):
    asset_id: str
    host: str = ""
    services: list[Any] = Field(default_factory=list)
    os: str = ""
    exposure: str = "external"


class VulnFindingResponse(BaseModel):
    finding_id: str
    cve_id: str = ""
    asset_id: str = ""
    cvss: float = 0.0
    attack_surface: str = ""


class AttackStepResponse(BaseModel):
    step_id: str
    technique: str = ""
    from_asset: str = ""
    to_asset: str = ""
    success: bool = False


class AttackChainResponse(BaseModel):
    chain_id: str
    target: str = ""
    steps: list[AttackStepResponse] = Field(default_factory=list)
    status: str = "planned"


class AlertResponse(BaseModel):
    alert_id: str
    severity: str = "low"
    src: str = ""
    dst: str = ""
    technique: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class DefenseActionResponse(BaseModel):
    action_id: str
    kind: str = "monitor"
    target: str = ""
    rationale: str = ""


class ResponsePlanResponse(BaseModel):
    plan_id: str
    actions: list[DefenseActionResponse] = Field(default_factory=list)
    confidence: float = 0.0
    rollback: dict[str, Any] = Field(default_factory=dict)


class ThreatIntelResponse(BaseModel):
    technique: str = ""
    tactic: str = ""
    refs: list[Any] = Field(default_factory=list)
    technique_id: str = ""
    sub_technique: str = ""
    detection: str = ""
    mitigation: str = ""
    risk_level: str = "medium"
    asset_ids: list[Any] = Field(default_factory=list)


class RedAttackResponse(BaseModel):
    assets: list[AssetResponse] = Field(default_factory=list)
    findings: list[VulnFindingResponse] = Field(default_factory=list)
    chain: dict[str, Any] = Field(default_factory=dict)
    # R15 可观测性：逐 agent 输入输出追踪（recon/vuln_correlator/exploit_planner）
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)


class BlueDefenseResponse(BaseModel):
    alerts: list[AlertResponse] = Field(default_factory=list)
    triaged: list[AlertResponse] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=dict)
    # R15 可观测性：逐 agent 输入输出追踪（detector/triage/threat_hunt/ir_planner）
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)


class PurpleReviewResponse(BaseModel):
    critique: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    # R15 可观测性：逐 agent 输入输出追踪（critic/reviewer）
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
