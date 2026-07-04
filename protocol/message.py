"""消息协议类型。

定义 AegisOS 跨模块通信的标准消息结构，包括节点引用、
消息头与消息体。所有模块间通信均应使用此处的 Message 类型。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NodeRef:
    """节点引用。

    统一的节点寻址结构，用于消息的发送方与接收方标识。

    Attributes:
        node_id: 节点唯一标识。
        node_type: 节点类型（如 agent / tool / memory）。
        name: 节点可读名称。
    """

    node_id: str
    node_type: str
    name: str = ""


@dataclass
class Header:
    """消息头。

    携带协议版本与链路追踪信息。

    Attributes:
        version: 协议版本号。
        trace_id: 链路追踪 ID，自动生成 UUID hex。
        session_id: 所属会话 ID。
        compress: 压缩方式标识（如 gzip），空表示不压缩。
    """

    version: str = "1.0"
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    compress: str = ""


@dataclass
class Message:
    """标准消息。

    跨模块通信的标准数据结构，包含路由、优先级、负载与头信息。

    Attributes:
        message_id: 消息唯一标识，自动生成 UUID hex。
        parent_id: 父消息 ID，用于构建消息链。
        task_id: 关联的任务 ID。
        workflow_id: 关联的工作流 ID。
        sender: 发送方节点引用。
        receiver: 接收方节点引用。
        priority: 消息优先级，数值越大优先级越高。
        ttl: 生存跳数，每转发一次减一，归零时丢弃。
        compression: 负载压缩方式。
        timestamp: 消息生成时间（Unix 时间戳，秒）。
        payload: 消息负载，任意类型。
        header: 消息头。
    """

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
        """将消息序列化为字典。

        Returns:
            包含所有字段的字典，嵌套的 NodeRef 与 Header 也会递归转换。
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        """从字典反序列化消息。

        Args:
            data: 包含消息字段的字典，其中 sender、receiver、header 为子字典。

        Returns:
            重建后的 Message 实例。
        """
        sender = NodeRef(**data.pop("sender", {"node_id": "", "node_type": ""}))
        receiver = NodeRef(**data.pop("receiver", {"node_id": "", "node_type": ""}))
        header = Header(**data.pop("header", {}))
        return cls(sender=sender, receiver=receiver, header=header, **data)
