"""记忆协议类型。

定义 Agent 记忆系统的数据包结构，涵盖工作记忆、语义记忆、
情景记忆与归档等多层记忆形式，是记忆压缩与检索的基础数据契约。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryPacket:
    """记忆数据包。

    封装 Agent 记忆系统各层的内容，用于记忆读写、压缩与传输。

    Attributes:
        working: 工作记忆，当前会话的临时信息。
        semantic: 语义记忆，结构化知识。
        episodic: 情景记忆，历史事件记录。
        archive: 归档记忆，长期存储。
        embedding: 记忆向量嵌入，用于语义检索。
        summary: 记忆摘要文本。
        compression: 压缩元信息（如压缩比例、时间）。
        session_id: 所属会话 ID。
        task_id: 所属任务 ID。
        kind: 记忆类型：normal / decision / digest。
        recent: 是否最近步记忆，压缩时优先保留。
    """

    working: dict = field(default_factory=dict)
    semantic: dict = field(default_factory=dict)
    episodic: dict = field(default_factory=dict)
    archive: dict = field(default_factory=dict)
    embedding: list = field(default_factory=list)
    summary: str = ""
    compression: dict = field(default_factory=dict)
    session_id: str = ""
    task_id: str = ""
    kind: str = "normal"  # normal | decision | digest
    recent: bool = False  # 是否最近步（压缩时保留）
