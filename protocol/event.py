from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .message import NodeRef


class EventType(str, Enum):
    AgentStart = "agent.start"
    AgentFinish = "agent.finish"
    ToolCall = "tool.call"
    ToolFinish = "tool.finish"
    Retry = "task.retry"
    Rollback = "task.rollback"
    MemoryUpdate = "memory.update"
    GraphUpdate = "graph.update"


@dataclass
class Event:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.AgentStart
    task_id: str = ""
    source: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def topic(self) -> str:
        return self.event_type.value
