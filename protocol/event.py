"""事件协议类型。

定义 AegisOS 事件总线使用的事件类型与事件结构，用于
模块间异步通知与状态同步。所有事件均携带唯一 ID 与时间戳。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .message import NodeRef


class EventType(str, Enum):
    """事件类型枚举。

    每个枚举值即事件总线的主题（topic）名称，订阅者按主题过滤事件。
    """

    AgentStart = "agent.start"      # Agent 开始执行任务
    AgentFinish = "agent.finish"    # Agent 完成任务（成功或失败）
    ToolCall = "tool.call"           # 发起工具调用
    ToolFinish = "tool.finish"       # 工具调用返回结果
    Retry = "task.retry"            # 任务重试
    Rollback = "task.rollback"      # 任务回滚
    MemoryUpdate = "memory.update"  # 记忆系统更新
    GraphUpdate = "graph.update"    # 拓扑图更新


@dataclass
class Event:
    """事件结构。

    事件总线中传递的标准事件数据结构，携带来源、负载与时间戳。

    Attributes:
        event_id: 事件唯一标识，自动生成 UUID hex。
        event_type: 事件类型，决定事件主题。
        task_id: 关联的任务 ID，便于按任务检索事件。
        source: 事件发起者的节点引用。
        payload: 事件负载，任意结构化数据。
        timestamp: 事件生成时间（Unix 时间戳，秒）。
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.AgentStart
    task_id: str = ""
    source: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def topic(self) -> str:
        """返回事件对应的总线主题字符串。

        订阅者使用该主题进行事件过滤。

        Returns:
            事件类型对应的主题字符串。
        """
        return self.event_type.value
