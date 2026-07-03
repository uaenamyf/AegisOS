from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryPacket:
    working: dict = field(default_factory=dict)
    semantic: dict = field(default_factory=dict)
    episodic: dict = field(default_factory=dict)
    archive: dict = field(default_factory=dict)
    embedding: list = field(default_factory=list)
    summary: str = ""
    compression: dict = field(default_factory=dict)
    session_id: str = ""
    task_id: str = ""
    kind: str = "normal"        # normal | decision | digest
    recent: bool = False        # 是否最近步（压缩时保留）
