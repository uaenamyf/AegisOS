"""心跳协议类型。

定义节点心跳数据结构，用于监控 Agent 与节点的资源占用与
健康状态，是健康检查与负载均衡的基础数据契约。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .message import NodeRef


@dataclass
class Heartbeat:
    """节点心跳。

    携带节点资源指标与健康状态，由各节点定期上报。

    Attributes:
        node: 发送心跳的节点引用。
        cpu: CPU 使用率，0.0-1.0。
        gpu: GPU 使用率，0.0-1.0。
        latency: 节点响应延迟（秒）。
        memory: 内存使用率，0.0-1.0。
        token: 当前 Token 消耗量。
        status: 健康状态：healthy / degraded / unhealthy。
        timestamp: 心跳生成时间（Unix 时间戳，秒）。
    """

    node: NodeRef = field(default_factory=lambda: NodeRef("", ""))
    cpu: float = 0.0
    gpu: float = 0.0
    latency: float = 0.0
    memory: float = 0.0
    token: int = 0
    status: str = "healthy"
    timestamp: float = field(default_factory=time.time)
