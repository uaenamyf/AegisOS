# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 Pydantic v2 请求/响应 Schema（CreateSessionRequest 等）
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., description="Identifier of the user owning the session")


class CreateTaskRequest(BaseModel):
    goal: str = Field(..., description="Natural-language goal for the task")
    session_id: str = Field(..., description="Owning session id")


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
