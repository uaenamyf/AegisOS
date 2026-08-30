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

from aegisos_agents.memory.archive.store import ArchiveStore
from aegisos_agents.memory.cache.store import MemoryCache
from aegisos_agents.memory.checkpoint.manager import CheckpointManager
from aegisos_agents.memory.compression.compactor import compress
from aegisos_agents.memory.episodic.store import EpisodicMemory
from aegisos_agents.memory.reflection.engine import ReflectionEngine
from aegisos_agents.memory.retrieval.engine import RetrievalEngine
from aegisos_agents.memory.semantic.store import SemanticMemory
from aegisos_agents.memory.snapshot.manager import SnapshotManager
from aegisos_agents.memory.sync.sync import MemorySync
from aegisos_agents.memory.vector.store import VectorMemory
from aegisos_agents.memory.working.store import WorkingMemory
from data.api import GraphStoreAPI, VectorStoreAPI
from protocol.memory import MemoryPacket


class MemoryStore:
    """记忆集成存储 —— 聚合四层记忆 + 压缩 + 唤醒 + 7 个 v2 子模块，实现 ``MemoryAPI``。

    持有工作/情景/语义/向量四层子存储 + 缓存/检索/检查点/反思/归档/快照/同步
    七个 v2 子模块，对外提供统一的读写检索接口，并在内部按记忆内容自动路由到
    对应层级，串联压缩与唤醒形成认知闭环。

    Attributes:
        working: 工作记忆存储（会话级临时上下文）。
        episodic: 情景记忆存储（跨会话历史经验）。
        semantic: 语义记忆存储（ATT&CK/CVE 知识库）。
        vector: 向量记忆存储（余弦相似度检索，Qdrant 预留）。
        retrieval_engine: v2 混合检索引擎（向量+关键词+图 RRF 融合）。
        cache: v2 二级记忆缓存（L1 查询 + L2 热点 LRU）。
        checkpoint: v2 检查点管理器（任务中断恢复）。
        reflection: v2 反思引擎（三维经验质量评估）。
        archive: v2 冷数据归档存储。
        snapshot: v2 全局快照管理器。
        sync: v2 端边云记忆同步管理器。
    """

    # date: 2026-08-06
    # dev: czy
    # changelog: 新增 vector_backend/graph_backend 可选注入，对接 data 层存储后端
    def __init__(
        self,
        vector_backend: VectorStoreAPI | None = None,
        graph_backend: GraphStoreAPI | None = None,
    ) -> None:
        """初始化记忆集成存储，装配四层子存储 + 七个 v2 子模块。

        Args:
            vector_backend: 可选的外部向量存储后端（默认 None → 内置内存实现）。
            graph_backend: 可选的外部图存储后端（默认 None → 内置内存知识库）。
        """
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(seed=True, graph_backend=graph_backend)
        self.vector = VectorMemory(backend=vector_backend)
        # ---- v2 新增：7 个子模块 ----
        self.retrieval_engine = RetrievalEngine(self.vector, self.semantic, self.episodic)
        self.cache = MemoryCache()
        self.checkpoint = CheckpointManager(self)
        self.reflection = ReflectionEngine()
        self.archive = ArchiveStore()
        self.snapshot = SnapshotManager()
        self.sync = MemorySync()

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

    # date: 2026-08-01
    # dev: 123 chen
    # changelog: 新增缓存失效（cache.invalidate）与反思预评估（reflection.evaluate）
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
        # [v2] 失效相关缓存
        self.cache.invalidate(packet.task_id)
        # [v2] 对新决策预计算评估分
        if packet.kind == "decision":
            self.reflection.evaluate(packet)
        return True

    # date: 2026-08-01
    # dev: 123 chen
    # changelog: 替换为 RetrievalEngine 混合检索 + ReflectionEngine 反思排序
    def retrieve(self, query: dict[str, Any]) -> list[Any]:
        """检索相关记忆（v2：委托 RetrievalEngine 做混合检索 + 反思排序）。

        Args:
            query: 检索条件字典，识别 ``trigger`` / ``keyword`` / ``embedding`` / ``channels`` 键。

        Returns:
            匹配的 ``MemoryPacket`` 列表（质量评分高的优先，Top-K）。
        """
        trigger = query.get("trigger") or query.get("keyword") or ""
        embedding = query.get("embedding")
        channels = query.get("channels")
        top_k = query.get("top_k", 10)
        if not trigger and not embedding:
            return []
        scored = self.retrieval_engine.retrieve(
            trigger, query_embedding=embedding, channels=channels, top_k=top_k
        )
        ranked = self.reflection.rank([s.packet for s in scored])
        return [p for p, _ in ranked[:top_k]]

    # ---- 认知循环专用接口（供编排器调用） ----

    # date: 2026-08-01
    # dev: 123 chen
    # changelog: 升级为三级流水线（L1缓存→RetrievalEngine RRF混合检索→ReflectionEngine排序）
    def recall(self, trigger: str) -> list[MemoryPacket]:
        """根据触发词唤醒相关历史经验（v2：缓存 → 检索 → 反思三级流水线）。

        1. L1 查询缓存命中直接返回。
        2. 调用混合检索引擎（向量 + 关键词 + 图三通道 RRF 融合）召回 20 条。
        3. 反思引擎按质量评分重排序，返回 Top-5。

        Args:
            trigger: 触发回忆的关键词或短语。

        Returns:
            命中的记忆片段列表，长度不超过 5。
        """
        # 1) L1 查询缓存
        cached = self.cache.get_query(trigger)
        if cached is not None:
            return cached
        # 2) 混合检索（三通道 RRF 融合）
        scored = self.retrieval_engine.retrieve(trigger, top_k=20)
        # 3) 反思重排序
        ranked = self.reflection.rank([s.packet for s in scored])
        results = [p for p, _ in ranked[:5]]
        # 4) 记录引用 + 写入 L1 缓存
        for pkt in results:
            if pkt.task_id:
                self.reflection.record_reference(pkt.task_id)
            self.cache.touch(pkt.task_id)
        self.cache.set_query(trigger, results)
        return results

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

    # ---- v2 编排器钩子 ----

    # date: 2026-08-01
    # dev: 123 chen
    # changelog: 新增编排器钩子 checkpoint_cycle / archive_cycle / snapshot_cycle
    def checkpoint_cycle(self, session_id: str, state: dict) -> str | None:
        """每步调用，内部计步，每 N 步自动保存检查点。

        编排器（如 CyberOrchestrator）在每个执行步后调用此方法，
        由 ``CheckpointManager.maybe_save`` 内部计数并在达到间隔时触发保存。

        Args:
            session_id: 当前会话标识符。
            state: 编排器当前状态字典（step_index / completed_tasks / working_summary / topology_snapshot）。

        Returns:
            触发保存时返回 checkpoint_id；否则返回 ``None``。
        """
        return self.checkpoint.maybe_save(session_id, state)

    def archive_cycle(self) -> int:
        """压缩后触发冷数据下沉。

        将情景记忆中从未被引用（``is_cold`` 返回 True）且不在最近 100 条内的
        记忆下沉到归档存储。

        Returns:
            本次归档的记忆条数。
        """
        all_episodes = self.episodic.all()
        if len(all_episodes) <= 100:
            return 0
        cold = [m for m in all_episodes[:-100] if self.reflection.is_cold(m.task_id)]
        if not cold:
            return 0
        return self.archive.archive(cold)

    def snapshot_cycle(self, session_id: str, state: dict | None = None) -> str:
        """阶段完成后触发快照。

        拍摄当前记忆子系统全局统计快照，供 replay/monitor 使用。

        Args:
            session_id: 当前会话标识符。
            state: 可选的编排器拓扑状态字典。

        Returns:
            快照标识符。
        """
        stats: dict[str, Any] = {
            "working_sessions": len(self.working.sessions()),
            "episodic_total": len(self.episodic),
            "semantic_total": len(self.semantic),
            "vector_total": len(self.vector),
            "archive_total": self.archive.size(),
        }
        if state:
            stats["topology_state"] = state
        return self.snapshot.capture(
            label=f"snapshot_{session_id}",
            state=stats,
        )
