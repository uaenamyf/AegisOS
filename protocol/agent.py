from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .message import NodeRef


class AgentStatus(str, Enum):
    Idle = "idle"
    Running = "running"
    Waiting = "waiting"
    Failed = "failed"
    Offline = "offline"


@dataclass
class Agent:
    agent_id: str
    name: str
    role: str
    ref: NodeRef = field(default_factory=lambda: NodeRef("", "agent"))
    capabilities: list = field(default_factory=list)
    status: AgentStatus = AgentStatus.Idle
    trust_score: float = 1.0
    success_rate: float = 1.0
