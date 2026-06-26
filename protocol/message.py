from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import time
import uuid


@dataclass
class NodeRef:
    node_id: str
    node_type: str
    name: str = ""


@dataclass
class Header:
    version: str = "1.0"
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    compress: str = ""


@dataclass
class Message:
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str = ""
    task_id: str = ""
    workflow_id: str = ""
    sender: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    receiver: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    priority: int = 0
    ttl: int = 64
    compression: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Any = None
    header: Header = field(default_factory=Header)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        sender = NodeRef(**data.pop("sender", {"node_id": "", "node_type": ""}))
        receiver = NodeRef(**data.pop("receiver", {"node_id": "", "node_type": ""}))
        header = Header(**data.pop("header", {}))
        return cls(sender=sender, receiver=receiver, header=header, **data)
