"""AegisOS protocol layer — the single source of truth for data contracts.

All cross-module communication must use the types defined here. See
developer/specs/04_PROTOCOL_SPEC.md for the specification.
"""

# date: 2026-07-03
# dev: myf
# changelog: docstring 引用从 developer/MESSAGE_PROTOCOL.md 改指 developer/specs/04_PROTOCOL_SPEC.md（SSOT 对齐）

# ---- Agent 身份与状态 ----
from .agent import Agent, AgentStatus
# ---- 攻防协议类型 ----
from .cyber import (
    Alert,
    Asset,
    AttackChain,
    AttackStep,
    DefenseAction,
    ResponsePlan,
    ThreatIntel,
    VulnFinding,
)
# ---- 事件总线 ----
from .event import Event, EventType
# ---- 拓扑图与路由 ----
from .graph import Graph, GraphDiff, GraphEdge, GraphNode, NodeKind, Route
# ---- 心跳与健康检查 ----
from .heartbeat import Heartbeat
# ---- 记忆系统 ----
from .memory import MemoryPacket
# ---- 消息协议 ----
from .message import Header, Message, NodeRef
# ---- 调度与任务 ----
from .scheduler import Plan, RetryPolicy, RollbackPlan, Schedule, Task, TaskStatus
# ---- 数据同步 ----
from .sync import SyncPacket, SyncStatus
# ---- 工具调用 ----
from .tool import ToolCall, ToolResult, ToolSpec

__all__ = [
    "Message",
    "NodeRef",
    "Header",
    "Event",
    "EventType",
    "Heartbeat",
    "Task",
    "TaskStatus",
    "Plan",
    "Schedule",
    "RetryPolicy",
    "RollbackPlan",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "MemoryPacket",
    "Agent",
    "AgentStatus",
    "Graph",
    "GraphNode",
    "GraphEdge",
    "Route",
    "GraphDiff",
    "NodeKind",
    "SyncPacket",
    "SyncStatus",
    "Asset",
    "VulnFinding",
    "AttackStep",
    "AttackChain",
    "Alert",
    "DefenseAction",
    "ResponsePlan",
    "ThreatIntel",
]
