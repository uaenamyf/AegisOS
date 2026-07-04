"""Agent 身份与状态协议类型。

定义智能体（Agent）的基本身份信息与运行状态枚举，用于在
AegisOS 中统一描述参与协作的智能体。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .message import NodeRef


class AgentStatus(str, Enum):
    """Agent 运行状态枚举。

    表示 Agent 在调度生命周期中的当前阶段，用于调度器决定
    是否可向该 Agent 分发新任务。
    """

    Idle = "idle"       # 空闲：可接收新任务
    Running = "running"  # 执行中：正在处理任务
    Waiting = "waiting"  # 等待中：阻塞于外部依赖（如工具返回）
    Failed = "failed"    # 失败：上次执行出错，需人工或自动恢复
    Offline = "offline"  # 离线：不可达，不参与调度


@dataclass
class Agent:
    """Agent 身份与能力描述。

    描述单个智能体的唯一标识、角色、能力清单及运行时指标，
    作为能力发现与任务路由的基础数据结构。

    Attributes:
        agent_id: Agent 唯一标识。
        name: Agent 可读名称。
        role: Agent 角色标签（如 planner / executor / reviewer）。
        ref: 节点引用，用于消息寻址。
        capabilities: 能力列表，调度器据此匹配任务。
        status: 当前运行状态，参见 AgentStatus。
        trust_score: 信任分数，0.0-1.0，越高表示越可信。
        success_rate: 历史成功率，0.0-1.0，用于调度优先级评估。
    """

    agent_id: str
    name: str
    role: str
    ref: NodeRef = field(default_factory=lambda: NodeRef("", "agent"))
    capabilities: list = field(default_factory=list)
    status: AgentStatus = AgentStatus.Idle
    trust_score: float = 1.0
    success_rate: float = 1.0
