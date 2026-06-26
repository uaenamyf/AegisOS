from __future__ import annotations

from dataclasses import dataclass, field
import time

from .message import NodeRef


@dataclass
class Heartbeat:
    node: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    cpu: float = 0.0
    gpu: float = 0.0
    latency: float = 0.0
    memory: float = 0.0
    token: int = 0
    status: str = "healthy"
    timestamp: float = field(default_factory=time.time)
