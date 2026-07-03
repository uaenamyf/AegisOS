"""AegisOS protocol layer — the single source of truth for data contracts.

All cross-module communication must use the types defined here. See
developer/specs/04_PROTOCOL_SPEC.md for the specification.
"""

# @aegis-gen
# date: 2026-07-03
# dev: Claude Code (glm-5.2)
# change: docstring 引用从 developer/MESSAGE_PROTOCOL.md 改指 developer/specs/04_PROTOCOL_SPEC.md（SSOT 对齐）

from .message import Message, NodeRef, Header
from .event import Event, EventType
from .heartbeat import Heartbeat
from .scheduler import Task, TaskStatus, Plan, Schedule, RetryPolicy, RollbackPlan
from .tool import ToolCall, ToolResult, ToolSpec
from .memory import MemoryPacket
from .agent import Agent, AgentStatus
from .graph import Graph, GraphNode, GraphEdge, Route, GraphDiff, NodeKind
from .sync import SyncPacket, SyncStatus
from .cyber import (
    Asset, VulnFinding, AttackStep, AttackChain,
    Alert, DefenseAction, ResponsePlan, ThreatIntel,
)

__all__ = [
    "Message", "NodeRef", "Header",
    "Event", "EventType",
    "Heartbeat",
    "Task", "TaskStatus", "Plan", "Schedule", "RetryPolicy", "RollbackPlan",
    "ToolCall", "ToolResult", "ToolSpec",
    "MemoryPacket",
    "Agent", "AgentStatus",
    "Graph", "GraphNode", "GraphEdge", "Route", "GraphDiff", "NodeKind",
    "SyncPacket", "SyncStatus",
    "Asset", "VulnFinding", "AttackStep", "AttackChain",
    "Alert", "DefenseAction", "ResponsePlan", "ThreatIntel",
]
