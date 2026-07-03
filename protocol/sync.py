from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class SyncStatus(str, Enum):
    Pending = "pending"
    InFlight = "in_flight"
    Applied = "applied"
    Conflict = "conflict"
    Failed = "failed"


@dataclass
class SyncPacket:
    sync_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: str = ""
    target: str = ""
    payload: dict = field(default_factory=dict)
    status: SyncStatus = SyncStatus.Pending
    vector_clock: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
