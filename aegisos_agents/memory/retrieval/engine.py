# date: 2026-08-01
# dev: myf
"""混合检索引擎 —— 向量 + 关键词 + 图三通道 RRF 融合检索。

聚合 :class:`VectorMemory`、:class:`SemanticMemory`、:class:`EpisodicMemory`
三条召回通道，通过 Reciprocal Rank Fusion (RRF) 融合排序后返回 Top-K 结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aegisos_agents.memory.episodic.store import EpisodicMemory
from aegisos_agents.memory.semantic.store import SemanticMemory
from aegisos_agents.memory.vector.store import VectorMemory, _cosine
from protocol.memory import MemoryPacket

# 默认通道权重（用于可选加权，当前 RRF 等权）
CHANNEL_WEIGHTS = {"vector": 0.4, "keyword": 0.35, "graph": 0.25}
# RRF 平滑常量 k，防止单通道排名 1 产生无穷大影响
RRF_K = 60


@dataclass
class ScoredPacket:
    """带融合评分的检索结果。

    Attributes:
        packet: 命中的记忆包。
        score: RRF 融合分数（越高越相关）。
        channels: 命中通道列表，如 ``["vector", "keyword"]``。
    """

    packet: MemoryPacket
    score: float = 0.0
    channels: list[str] = field(default_factory=list)


class RetrievalEngine:
    """混合检索引擎 —— 三通道 RRF 融合检索。

    聚合向量（余弦相似度）、关键词（子串匹配）、图（ATT&CK 关联）三条
    召回通道，各通道独立排名后用 RRF 公式融合去重，返回融合排序后的 Top-K。

    Attributes:
        _vector: 向量记忆存储引用（只读）。
        _semantic: 语义记忆存储引用（只读）。
        _episodic: 情景记忆存储引用（只读）。
    """

    def __init__(
        self,
        vector: VectorMemory,
        semantic: SemanticMemory,
        episodic: EpisodicMemory,
    ) -> None:
        """初始化检索引擎，持有三层存储的只读引用。

        Args:
            vector: 向量记忆存储，用于余弦相似度召回。
            semantic: 语义记忆存储（ATT&CK 知识库），用于图关联召回。
            episodic: 情景记忆存储，用于关键词召回。
        """
        self._vector = vector
        self._semantic = semantic
        self._episodic = episodic

    # ---- 公开接口 ----

    def retrieve(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        channels: list[str] | None = None,
        top_k: int = 10,
    ) -> list[ScoredPacket]:
        """三通道混合检索，RRF 融合排序。

        Args:
            query: 查询文本（关键词/图通道使用）。
            query_embedding: 查询向量（向量通道使用），为 None 时跳过向量通道。
            channels: 启用的通道列表，默认全部（``["vector", "keyword", "graph"]``）。
            top_k: 返回结果条数上限。

        Returns:
            按 RRF 融合分降序排列的 ``ScoredPacket`` 列表，长度不超过 ``top_k``。
        """
        if not query and not query_embedding:
            return []
        if channels is None:
            channels = ["vector", "keyword", "graph"]
        # 各通道独立召回（每通道返回 dict[task_id, rank]）
        channel_ranks: dict[str, dict[str, int]] = {}
        if "vector" in channels and query_embedding:
            channel_ranks["vector"] = self._vector_channel(query_embedding, top_k * 2)
        if "keyword" in channels and query:
            channel_ranks["keyword"] = self._keyword_channel(query, top_k * 2)
        if "graph" in channels and query:
            channel_ranks["graph"] = self._graph_channel(query, top_k * 2)
        # RRF 融合
        return self._rrf_fuse(channel_ranks, top_k)

    def add_to_index(self, packet: MemoryPacket) -> None:
        """新记忆加入各通道索引（当前为被动模式：通道按需从 store 拉数据）。

        Args:
            packet: 待索引的记忆包。
        """
        # 当前实现：各通道在 retrieve 时实时从 VectorMemory/SemanticMemory/EpisodicMemory
        # 拉取数据，无需独立索引。本方法为未来预构建索引预留。
        pass

    def rebuild_index(self) -> None:
        """全量重建索引（当前为无操作，数据源为引用存储）。"""
        pass

    # ---- 私有通道 ----

    def _vector_channel(
        self, query_embedding: list[float], top_k: int
    ) -> dict[str, int]:
        """向量通道：余弦相似度检索。

        Returns:
            {task_id: rank}，排名 1 为最相似。
        """
        results = self._vector.search(query_embedding, top_k=top_k)
        return {m.task_id or str(i): i + 1 for i, m in enumerate(results)}

    def _keyword_channel(self, query: str, top_k: int) -> dict[str, int]:
        """关键词通道：在情景记忆与语义记忆中做子串匹配。

        Returns:
            {task_id: rank}，排名 1 为最佳匹配。
        """
        kw = query.lower()
        scored: list[tuple[str, float]] = []
        # 情景记忆匹配
        for m in self._episodic.all():
            if kw in (m.summary or "").lower():
                scored.append((m.task_id, 1.0))
        # 语义记忆匹配
        for m in self._semantic.all():
            text = (m.summary or "") + " " + " ".join(
                str(v) for v in m.semantic.values()
            )
            if kw in text.lower():
                scored.append((m.task_id, 0.8))
        # 去重保留最高分
        best: dict[str, float] = {}
        for tid, score in scored:
            if tid not in best or score > best[tid]:
                best[tid] = score
        # 按分降序编号 rank
        sorted_ids = sorted(best, key=lambda k: best[k], reverse=True)
        return {tid: i + 1 for i, tid in enumerate(sorted_ids[:top_k])}

    def _graph_channel(self, query: str, top_k: int) -> dict[str, int]:
        """图通道：ATT&CK tactic/technique 关联遍历。

        在语义记忆中搜索与查询关键词关联的技战术条目，命中后再通过
        tactic 字段找到同战术阶段的其他条目作为关联扩展。

        Returns:
            {task_id: rank}，排名 1 为最相关。
        """
        kw = query.lower()
        scored: list[tuple[str, float]] = []
        for m in self._semantic.all():
            if not m.semantic:
                continue
            tactic = str(m.semantic.get("tactic", "")).lower()
            technique_id = str(m.semantic.get("technique_id", "")).lower()
            name = str(m.semantic.get("name", "")).lower()
            # 查询命中技战术 ID、名称或战术阶段
            if kw in technique_id or kw in name or kw in tactic:
                scored.append((m.task_id, 1.0))
                # 关联扩展：同一战术阶段的其他技战术
                if kw in tactic:
                    for related in self._semantic.all():
                        if (
                            related.task_id != m.task_id
                            and str(related.semantic.get("tactic", "")).lower() == tactic
                        ):
                            scored.append((related.task_id, 0.6))
        # 去重保留最高分
        best: dict[str, float] = {}
        for tid, score in scored:
            if tid not in best or score > best[tid]:
                best[tid] = score
        sorted_ids = sorted(best, key=lambda k: best[k], reverse=True)
        return {tid: i + 1 for i, tid in enumerate(sorted_ids[:top_k])}

    def _rrf_fuse(
        self, channel_ranks: dict[str, dict[str, int]], top_k: int
    ) -> list[ScoredPacket]:
        """RRF 融合多通道排名结果。

        公式：RRF_score(d, c) = Σ_c 1 / (k + rank_c(d))
        k = RRF_K = 60。

        Args:
            channel_ranks: {channel_name: {task_id: rank}}
            top_k: 返回条数上限。

        Returns:
            按 RRF 融合分降序排列的 ``ScoredPacket`` 列表。
        """
        # 收集所有 task_id → {channel: rank}
        all_ids: dict[str, dict[str, int]] = {}
        for ch, ranks in channel_ranks.items():
            for tid, rank in ranks.items():
                all_ids.setdefault(tid, {})[ch] = rank
        # 计算 RRF 分
        scored: list[ScoredPacket] = []
        for tid, ch_ranks in all_ids.items():
            rrf_score = sum(1.0 / (RRF_K + r) for r in ch_ranks.values())
            hit_channels = list(ch_ranks.keys())
            # 查找原始 MemoryPacket（优先从 episodic 找，其次 semantic）
            packet = self._lookup_packet(tid)
            if packet is not None:
                scored.append(ScoredPacket(packet=packet, score=rrf_score, channels=hit_channels))
        # 按 RRF 分降序
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]

    def _lookup_packet(self, task_id: str) -> MemoryPacket | None:
        """按 task_id 在三个存储中查找 MemoryPacket。

        Args:
            task_id: 目标 task_id。

        Returns:
            找到的 MemoryPacket；三个存储都找不到时返回 None。
        """
        # 查情景记忆
        m = self._episodic.by_task(task_id)
        if m is not None:
            return m
        # 查语义记忆
        m = self._semantic.get(task_id)
        if m is not None:
            return m
        # 查向量记忆（all() 遍历）
        for vm in self._vector.all():
            if vm.task_id == task_id:
                return vm
        return None
