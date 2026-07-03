from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    args: dict = field(default_factory=dict)
    timeout: float = 30.0
    permission: str = ""


@dataclass
class ToolResult:
    call_id: str = ""
    ok: bool = True
    output: object = None
    error: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    args_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    permission: str = "default"
    resource_limit: dict = field(default_factory=dict)
