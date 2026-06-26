"""AegisOS protocol layer — the single source of truth for data contracts.

All cross-module communication must use the types defined here. See
developer/MESSAGE_PROTOCOL.md for the specification.
"""

from .message import Message, NodeRef, Header
from .event import Event, EventType
from .heartbeat import Heartbeat
from .scheduler import Task, TaskStatus, Plan, Schedule, RetryPolicy, RollbackPlan
from .tool import ToolCall, ToolResult, ToolSpec
from .memory import MemoryPacket
from .agent import Agent, AgentStatus
from .graph import Graph, GraphNode, GraphEdge, Route, GraphDiff, NodeKind
from .sync import SyncPacket, SyncStatus

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
]
