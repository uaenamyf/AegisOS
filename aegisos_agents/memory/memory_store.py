# date: 2026-07-06
# dev: myf
"""记忆集成存储 —— 认知循环的记忆中枢。

:class:`MemoryStore` 是 Agent 认知循环的记忆入口：聚合工作记忆、情景记忆、
语义记忆、向量记忆四层存储，并串联 :mod:`compactor`（压缩）与
:mod:`recaller`（唤醒），实现"写入 → 压缩 → 唤醒 → 复用"的超长程闭环。

认知循环（由编排器驱动）：
    1. 推理前：``recall(trigger)`` 唤醒相关历史经验 + ``search_knowledge(keyword)``
       查询 ATT&CK/CVE 知识，注入 Agent 上下文。
    2. 推理后：``write(packet)`` 将本步产出按内容路由到对应记忆层。
    3. 上下文超长：``compress(session_id, budget)`` 压缩工作记忆栈，保留决策与最近步。
    4. 语义检索：``retrieve(query)`` 跨情景+向量做关键词唤醒，对外实现 MemoryAPI。

本类实现 ``agents.api.MemoryAPI``（read/write/retrieve），可由后端注入替代
``MockMemoryAPI``，使记忆真正接入 runtime。
"""

from __future__ import annotations

from typing import Any

from aegisos_agents.memory.compression.compactor import compress
from aegisos_agents.memory.episodic.store import EpisodicMemory
from aegisos_agents.memory.recall.recaller import recall
from aegisos_agents.memory.semantic.store import SemanticMemory
from aegisos_agents.memory.vector.store import VectorMemory
from aegisos_agents.memory.working.store import WorkingMemory
from protocol.memory import MemoryPacket


class MemoryStore:
    """记忆集成存储 —— 聚合四层记忆 + 压缩 + 唤醒，实现 ``MemoryAPI``。

    持有工作/情景/语义/向量四层子存储，对外提供统一的读写检索接口，
    并在内部按记忆内容自动路由到对应层级，串联压缩与唤醒形成认知闭环。

    Attributes:
        working: 工作记忆存储（会话级临时上下文）。
        episodic: 情景记忆存储（跨会话历史经验）。
        semantic: 语义记忆存储（ATT&CK/CVE 知识库）。
        vector: 向量记忆存储（余弦相似度检索，Qdrant 预留）。
    """

    def __init__(self) -> None:
        """初始化记忆集成存储，装配四层子存储（语义层预置 ATT&CK 种子知识）。"""
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(seed=True)
        self.vector = VectorMemory()

    # ---- MemoryAPI 实现 ----

    def read(self, query: dict[str, Any]) -> MemoryPacket:
        """按查询条件读取记忆（实现 ``MemoryAPI.read``）。

        以 ``session_id`` 为主键聚合该会话的工作记忆，合并为单个
        ``MemoryPacket`` 返回（summary 拼接各步，working 汇总各步 working dict）。

        Args:
            query: 查询条件字典，识别 ``session_id`` 键。

        Returns:
            聚合后的记忆包；会话无工作记忆时返回空包（带 session_id）。
        """
        session_id = query.get("session_id", "")
        stack = self.working.get(session_id)
        if not stack:
            return MemoryPacket(session_id=session_id)
        # 合并各步 working dict，拼接 summary 便于上层展示
        merged_working: dict[str, Any] = {}
        for m in stack:
            merged_working.update(m.working)
        return MemoryPacket(
            session_id=session_id,
            working=merged_working,
            summary=" | ".join(m.summary for m in stack if m.summary),
            kind="normal",
        )

    def write(self, packet: MemoryPacket) -> bool:
        """写入一条记忆，按内容自动路由到对应记忆层（实现 ``MemoryAPI.write``）。

        路由规则：
            - 始终追加到工作记忆（当前会话上下文栈）。
            - ``kind == "decision"`` 或 ``episodic`` 字段非空 → 同时记入情景记忆。
            - ``embedding`` 非空 → 同时索引到向量记忆。
            - ``semantic`` 字段非空且提供 ``concept_id`` → 写入语义知识库。

        Args:
            packet: 待写入的记忆数据包。

        Returns:
            始终返回 ``True``（写入不失败）。
        """
        # 1) 工作记忆：当前会话上下文栈
        self.working.add(packet)
        # 2) 情景记忆：决策类或显式 episodic 内容记为历史经验
        if packet.kind == "decision" or packet.episodic:
            self.episodic.add(packet)
        # 3) 向量记忆：携带 embedding 时索引
        if packet.embedding:
            self.vector.add(packet)
        # 4) 语义记忆：携带结构化 semantic 且有 concept_id 时入库
        if packet.semantic and "concept_id" in packet.semantic:
            self.semantic.add(str(packet.semantic["concept_id"]), packet)
        return True

    def retrieve(self, query: dict[str, Any]) -> list[Any]:
        """检索相关记忆（实现 ``MemoryAPI.retrieve``）。

        优先按 ``trigger`` 关键词经 recaller 跨情景+向量唤醒；若 ``query`` 含
        ``keyword`` 则额外合并语义知识库检索结果。

        Args:
            query: 检索条件字典，识别 ``trigger`` 与 ``keyword`` 键。

        Returns:
            匹配的 ``MemoryPacket`` 列表（决策优先，Top-K）。
        """
        trigger = query.get("trigger") or query.get("keyword") or ""
        results = self.recall(trigger)
        # 额外的语义知识检索（与唤醒结果合并去重）
        keyword = query.get("keyword")
        if keyword:
            knowledge = self.semantic.search(keyword)
            existing_ids = {m.task_id for m in results}
            for m in knowledge:
                if m.task_id not in existing_ids:
                    results.append(m)
        return results

    # ---- 认知循环专用接口（供编排器调用） ----

    def recall(self, trigger: str) -> list[MemoryPacket]:
        """根据触发词唤醒相关历史经验（封装 recaller）。

        跨情景记忆与向量记忆做关键词匹配，决策类优先，返回 Top-5。

        Args:
            trigger: 触发回忆的关键词或短语。

        Returns:
            命中的记忆片段列表，长度不超过 5。
        """
        return recall(trigger, self.episodic.all(), self.vector.all())

    def search_knowledge(self, keyword: str) -> list[MemoryPacket]:
        """查询语义知识库（ATT&CK/CVE）。

        Args:
            keyword: 检索关键词，如 ``"lateral"``、``"扫描"``。

        Returns:
            命中的知识条目列表。
        """
        return self.semantic.search(keyword)

    def compress(self, session_id: str, budget: int) -> list[MemoryPacket]:
        """在 token 预算内压缩指定会话的工作记忆栈（封装 compactor）。

        压缩后用结果替换该会话的工作记忆栈，保留决策与最近步，其余合并为摘要。

        Args:
            session_id: 目标会话标识符。
            budget: 允许的最大 token 数。

        Returns:
            压缩后的工作记忆列表。
        """
        stack = self.working.get(session_id)
        compressed = compress(stack, budget)
        # 用压缩结果替换工作记忆栈：清空后回填，并给每个包盖上目标 session_id
        # （compactor 生成的 digest 包默认 session_id 为空，需补齐否则会落入全局栈）
        self.working.clear(session_id)
        for m in compressed:
            m.session_id = session_id
            self.working.add(m)
        return compressed

    def end_session(self, session_id: str) -> None:
        """结束会话，回收工作记忆（情景/语义/向量保留）。

        Args:
            session_id: 待结束的会话标识符。
        """
        self.working.clear(session_id)
