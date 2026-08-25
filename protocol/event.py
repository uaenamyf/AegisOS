# date: 2026-08-25
# dev: overwhelmingly
# change: R1.2 Protocol→Pydantic 迁移：从 dataclass 升级为 BaseModel，保留 to_dict/from_dict 兼容
"""事件协议类型。

定义 AegisOS 事件总线使用的事件类型与事件结构，用于
模块间异步通知与状态同步。所有事件均携带唯一 ID 与时间戳。
"""
from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .message import NodeRef


class EventType(StrEnum):
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
    # AP4: 人机协同（Ask 范式）——暂停提问 + 超时降级
    HumanInputRequired = "human.input.required"  # Agent 需要人工输入/确认（阻塞决策点）
    HumanResponse = "human.response"            # 人类对上述请求的回答（含超时降级标记）


class Event(BaseModel):
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

    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.AgentStart
    task_id: str = ""
    source: NodeRef = Field(default_factory=lambda: NodeRef("", ""))
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    @property
    def topic(self) -> str:
        """返回事件对应的总线主题字符串。

        订阅者使用该主题进行事件过滤。

        Returns:
            事件类型对应的主题字符串。
        """
        return self.event_type.value

    # ----------------- 兼容 shim（旧 dataclass 接口） -----------------

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（与旧 dataclass 接口兼容）。"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """从 dict 反序列化（与旧 dataclass 接口兼容）。"""
        return cls.model_validate(data)
