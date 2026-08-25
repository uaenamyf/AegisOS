# date: 2026-08-25
# dev: overwhelmingly
# change: R1.5 Protocol→Pydantic 迁移：从 dataclass 升级为 BaseModel，保留 to_dict/from_dict 兼容
"""数据同步协议类型。

定义多节点间数据同步的数据包结构与同步状态枚举，
基于向量时钟解决并发冲突，是拓扑与记忆同步的基础数据契约。
"""
from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SyncStatus(StrEnum):
    """同步状态枚举。

    表示同步数据包在同步流程中的当前阶段。
    """

    Pending = "pending"      # 待同步：已创建尚未发送
    InFlight = "in_flight"    # 传输中：已发送尚未确认
    Applied = "applied"       # 已应用：目标已成功应用
    Conflict = "conflict"     # 冲突：检测到并发冲突，需解决
    Failed = "failed"        # 失败：同步出错


class SyncPacket(BaseModel):
    """同步数据包。

    封装需要在节点间同步的负载数据，附带向量时钟用于冲突检测。

    Attributes:
        sync_id: 同步包唯一标识，自动生成 UUID hex。
        source: 发送方节点标识。
        target: 接收方节点标识。
        payload: 待同步的负载数据。
        status: 当前同步状态，参见 SyncStatus。
        vector_clock: 向量时钟，记录各节点的逻辑时间，用于冲突检测。
        timestamp: 包生成时间（Unix 时间戳，秒）。
    """

    model_config = ConfigDict(extra="ignore")

    sync_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: str = ""
    target: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    status: SyncStatus = SyncStatus.Pending
    vector_clock: dict[str, int] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncPacket:
        return cls.model_validate(data)
