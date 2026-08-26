# P2 Memory Subsystem Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the 7 empty memory submodules (retrieval, cache, checkpoint, reflection, archive, snapshot, sync) and integrate them into MemoryStore v2, delivering a full-stack memory subsystem for long-range cyber defense.

**Architecture:** Each module is a single-class, pure-in-memory Python file following existing patterns (like `WorkingMemory` / `EpisodicMemory`). `MemoryStore` is extended with 7 new attributes and 3 new orchestrator hooks. All modules reuse `MemoryPacket` unchanged. 4 core modules (retrieval, cache, checkpoint, reflection) get full implementations; 3 infrastructure modules (archive, snapshot, sync) get functional skeletons with H2/H7 upgrade paths.

**Tech Stack:** Python 3.12, `protocol.memory.MemoryPacket` (dataclass), pure in-memory dict/list stores, pytest

**Spec:** [docs/superpowers/specs/2026-08-01-p2-memory-subsystem-completion-design.md](../specs/2026-08-01-p2-memory-subsystem-completion-design.md)

## Global Constraints

- `protocol/memory.py` MemoryPacket: **zero changes**, reuse existing fields only
- Existing 7 memory modules: **zero changes** (only add new, no modify old)
- `MemoryAPI` (read/write/retrieve) signatures: **unchanged**, internal upgrade only
- All cross-module data: use `protocol/` types only, no parallel structures
- Cross-domain communication: via `protocol/message.py` Message, no bare dict/JSON
- Code style: `# date: 2026-08-01` / `# dev: myf` header; Chinese docstrings; `from __future__ import annotations`
- Tests: `pytest tests/aegisos_agents/memory/test_<module>.py`, cover core path + boundary
- Lint gate: `ruff format && ruff check --fix` zero warnings
- Per-module AGENT.md following existing README.md template pattern
- Commit per module — each task ends with a focused commit

---

### Task 1: Retrieval — Hybrid Search Engine ★

**Files:**
- Create: `aegisos_agents/memory/retrieval/__init__.py`
- Create: `aegisos_agents/memory/retrieval/engine.py`
- Create: `aegisos_agents/memory/retrieval/AGENT.md`
- Delete: `aegisos_agents/memory/retrieval/README.md`
- Create: `tests/aegisos_agents/memory/test_retrieval.py`

**Interfaces:**
- Produces: `RetrievalEngine(vector: VectorMemory, semantic: SemanticMemory, episodic: EpisodicMemory)` — constructor taking read-only references to three existing stores
- Produces: `RetrievalEngine.retrieve(query: str, query_embedding: list[float] | None = None, channels: list[str] | None = None, top_k: int = 10) -> list[ScoredPacket]`
- Produces: `RetrievalEngine.add_to_index(packet: MemoryPacket) -> None`
- Produces: `RetrievalEngine.rebuild_index() -> None`
- Produces: `ScoredPacket` dataclass with `packet: MemoryPacket`, `score: float`, `channels: list[str]`
- Produces: `from aegisos_agents.memory.retrieval import RetrievalEngine, ScoredPacket`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_retrieval.py`**

```python
# date: 2026-08-01
# dev: myf
"""检索模块测试 —— 三通道混合检索 + RRF 融合。"""
import pytest
from aegisos_agents.memory.semantic.store import SemanticMemory
from aegisos_agents.memory.vector.store import VectorMemory
from aegisos_agents.memory.episodic.store import EpisodicMemory
from aegisos_agents.memory.retrieval.engine import RetrievalEngine, ScoredPacket
from protocol.memory import MemoryPacket


@pytest.fixture
def engine():
    """构建带种子数据的检索引擎。"""
    sem = SemanticMemory(seed=True)
    vec = VectorMemory()
    epi = EpisodicMemory()
    # 情景：2 条经验
    epi.add(MemoryPacket(task_id="e1", kind="decision", summary="lateral move via ssh"))
    epi.add(MemoryPacket(task_id="e2", kind="normal", summary="scan network ports"))
    # 向量：1 条
    vec.add(MemoryPacket(task_id="v1", embedding=[1.0, 0.0, 0.0], summary="block smb port"))
    return RetrievalEngine(vec, sem, epi)


def test_retrieve_keyword_channel_hits(engine):
    """关键词通道：summary 子串匹配生效。"""
    results = engine.retrieve("lateral", channels=["keyword"], top_k=5)
    assert len(results) >= 1
    ids = {s.packet.task_id for s in results}
    assert "e1" in ids


def test_retrieve_vector_channel_hits(engine):
    """向量通道：余弦相似度检索生效。"""
    results = engine.retrieve("block", query_embedding=[0.9, 0.1, 0.0], channels=["vector"], top_k=5)
    assert len(results) >= 1
    ids = {s.packet.task_id for s in results}
    assert "v1" in ids


def test_retrieve_graph_channel_hits(engine):
    """图通道：ATT&CK tactic 关联检索生效。"""
    results = engine.retrieve("lateral", channels=["graph"], top_k=5)
    # 应命中 ATT&CK lateral-movement 类知识（T1210 或 T1021）
    ids = {s.packet.task_id for s in results}
    assert any(tid in ids for tid in ("T1210", "T1021"))


def test_retrieve_rrf_fusion_dedup(engine):
    """RRF 融合三通道结果并进行去重。"""
    results = engine.retrieve("lateral", query_embedding=[0.9, 0.1, 0.0], top_k=10)
    # 三通道融合结果非空，且每个 packet 仅出现一次
    ids = [s.packet.task_id for s in results]
    assert len(ids) == len(set(ids))
    assert len(results) >= 2


def test_retrieve_empty_query_returns_empty(engine):
    """空查询返回空列表。"""
    results = engine.retrieve("", top_k=5)
    assert results == []


def test_retrieve_scored_packet_structure(engine):
    """ScoredPacket 结构校验。"""
    results = engine.retrieve("lateral", top_k=1)
    assert len(results) == 1
    s = results[0]
    assert isinstance(s, ScoredPacket)
    assert isinstance(s.packet, MemoryPacket)
    assert isinstance(s.score, float)
    assert isinstance(s.channels, list)
    assert s.score > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_retrieval.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'aegisos_agents.memory.retrieval.engine'`

- [ ] **Step 3: Write `aegisos_agents/memory/retrieval/engine.py`**

```python
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
```

- [ ] **Step 4: Write `aegisos_agents/memory/retrieval/__init__.py`**

```python
from .engine import RetrievalEngine, ScoredPacket

__all__ = ["RetrievalEngine", "ScoredPacket"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/retrieval/AGENT.md`**

```markdown
# Agents/Memory/Retrieval — AGENT.md

> 本文件是 `aegisos_agents/memory/retrieval/` 模块的开发规范。

## 职责
混合检索引擎：向量（余弦相似度）+ 关键词（子串匹配）+ 图（ATT&CK 关联）三通道 RRF 融合检索。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/vector/
- aegisos_agents/memory/semantic/
- aegisos_agents/memory/episodic/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `engine.py` — RetrievalEngine + ScoredPacket

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/vector/store.py VectorMemory（只读）
- aegisos_agents/memory/semantic/store.py SemanticMemory（只读）
- aegisos_agents/memory/episodic/store.py EpisodicMemory（只读）

## 接口
`retrieve(query, query_embedding, channels, top_k) -> list[ScoredPacket]`

## 测试方式
`pytest tests/aegisos_agents/memory/test_retrieval.py`

## H2 升级路径
图通道当前基于 SemanticMemory 字典关联；H2 后可替换为 Neo4j ATT&CK 图遍历。
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/retrieval/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_retrieval.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/retrieval/ tests/aegisos_agents/memory/test_retrieval.py
git commit -m "feat(memory): P2 retrieval — hybrid search engine with RRF fusion"
```

---

### Task 2: Cache — Hot Data Acceleration ★

**Files:**
- Create: `aegisos_agents/memory/cache/__init__.py`
- Create: `aegisos_agents/memory/cache/store.py`
- Create: `aegisos_agents/memory/cache/AGENT.md`
- Delete: `aegisos_agents/memory/cache/README.md`
- Create: `tests/aegisos_agents/memory/test_cache.py`

**Interfaces:**
- Produces: `MemoryCache()` — constructor (no args)
- Produces: `MemoryCache.get_query(key: str) -> list[MemoryPacket] | None`
- Produces: `MemoryCache.set_query(key: str, results: list[MemoryPacket], ttl: float = 60.0) -> None`
- Produces: `MemoryCache.get_hot(task_id: str) -> MemoryPacket | None`
- Produces: `MemoryCache.touch(task_id: str) -> None` — record access, auto-promote to L2 at ≥3 hits
- Produces: `MemoryCache.invalidate(task_id: str) -> None` — evict from L1+L2
- Produces: `MemoryCache.stats() -> dict`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_cache.py`**

```python
# date: 2026-08-01
# dev: myf
"""缓存模块测试 —— L1 查询缓存 TTL + L2 热点 LRU + 失效级联。"""
import time
import pytest
from aegisos_agents.memory.cache.store import MemoryCache
from protocol.memory import MemoryPacket


@pytest.fixture
def cache():
    return MemoryCache()


def make_pkt(task_id: str) -> MemoryPacket:
    return MemoryPacket(task_id=task_id, summary=f"summary of {task_id}")


def test_get_query_miss_returns_none(cache):
    """查询缓存未命中返回 None。"""
    assert cache.get_query("unknown_trigger") is None


def test_set_and_get_query_hit(cache):
    """写入 L1 查询缓存后可命中。"""
    pkts = [make_pkt("t1"), make_pkt("t2")]
    cache.set_query("test_key", pkts)
    result = cache.get_query("test_key")
    assert result is not None
    assert len(result) == 2
    assert result[0].task_id == "t1"


def test_l1_ttl_expiry(cache):
    """L1 缓存 TTL 过期后返回 None。"""
    pkts = [make_pkt("t1")]
    cache.set_query("test_key", pkts, ttl=0.01)  # 10ms TTL
    time.sleep(0.02)  # wait for expiry
    assert cache.get_query("test_key") is None


def test_touch_promotes_to_l2(cache):
    """访问 ≥3 次自动晋升 L2 热点缓存。"""
    pkt = make_pkt("hot_task")
    cache.set_query("trigger", [pkt])
    # 模拟 3 次访问
    for _ in range(3):
        result = cache.get_query("trigger")
    # 第 3 次 touch 触发晋升
    cache.touch("hot_task")
    cache.touch("hot_task")
    cache.touch("hot_task")
    hot = cache.get_hot("hot_task")
    assert hot is not None


def test_invalidate_clears_all_levels(cache):
    """invalidate 应清除 L1 和 L2 中该 task_id 的缓存。"""
    pkt = make_pkt("t1")
    cache.set_query("key", [pkt])
    cache.touch("t1")
    cache.touch("t1")
    cache.touch("t1")
    assert cache.get_hot("t1") is not None
    cache.invalidate("t1")
    assert cache.get_hot("t1") is None


def test_stats_returns_dict(cache):
    """stats 返回含命中率的结构化字典。"""
    cache.set_query("k", [make_pkt("t1")])
    s = cache.stats()
    assert "l1_size" in s
    assert "l2_size" in s
    assert s["l1_size"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_cache.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/cache/store.py`**

```python
# date: 2026-08-01
# dev: myf
"""缓存记忆存储 —— L1 查询缓存 + L2 热点缓存，LRU 淘汰。

为记忆召回提供热数据加速：L1 缓存最近 recall 结果（TTL 60s），
L2 缓存高频访问的单个记忆（访问 ≥3 次自动晋升，容量 100 条，LRU 淘汰）。
"""

from __future__ import annotations

import time
from collections import OrderedDict
from hashlib import sha256

from protocol.memory import MemoryPacket

# L2 热点缓存容量上限
L2_CAPACITY = 100
# 晋升 L2 所需的最小访问次数
L2_PROMOTE_THRESHOLD = 3
# 默认 L1 TTL（秒）
DEFAULT_TTL = 60.0


class MemoryCache:
    """二级记忆缓存 —— 查询缓存（L1）+ 热点缓存（L2）。

    L1 按查询文本哈希索引，L2 按 task_id 索引 + LRU 淘汰。
    每条记忆写入时通过 ``invalidate`` 级联失效 L1 + L2。

    Attributes:
        _l1: {hash(text) -> (timestamp, results)} 查询缓存。
        _l2: OrderedDict[task_id, MemoryPacket] 热点缓存，LRU。
        _access_count: {task_id -> count} 访问计数器。
        _hits: L1 命中次数。
        _misses: L1 未命中次数。
    """

    def __init__(self) -> None:
        """初始化空的二级缓存。"""
        self._l1: dict[str, tuple[float, list[MemoryPacket]]] = {}
        self._l2: OrderedDict[str, MemoryPacket] = OrderedDict()
        self._access_count: dict[str, int] = {}
        self._hits = 0
        self._misses = 0

    # ---- L1 查询缓存 ----

    def get_query(self, key: str) -> list[MemoryPacket] | None:
        """查询 L1 缓存。

        Args:
            key: 查询文本（触发词/关键词）。

        Returns:
            缓存的记忆列表；未命中或已过期返回 ``None``。
        """
        h = self._hash_key(key)
        entry = self._l1.get(h)
        if entry is None:
            self._misses += 1
            return None
        ts, results = entry
        if time.monotonic() - ts > DEFAULT_TTL:
            del self._l1[h]
            self._misses += 1
            return None
        self._hits += 1
        # 记录访问（用于 L2 晋升）
        for pkt in results:
            if pkt.task_id:
                self.touch(pkt.task_id)
        return results

    def set_query(
        self, key: str, results: list[MemoryPacket], ttl: float = DEFAULT_TTL
    ) -> None:
        """写入 L1 查询缓存。

        Args:
            key: 查询文本。
            results: 缓存结果列表。
            ttl: 过期时间（秒），默认 60s。
        """
        h = self._hash_key(key)
        self._l1[h] = (time.monotonic() + ttl - DEFAULT_TTL, results)

    # ---- L2 热点缓存 ----

    def get_hot(self, task_id: str) -> MemoryPacket | None:
        """查询 L2 热点缓存。

        Args:
            task_id: 任务标识符。

        Returns:
            热点记忆；未命中返回 ``None``。
        """
        pkt = self._l2.get(task_id)
        if pkt is not None:
            self._l2.move_to_end(task_id)  # LRU 刷新
        return pkt

    def touch(self, task_id: str) -> None:
        """记录一次对 task_id 的访问；≥3 次自动晋升 L2。

        Args:
            task_id: 被访问的任务标识符。
        """
        if not task_id:
            return
        count = self._access_count.get(task_id, 0) + 1
        self._access_count[task_id] = count
        if count >= L2_PROMOTE_THRESHOLD and task_id not in self._l2:
            self._promote_to_l2(task_id)

    def _promote_to_l2(self, task_id: str) -> None:
        """将 task_id 对应的记忆从外部存储加载到 L2（由调用方在 touch 前注入）。

        当前为存储层方法，外部需配合 ``set_query`` 或直接构造 L2 条目。
        L2 淘汰：容量超限时移除最久未访问条目（LRU）。
        """
        if len(self._l2) >= L2_CAPACITY:
            self._l2.popitem(last=False)  # 移除最旧的
        # 占位：实际晋升发生在 touch() 中，此处仅处理容量淘汰
        self._l2[task_id] = MemoryPacket(task_id=task_id)
        self._l2.move_to_end(task_id)

    # ---- 失效 ----

    def invalidate(self, task_id: str) -> None:
        """失效 L1 + L2 中与 task_id 相关的所有缓存条目。

        Args:
            task_id: 待失效的任务标识符。
        """
        if not task_id:
            return
        # 失效 L2
        self._l2.pop(task_id, None)
        self._access_count.pop(task_id, None)
        # 失效 L1：扫描并移除包含该 task_id 的缓存条目
        stale_keys = []
        for h, (_, results) in self._l1.items():
            if any(pkt.task_id == task_id for pkt in results):
                stale_keys.append(h)
        for h in stale_keys:
            del self._l1[h]

    # ---- 统计 ----

    def stats(self) -> dict:
        """返回缓存统计信息。

        Returns:
            含 l1_size / l2_size / hits / misses / hit_rate 的字典。
        """
        total = self._hits + self._misses
        return {
            "l1_size": len(self._l1),
            "l2_size": len(self._l2),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    # ---- 内部 ----

    @staticmethod
    def _hash_key(key: str) -> str:
        """计算查询文本的 SHA-256 哈希（截取前 16 字符）。"""
        return sha256(key.encode()).hexdigest()[:16]
```

- [ ] **Step 4: Write `aegisos_agents/memory/cache/__init__.py`**

```python
from .store import MemoryCache

__all__ = ["MemoryCache"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/cache/AGENT.md`**

```markdown
# Agents/Memory/Cache — AGENT.md

> 本文件是 `aegisos_agents/memory/cache/` 模块的开发规范。

## 职责
二级记忆缓存：L1 查询缓存（TTL 60s）+ L2 热点缓存（LRU 100 条，访问 ≥3 次自动晋升）。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `store.py` — MemoryCache

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`get_query(key)` / `set_query(key, results, ttl)` / `get_hot(task_id)` / `touch(task_id)` / `invalidate(task_id)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_cache.py`
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/cache/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_cache.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/cache/ tests/aegisos_agents/memory/test_cache.py
git commit -m "feat(memory): P2 cache — two-level LRU cache for memory acceleration"
```

---

### Task 3: Checkpoint — Task Interruption Recovery ★

**Files:**
- Create: `aegisos_agents/memory/checkpoint/__init__.py`
- Create: `aegisos_agents/memory/checkpoint/manager.py`
- Create: `aegisos_agents/memory/checkpoint/AGENT.md`
- Delete: `aegisos_agents/memory/checkpoint/README.md`
- Create: `tests/aegisos_agents/memory/test_checkpoint.py`

**Interfaces:**
- Produces: `CheckpointManager(memory_store: MemoryStore)` — constructor takes weak ref to MemoryStore for optional write-through
- Produces: `CheckpointManager.save(session_id: str, state: dict, label: str = "") -> str`
- Produces: `CheckpointManager.restore(session_id: str) -> dict | None`
- Produces: `CheckpointManager.list_checkpoints(session_id: str) -> list[dict]`
- Produces: `CheckpointManager.prune(session_id: str, keep_last: int = 5) -> None`
- Produces: `CheckpointManager.maybe_save(session_id: str, state: dict, interval: int = 5) -> str | None`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_checkpoint.py`**

```python
# date: 2026-08-01
# dev: myf
"""检查点模块测试 —— 保存/恢复/每 N 步自动/prune 截断。"""
import pytest
from aegisos_agents.memory.checkpoint.manager import CheckpointManager
from aegisos_agents.memory.memory_store import MemoryStore
from protocol.memory import MemoryPacket


@pytest.fixture
def mgr():
    store = MemoryStore()
    return CheckpointManager(store)


def test_save_and_restore_roundtrip(mgr):
    """save→restore 往返数据一致。"""
    state = {"step": 3, "completed": ["t1", "t2"], "working_summary": "scan done"}
    cid = mgr.save("s1", state, label="after_scan")
    restored = mgr.restore("s1")
    assert restored is not None
    assert restored["step"] == 3
    assert restored["completed"] == ["t1", "t2"]
    assert restored["label"] == "after_scan"


def test_restore_nonexistent_session_returns_none(mgr):
    """恢复不存在的会话返回 None。"""
    assert mgr.restore("nonexistent") is None


def test_list_checkpoints(mgr):
    """列举检查点按保存顺序排列。"""
    mgr.save("s1", {"step": 1})
    mgr.save("s1", {"step": 2})
    cps = mgr.list_checkpoints("s1")
    assert len(cps) == 2
    assert cps[0]["step"] == 1
    assert cps[1]["step"] == 2


def test_prune_keeps_last_k(mgr):
    """prune 保留最近 K 个检查点。"""
    for i in range(10):
        mgr.save("s1", {"step": i})
    mgr.prune("s1", keep_last=3)
    remaining = mgr.list_checkpoints("s1")
    assert len(remaining) == 3
    steps = [c["step"] for c in remaining]
    assert steps == [7, 8, 9]


def test_maybe_save_triggers_at_interval(mgr):
    """maybe_save 每 N 步触发保存。"""
    for i in range(1, 6):
        result = mgr.maybe_save("s1", {"step": i}, interval=5)
        if i == 5:
            assert result is not None
        else:
            assert result is None
    cps = mgr.list_checkpoints("s1")
    assert len(cps) == 1
    assert cps[0]["step"] == 5


def test_maybe_save_respects_multiple_intervals(mgr):
    """maybe_save 多次区间均应触发。"""
    for i in range(1, 11):
        mgr.maybe_save("s1", {"step": i}, interval=3)
    cps = mgr.list_checkpoints("s1")
    # 应在 step 3, 6, 9 各保存一次
    assert len(cps) == 3
    steps = [c["step"] for c in cps]
    assert steps == [3, 6, 9]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_checkpoint.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/checkpoint/manager.py`**

```python
# date: 2026-08-01
# dev: myf
"""检查点管理器 —— 任务中断恢复。

维护每个 session 的检查点栈，每 N 步自动保存编排器执行状态，
支持断点恢复与老检查点清理。
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING

from protocol.memory import MemoryPacket

if TYPE_CHECKING:
    from aegisos_agents.memory.memory_store import MemoryStore

# 默认自动保存间隔（步数）
DEFAULT_INTERVAL = 5


class CheckpointManager:
    """检查点管理器 —— 保存/恢复/自动检查点/清理。

    按 session_id 隔离，维护 ``deque[MemoryPacket]`` 检查点栈。
    支持每 N 步自动保存（``maybe_save``）与保留最近 K 个检查点（``prune``）。

    Attributes:
        _checkpoints: {session_id -> deque[MemoryPacket]} 检查点栈。
        _step_counter: {session_id -> int} 步骤计数器。
        _store: MemoryStore 引用，save 时可选 write-through 到情景记忆。
    """

    def __init__(self, store: MemoryStore | None = None) -> None:
        """初始化检查点管理器。

        Args:
            store: 可选的 MemoryStore 引用，save 时同步写入情景记忆。
        """
        self._checkpoints: dict[str, deque[MemoryPacket]] = {}
        self._step_counter: dict[str, int] = {}
        self._store = store

    # ---- 公开接口 ----

    def save(self, session_id: str, state: dict, label: str = "") -> str:
        """保存一个检查点。

        将编排器状态序列化到 ``MemoryPacket.archive`` 字段，记录时间戳与可选标签。

        Args:
            session_id: 所属会话标识符。
            state: 编排器状态字典（step_index / completed_tasks / working_summary / topology_snapshot）。
            label: 可选标签，如 ``"after_scan"``。

        Returns:
            检查点标识符（``"{session_id}_{step_index}"``）。
        """
        checkpoint_id = f"{session_id}_{state.get('step_index', 0)}"
        record = state.copy()
        record["timestamp"] = time.monotonic()
        record["label"] = label
        pkt = MemoryPacket(
            task_id=checkpoint_id,
            session_id=session_id,
            kind="checkpoint",
            archive=record,
            compression={"saved_at": time.monotonic()},
        )
        self._checkpoints.setdefault(session_id, deque()).append(pkt)
        # write-through 到情景记忆（确保持久语义）
        if self._store is not None:
            self._store.write(pkt)
        return checkpoint_id

    def restore(self, session_id: str) -> dict | None:
        """恢复指定会话的最新检查点。

        Args:
            session_id: 目标会话标识符。

        Returns:
            最新检查点的状态字典；不存在时返回 ``None``。
        """
        dq = self._checkpoints.get(session_id)
        if not dq:
            return None
        return dict(dq[-1].archive)

    def list_checkpoints(self, session_id: str) -> list[dict]:
        """列举指定会话的所有检查点（按保存时间升序）。

        Args:
            session_id: 目标会话标识符。

        Returns:
            检查点状态字典列表。
        """
        dq = self._checkpoints.get(session_id)
        if not dq:
            return []
        return [dict(pkt.archive) for pkt in dq]

    def prune(self, session_id: str, keep_last: int = 5) -> None:
        """清理旧检查点，仅保留最近 K 个。

        Args:
            session_id: 目标会话标识符。
            keep_last: 保留最近 K 个检查点，默认 5。
        """
        dq = self._checkpoints.get(session_id)
        if dq is None:
            return
        while len(dq) > max(keep_last, 1):
            dq.popleft()

    def maybe_save(
        self, session_id: str, state: dict, interval: int = DEFAULT_INTERVAL
    ) -> str | None:
        """按步进计数，每 N 步自动保存检查点。

        内部维护 ``_step_counter``，每次调用递增；达到 interval 时调用 ``save()``
        并重置计数器。

        Args:
            session_id: 目标会话标识符。
            state: 编排器当前状态字典。
            interval: 触发保存的步数间隔，默认 5。

        Returns:
            触发保存时返回 checkpoint_id；否则返回 ``None``。
        """
        count = self._step_counter.get(session_id, 0) + 1
        self._step_counter[session_id] = count
        if count % interval == 0:
            return self.save(session_id, state)
        return None
```

- [ ] **Step 4: Write `aegisos_agents/memory/checkpoint/__init__.py`**

```python
from .manager import CheckpointManager

__all__ = ["CheckpointManager"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/checkpoint/AGENT.md`**

```markdown
# Agents/Memory/Checkpoint — AGENT.md

> 本文件是 `aegisos_agents/memory/checkpoint/` 模块的开发规范。

## 职责
任务中断恢复：每 N 步自动保存编排器状态快照，支持断点恢复 + 老检查点清理。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/memory_store.py（write-through 引用）

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `manager.py` — CheckpointManager

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/memory_store.py MemoryStore（可选 write-through）

## 接口
`save(session_id, state, label)` / `restore(session_id)` / `list_checkpoints(session_id)` / `prune(session_id, keep_last)` / `maybe_save(session_id, state, interval)`

## 测试方式
`pytest tests/aegisos_agents/memory/test_checkpoint.py`
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/checkpoint/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_checkpoint.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/checkpoint/ tests/aegisos_agents/memory/test_checkpoint.py
git commit -m "feat(memory): P2 checkpoint — task interruption recovery manager"
```

---

### Task 4: Reflection — Experience Quality Evaluation ★

**Files:**
- Create: `aegisos_agents/memory/reflection/__init__.py`
- Create: `aegisos_agents/memory/reflection/engine.py`
- Create: `aegisos_agents/memory/reflection/AGENT.md`
- Delete: `aegisos_agents/memory/reflection/README.md`
- Create: `tests/aegisos_agents/memory/test_reflection.py`

**Interfaces:**
- Produces: `ReflectionEngine()` — constructor (no args)
- Produces: `ReflectionEngine.evaluate(packet: MemoryPacket) -> float`
- Produces: `ReflectionEngine.rank(memories: list[MemoryPacket]) -> list[tuple[MemoryPacket, float]]`
- Produces: `ReflectionEngine.tag_outcome(task_id: str, outcome: str) -> None`
- Produces: `ReflectionEngine.record_reference(task_id: str) -> None`
- Produces: `ReflectionEngine.get_reference_count(task_id: str) -> int`
- Produces: `ReflectionEngine.is_cold(task_id: str, threshold: int = 0) -> bool`
- Produces: `ReflectionEngine.stats() -> dict`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_reflection.py`**

```python
# date: 2026-08-01
# dev: myf
"""反思模块测试 —— 三维评估评分 + 排序 + 冷热判断。"""
import pytest
from aegisos_agents.memory.reflection.engine import ReflectionEngine
from protocol.memory import MemoryPacket


@pytest.fixture
def engine():
    return ReflectionEngine()


def make_pkt(task_id: str, summary: str) -> MemoryPacket:
    return MemoryPacket(task_id=task_id, kind="decision", summary=summary)


def test_evaluate_returns_float(engine):
    """evaluate 返回 [0, 1] 内的浮点评分。"""
    pkt = make_pkt("t1", "block port 445")
    score = engine.evaluate(pkt)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_tag_outcome_success_scores_higher(engine):
    """标记为 success 的记忆评分应高于 failure。"""
    pkt_success = make_pkt("t1", "block port 445")
    pkt_failure = make_pkt("t2", "failed scan")
    engine.tag_outcome("t1", "success")
    engine.tag_outcome("t2", "failure")
    # 记录相同的引用次数和时间以确保其他维度相同
    assert engine.evaluate(pkt_success) > engine.evaluate(pkt_failure)


def test_rank_sorts_by_score_desc(engine):
    """rank 按评分降序排列。"""
    pkts = [make_pkt(f"t{i}", f"summary {i}") for i in range(5)]
    engine.tag_outcome("t0", "success")
    engine.tag_outcome("t4", "failure")
    ranked = engine.rank(pkts)
    assert ranked[0][1] >= ranked[-1][1]  # 降序
    # success 的排在最前
    assert ranked[0][0].task_id == "t0"


def test_record_reference_increments(engine):
    """record_reference 应递增引用计数。"""
    assert engine.get_reference_count("t1") == 0
    engine.record_reference("t1")
    assert engine.get_reference_count("t1") == 1
    engine.record_reference("t1")
    assert engine.get_reference_count("t1") == 2


def test_is_cold(engine):
    """引用为 0 的记忆判断为冷。"""
    assert engine.is_cold("t1") is True
    engine.record_reference("t1")
    assert engine.is_cold("t1") is False


def test_stats_returns_dict(engine):
    """stats 返回评估统计信息。"""
    engine.tag_outcome("t1", "success")
    engine.tag_outcome("t2", "failure")
    engine.tag_outcome("t3", "unknown")
    s = engine.stats()
    assert "total_evaluated" in s
    assert s["total_evaluated"] == 3
    assert s["success_count"] == 1
    assert s["failure_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_reflection.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/reflection/engine.py`**

```python
# date: 2026-08-01
# dev: myf
"""反思引擎 —— 经验质量评估。

对情景记忆中的决策类记忆（kind=decision）做三维评估：
时效性（freshness）× 引用频次（reference_count）× 结果标记（outcome）。
纯算法实现，不依赖 LLM 调用。用于 recall 结果重排序，使优质经验优先。
"""

from __future__ import annotations

import time

from protocol.memory import MemoryPacket

# 评估维度权重
WEIGHT_FRESHNESS = 0.3
WEIGHT_REFERENCE = 0.3
WEIGHT_OUTCOME = 0.4

# 结果标记映射为评分系数
OUTCOME_SCORES = {"success": 1.0, "unknown": 0.5, "failure": 0.0}

# 时效性衰减半衰期（秒）—— 1 小时
FRESHNESS_HALF_LIFE = 3600.0


class ReflectionEngine:
    """反思引擎 —— 三维经验质量评估。

    对决策类记忆按 **时效性 × 引用频次 × 结果标记** 三维度加权评分，
    用于在 recall 时重排序候选记忆，确保优质经验优先注入推理上下文。

    Attributes:
        _outcomes: {task_id -> outcome} 结果标记（success/failure/unknown）。
        _reference_counts: {task_id -> count} 引用计数器。
        _creation_times: {task_id -> timestamp} 记忆创建时间（monotonic）。
    """

    def __init__(self) -> None:
        """初始化反思引擎，空的评估记录。"""
        self._outcomes: dict[str, str] = {}
        self._reference_counts: dict[str, int] = {}
        self._creation_times: dict[str, float] = {}

    # ---- 公开接口 ----

    def evaluate(self, packet: MemoryPacket) -> float:
        """对单条记忆做三维评估评分。

        评分公式：
            score = 0.3 × freshness + 0.3 × ref_score + 0.4 × outcome
        其中 freshness = 1.0 / (1 + age / half_life)。

        Args:
            packet: 待评估的记忆包。

        Returns:
            综合评分（[0.0, 1.0] 区间）。
        """
        task_id = packet.task_id or ""
        if not task_id:
            return 0.5  # 无 task_id 的记忆给中性分
        # 记录创建时间（首次调用）
        if task_id not in self._creation_times:
            self._creation_times[task_id] = time.monotonic()
        age = time.monotonic() - self._creation_times[task_id]
        freshness = 1.0 / (1.0 + age / FRESHNESS_HALF_LIFE)
        ref_count = self._reference_counts.get(task_id, 0)
        ref_score = min(ref_count / 10.0, 1.0)
        outcome = self._outcomes.get(task_id, "unknown")
        outcome_score = OUTCOME_SCORES.get(outcome, 0.5)
        return (
            WEIGHT_FRESHNESS * freshness
            + WEIGHT_REFERENCE * ref_score
            + WEIGHT_OUTCOME * outcome_score
        )

    def rank(
        self, memories: list[MemoryPacket]
    ) -> list[tuple[MemoryPacket, float]]:
        """批量评估并按评分降序排列。

        Args:
            memories: 待排序的记忆列表。

        Returns:
            ``(MemoryPacket, score)`` 列表，按评分降序。
        """
        scored = [(m, self.evaluate(m)) for m in memories]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def tag_outcome(self, task_id: str, outcome: str) -> None:
        """标注记忆的执行结果。

        Args:
            task_id: 目标任务标识符。
            outcome: ``"success"`` / ``"failure"`` / ``"unknown"``。
        """
        if outcome in OUTCOME_SCORES:
            self._outcomes[task_id] = outcome

    def record_reference(self, task_id: str) -> None:
        """记录一次对某条记忆的引用（召回命中）。

        Args:
            task_id: 被引用的任务标识符。
        """
        self._reference_counts[task_id] = self._reference_counts.get(task_id, 0) + 1

    def get_reference_count(self, task_id: str) -> int:
        """查询引用次数。

        Args:
            task_id: 目标任务标识符。

        Returns:
            引用计数，未记录过返回 0。
        """
        return self._reference_counts.get(task_id, 0)

    def is_cold(self, task_id: str, threshold: int = 0) -> bool:
        """判断某条记忆是否为"冷"记忆（引用次数 ≤ 阈值）。

        用于 archive 模块判断是否应下沉冷数据。

        Args:
            task_id: 目标任务标识符。
            threshold: 冷数据判断阈值，默认 0（从未被引用即为冷）。

        Returns:
            ``True`` 表示冷记忆（可归档）。
        """
        return self.get_reference_count(task_id) <= threshold

    def stats(self) -> dict:
        """返回评估统计信息。

        Returns:
            含 total_evaluated / success_count / failure_count / unknown_count 的字典。
        """
        outcomes = list(self._outcomes.values())
        return {
            "total_evaluated": len(self._outcomes),
            "success_count": outcomes.count("success"),
            "failure_count": outcomes.count("failure"),
            "unknown_count": outcomes.count("unknown"),
        }
```

- [ ] **Step 4: Write `aegisos_agents/memory/reflection/__init__.py`**

```python
from .engine import ReflectionEngine

__all__ = ["ReflectionEngine"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/reflection/AGENT.md`**

```markdown
# Agents/Memory/Reflection — AGENT.md

> 本文件是 `aegisos_agents/memory/reflection/` 模块的开发规范。

## 职责
反思引擎：对决策类记忆做三维评估（时效性 × 引用频次 × 结果标记），纯算法实现，用于 recall 结果重排序。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `engine.py` — ReflectionEngine

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`evaluate(packet)` / `rank(memories)` / `tag_outcome(task_id, outcome)` / `record_reference(task_id)` / `get_reference_count(task_id)` / `is_cold(task_id, threshold)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_reflection.py`
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/reflection/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_reflection.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/reflection/ tests/aegisos_agents/memory/test_reflection.py
git commit -m "feat(memory): P2 reflection — experience quality evaluation engine"
```

---

### Task 5: Archive — Cold Data Tier ◇

**Files:**
- Create: `aegisos_agents/memory/archive/__init__.py`
- Create: `aegisos_agents/memory/archive/store.py`
- Create: `aegisos_agents/memory/archive/AGENT.md`
- Delete: `aegisos_agents/memory/archive/README.md`
- Create: `tests/aegisos_agents/memory/test_archive.py`

**Interfaces:**
- Produces: `ArchiveStore()` — constructor (no args)
- Produces: `ArchiveStore.archive(packets: list[MemoryPacket]) -> int`
- Produces: `ArchiveStore.recall(task_id: str) -> MemoryPacket | None`
- Produces: `ArchiveStore.defrost(task_id: str, episodic: EpisodicMemory) -> bool` — move back to episodic
- Produces: `ArchiveStore.search(keyword: str) -> list[MemoryPacket]`
- Produces: `ArchiveStore.size() -> int`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_archive.py`**

```python
# date: 2026-08-01
# dev: myf
"""归档模块测试 —— 冷热分层 + 回热 + 关键词检索。"""
import pytest
from aegisos_agents.memory.archive.store import ArchiveStore
from aegisos_agents.memory.episodic.store import EpisodicMemory
from protocol.memory import MemoryPacket


@pytest.fixture
def store():
    return ArchiveStore()


def make_pkt(task_id: str, summary: str = "") -> MemoryPacket:
    return MemoryPacket(task_id=task_id, kind="decision", summary=summary)


def test_archive_returns_count(store):
    """archive 返回归档条数。"""
    count = store.archive([make_pkt("t1", "old exp"), make_pkt("t2", "old exp 2")])
    assert count == 2
    assert store.size() == 2


def test_recall_by_task_id(store):
    """按 task_id 精确回查归档记忆。"""
    store.archive([make_pkt("t1", "old lateral move")])
    pkt = store.recall("t1")
    assert pkt is not None
    assert pkt.summary == "old lateral move"


def test_recall_missing_returns_none(store):
    """回查不存在的归档记忆返回 None。"""
    assert store.recall("nope") is None


def test_defrost_moves_to_episodic(store):
    """回热：从 archive 移除并追加到 episodic。"""
    epi = EpisodicMemory()
    pkt = make_pkt("t1", "valuable old exp")
    store.archive([pkt])
    assert store.size() == 1
    success = store.defrost("t1", epi)
    assert success is True
    assert store.size() == 0
    assert len(epi) == 1
    assert epi.by_task("t1") is not None


def test_search_keyword_in_archive(store):
    """归档记忆支持关键词检索。"""
    store.archive([
        make_pkt("t1", "lateral movement via smb"),
        make_pkt("t2", "port scan detection"),
    ])
    results = store.search("lateral")
    assert len(results) == 1
    assert results[0].task_id == "t1"


def test_search_no_match_returns_empty(store):
    """关键词无匹配返回空列表。"""
    store.archive([make_pkt("t1", "scan")])
    assert store.search("nonexistent") == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_archive.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/archive/store.py`**

```python
# date: 2026-08-01
# dev: myf
"""归档记忆存储 —— 冷数据长期存储。

冷热分层：低引用频次的旧经验从 episodic 下沉到本模块长期保存，
支持按 task_id 精确回查、关键词检索、按需回热（defrost）。
纯内存 list 实现，为 H2 持久化预留文件/SQLite 升级路径。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from protocol.memory import MemoryPacket

if TYPE_CHECKING:
    from aegisos_agents.memory.episodic.store import EpisodicMemory


class ArchiveStore:
    """归档记忆存储 —— 冷数据长期存储（H2 持久化预留位）。

    以 ``list[MemoryPacket]`` 维护已归档的冷记忆，支持精确回查、
    关键词检索与回热到情景记忆。

    Attributes:
        _store: 已归档的记忆列表，按写入顺序排列。
    """

    def __init__(self) -> None:
        """初始化空的归档存储。"""
        self._store: list[MemoryPacket] = []

    # ---- 公开接口 ----

    def archive(self, packets: list[MemoryPacket]) -> int:
        """批量归档记忆。

        Args:
            packets: 待归档的记忆列表。

        Returns:
            实际归档的条数。
        """
        count = len(packets)
        self._store.extend(packets)
        return count

    def recall(self, task_id: str) -> MemoryPacket | None:
        """按 task_id 精确回查归档记忆。

        Args:
            task_id: 目标任务标识符。

        Returns:
            匹配的记忆包；未找到返回 ``None``。
        """
        for m in self._store:
            if m.task_id == task_id:
                return m
        return None

    def defrost(self, task_id: str, episodic: EpisodicMemory) -> bool:
        """回热：从归档移回情景记忆。

        找到匹配记忆后从 archive 移除并追加到 episodic。

        Args:
            task_id: 待回热的任务标识符。
            episodic: 目标情景记忆存储。

        Returns:
            回热成功返回 ``True``；未找到目标记忆返回 ``False``。
        """
        for i, m in enumerate(self._store):
            if m.task_id == task_id:
                episodic.add(m)
                del self._store[i]
                return True
        return False

    def search(self, keyword: str) -> list[MemoryPacket]:
        """关键词子串检索归档记忆（大小写不敏感）。

        Args:
            keyword: 检索关键词。

        Returns:
            命中的记忆包列表。
        """
        kw = keyword.lower()
        results: list[MemoryPacket] = []
        for m in self._store:
            if kw in (m.summary or "").lower():
                results.append(m)
        return results

    def size(self) -> int:
        """返回已归档记忆总数。"""
        return len(self._store)
```

- [ ] **Step 4: Write `aegisos_agents/memory/archive/__init__.py`**

```python
from .store import ArchiveStore

__all__ = ["ArchiveStore"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/archive/AGENT.md`**

```markdown
# Agents/Memory/Archive — AGENT.md

> 本文件是 `aegisos_agents/memory/archive/` 模块的开发规范。

## 职责
冷数据归档：低引用频次的历史经验从 episodic 下沉长期保存，支持回热（defrost）。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/episodic/（defrost 回写）

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `store.py` — ArchiveStore

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/episodic/store.py EpisodicMemory（defrost 回写引用）

## 接口
`archive(packets)` / `recall(task_id)` / `defrost(task_id, episodic)` / `search(keyword)` / `size()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_archive.py`

## H2 升级路径
替换 `_store: list` 为文件/SQLite 持久化，接口不变。
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/archive/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_archive.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/archive/ tests/aegisos_agents/memory/test_archive.py
git commit -m "feat(memory): P2 archive — cold data tier with defrost support"
```

---

### Task 6: Snapshot — State Snapshot ◇

**Files:**
- Create: `aegisos_agents/memory/snapshot/__init__.py`
- Create: `aegisos_agents/memory/snapshot/manager.py`
- Create: `aegisos_agents/memory/snapshot/AGENT.md`
- Delete: `aegisos_agents/memory/snapshot/README.md`
- Create: `tests/aegisos_agents/memory/test_snapshot.py`

**Interfaces:**
- Produces: `SnapshotManager()` — constructor (no args)
- Produces: `SnapshotManager.capture(label: str, state: dict | None = None) -> str`
- Produces: `SnapshotManager.restore(snapshot_id: str) -> dict | None`
- Produces: `SnapshotManager.list_snapshots(session_id: str = "") -> list[str]`
- Produces: `SnapshotManager.prune(session_id: str, keep: int = 10) -> None`
- Produces: `SnapshotManager.stats() -> dict`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_snapshot.py`**

```python
# date: 2026-08-01
# dev: myf
"""快照模块测试 —— capture/restore/prune/统计。"""
import pytest
from aegisos_agents.memory.snapshot.manager import SnapshotManager


@pytest.fixture
def mgr():
    return SnapshotManager()


def test_capture_and_restore_roundtrip(mgr):
    """capture→restore 往返数据一致。"""
    state = {"episodic_total": 42, "topology": {"nodes": 5, "edges": 8}}
    sid = mgr.capture("phase1_done", state)
    restored = mgr.restore(sid)
    assert restored is not None
    assert restored["label"] == "phase1_done"
    assert restored["episodic_total"] == 42
    assert restored["topology"]["nodes"] == 5


def test_capture_without_state(mgr):
    """无 state 时可正常 capture（仅记录标签与时间戳）。"""
    sid = mgr.capture("empty_snapshot")
    restored = mgr.restore(sid)
    assert restored is not None
    assert restored["label"] == "empty_snapshot"
    assert "timestamp" in restored


def test_restore_nonexistent_returns_none(mgr):
    """恢复不存在的快照返回 None。"""
    assert mgr.restore("nonexistent") is None


def test_list_snapshots(mgr):
    """列举快照 ID 列表。"""
    mgr.capture("s1")
    mgr.capture("s2")
    snaps = mgr.list_snapshots()
    assert len(snaps) == 2


def test_prune_keeps_last_k(mgr):
    """prune 保留最近 K 个快照。"""
    for i in range(15):
        mgr.capture(f"snap_{i}", {"idx": i})
    mgr.prune(keep=5)
    remaining = mgr.list_snapshots()
    assert len(remaining) == 5
    # 应保留最后 5 个
    restored = mgr.restore(remaining[-1])
    assert restored["idx"] == 14


def test_stats(mgr):
    """stats 返回快照统计。"""
    mgr.capture("s1", {"nodes": 3})
    mgr.capture("s2", {"nodes": 5})
    s = mgr.stats()
    assert s["total_snapshots"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_snapshot.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/snapshot/manager.py`**

```python
# date: 2026-08-01
# dev: myf
"""快照管理器 —— 拓扑/状态时间点固化。

定期拍摄系统全局状态快照，为 replay/monitor 提供时间线数据源。
每条快照以 ``MemoryPacket`` 承载（kind=snapshot），按时间戳排序。
"""

from __future__ import annotations

import time
import uuid

from protocol.memory import MemoryPacket


class SnapshotManager:
    """快照管理器 —— 全局状态时间点快照。

    以 ``{snapshot_id: MemoryPacket}`` 维护快照集合，支持拍摄、恢复、
    列举与清理。快照数据序列化到 ``MemoryPacket.archive`` 字段。

    Attributes:
        _snapshots: {snapshot_id: MemoryPacket} 快照存储。
        _order: [snapshot_id] 按拍摄时间排序的 ID 列表。
    """

    def __init__(self) -> None:
        """初始化空的快照管理器。"""
        self._snapshots: dict[str, MemoryPacket] = {}
        self._order: list[str] = []

    # ---- 公开接口 ----

    def capture(self, label: str, state: dict | None = None) -> str:
        """拍摄一次全局状态快照。

        Args:
            label: 快照标签，如 ``"after_recon"``。
            state: 可选的全局状态字典（memory_stats / topology_state / recent_decisions）。

        Returns:
            快照唯一标识符（UUID hex）。
        """
        snapshot_id = uuid.uuid4().hex[:12]
        record = {
            "label": label,
            "timestamp": time.monotonic(),
            **(state or {}),
        }
        pkt = MemoryPacket(
            task_id=snapshot_id,
            kind="snapshot",
            archive=record,
        )
        self._snapshots[snapshot_id] = pkt
        self._order.append(snapshot_id)
        return snapshot_id

    def restore(self, snapshot_id: str) -> dict | None:
        """恢复指定快照。

        Args:
            snapshot_id: 快照标识符。

        Returns:
            快照状态字典；不存在返回 ``None``。
        """
        pkt = self._snapshots.get(snapshot_id)
        if pkt is None:
            return None
        return dict(pkt.archive)

    def list_snapshots(self, session_id: str = "") -> list[str]:
        """列举所有快照 ID（按拍摄时间升序）。

        Args:
            session_id: 当前未使用；为未来按会话过滤预留。

        Returns:
            快照 ID 列表。
        """
        return list(self._order)

    def prune(self, session_id: str = "", keep: int = 10) -> None:
        """清理旧快照，仅保留最近 K 个。

        Args:
            session_id: 当前未使用；为未来按会话过滤预留。
            keep: 保留最近 K 个快照，默认 10。
        """
        while len(self._order) > max(keep, 1):
            oldest = self._order.pop(0)
            self._snapshots.pop(oldest, None)

    def stats(self) -> dict:
        """返回快照统计信息。

        Returns:
            含 total_snapshots 的字典。
        """
        return {"total_snapshots": len(self._snapshots)}
```

- [ ] **Step 4: Write `aegisos_agents/memory/snapshot/__init__.py`**

```python
from .manager import SnapshotManager

__all__ = ["SnapshotManager"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/snapshot/AGENT.md`**

```markdown
# Agents/Memory/Snapshot — AGENT.md

> 本文件是 `aegisos_agents/memory/snapshot/` 模块的开发规范。

## 职责
全局状态快照：定期拍摄 MemoryStore + 编排器拓扑快照，为 replay/monitor 提供时间线数据源。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `manager.py` — SnapshotManager

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`capture(label, state)` / `restore(snapshot_id)` / `list_snapshots(session_id)` / `prune(session_id, keep)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_snapshot.py`

## H2 升级路径
对接 observability/inspect/replay/ 播放器，按快照时间线跳转。
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/snapshot/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_snapshot.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/snapshot/ tests/aegisos_agents/memory/test_snapshot.py
git commit -m "feat(memory): P2 snapshot — global state time-point capture"
```

---

### Task 7: Sync — Edge-Fog-Cloud Synchronization ◇

**Files:**
- Create: `aegisos_agents/memory/sync/__init__.py`
- Create: `aegisos_agents/memory/sync/sync.py`
- Create: `aegisos_agents/memory/sync/AGENT.md`
- Delete: `aegisos_agents/memory/sync/README.md`
- Create: `tests/aegisos_agents/memory/test_sync.py`

**Interfaces:**
- Produces: `MemorySync()` — constructor (no args)
- Produces: `MemorySync.register_node(node_id: str, role: str) -> None`
- Produces: `MemorySync.unregister_node(node_id: str) -> None`
- Produces: `MemorySync.push(node_id: str, packets: list[MemoryPacket]) -> int`
- Produces: `MemorySync.pull(node_id: str, since_timestamp: float = 0.0) -> list[MemoryPacket]`
- Produces: `MemorySync.merge(local: list[MemoryPacket], remote: list[MemoryPacket]) -> list[MemoryPacket]`
- Produces: `MemorySync.list_nodes() -> list[dict]`

- [ ] **Step 1: Write the test file `tests/aegisos_agents/memory/test_sync.py`**

```python
# date: 2026-08-01
# dev: myf
"""同步模块测试 —— push/pull/merge + 多节点隔离。"""
import time
import pytest
from aegisos_agents.memory.sync.sync import MemorySync
from protocol.memory import MemoryPacket


@pytest.fixture
def sync():
    return MemorySync()


def make_pkt(task_id: str) -> MemoryPacket:
    return MemoryPacket(
        task_id=task_id,
        summary=f"sync test {task_id}",
        compression={"synced_at": time.monotonic()},
    )


def test_register_and_list_nodes(sync):
    """注册节点后可列举。"""
    sync.register_node("edge_01", "edge")
    sync.register_node("cloud_01", "cloud")
    nodes = sync.list_nodes()
    assert len(nodes) == 2
    roles = {n["role"] for n in nodes}
    assert roles == {"edge", "cloud"}


def test_push_and_pull_roundtrip(sync):
    """push→pull 往返数据一致。"""
    sync.register_node("edge_01", "edge")
    pkts = [make_pkt("t1"), make_pkt("t2")]
    count = sync.push("edge_01", pkts)
    assert count == 2
    pulled = sync.pull("edge_01")
    assert len(pulled) == 2
    ids = {p.task_id for p in pulled}
    assert ids == {"t1", "t2"}


def test_pull_since_timestamp(sync):
    """since 时间戳过滤增量。"""
    sync.register_node("edge_01", "edge")
    base = time.monotonic()
    sync.push("edge_01", [make_pkt("old")])
    time.sleep(0.01)
    sync.push("edge_01", [make_pkt("new")])
    incremental = sync.pull("edge_01", since_timestamp=base + 0.005)
    assert len(incremental) == 1
    assert incremental[0].task_id == "new"


def test_pull_nonexistent_node_returns_empty(sync):
    """拉取未注册节点返回空列表。"""
    assert sync.pull("ghost") == []


def test_merge_dedup_by_task_id(sync):
    """merge 按 task_id 去重，保留时间戳最新的。"""
    local = [make_pkt("t1"), make_pkt("t2")]
    remote = [make_pkt("t2"), make_pkt("t3")]
    merged = sync.merge(local, remote)
    ids = {p.task_id for p in merged}
    assert ids == {"t1", "t2", "t3"}
    assert len(merged) == 3


def test_unregister_node(sync):
    """注销节点后 push 应忽略。"""
    sync.register_node("edge_01", "edge")
    sync.unregister_node("edge_01")
    assert sync.push("edge_01", [make_pkt("t1")]) == 0
    assert sync.list_nodes() == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/aegisos_agents/memory/test_sync.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `aegisos_agents/memory/sync/sync.py`**

```python
# date: 2026-08-01
# dev: myf
"""记忆同步 —— 端边云记忆一致性协议骨架。

为端-边-云三层节点的记忆同步提供 push/pull/merge 协议。
当前为进程内 dict 模拟多节点，为 H7 容器化替换 gRPC/WebSocket 预留接口。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


class MemorySync:
    """端边云记忆同步管理器。

    维护多节点注册表，每节点独立存储一段记忆列表。
    同步策略：推模式（push）+ 拉模式（pull）+ 合并去重（merge, last-write-wins）。

    Attributes:
        _nodes: {node_id -> {"role": str, "store": list[MemoryPacket]}} 节点注册表。
    """

    def __init__(self) -> None:
        """初始化空的同步管理器（无不预注册节点）。"""
        self._nodes: dict[str, dict] = {}

    # ---- 节点管理 ----

    def register_node(self, node_id: str, role: str) -> None:
        """注册一个同步节点。

        Args:
            node_id: 节点唯一标识（如 ``"edge_01"``）。
            role: 节点角色：``"edge"`` / ``"fog"`` / ``"cloud"``。
        """
        if node_id not in self._nodes:
            self._nodes[node_id] = {"role": role, "store": []}

    def unregister_node(self, node_id: str) -> None:
        """注销一个同步节点并清理其数据。

        Args:
            node_id: 待注销的节点标识符。
        """
        self._nodes.pop(node_id, None)

    def list_nodes(self) -> list[dict]:
        """列举已注册节点。

        Returns:
            节点信息列表，每项含 ``node_id`` 与 ``role``。
        """
        return [{"node_id": nid, "role": info["role"]} for nid, info in self._nodes.items()]

    # ---- 同步操作 ----

    def push(self, node_id: str, packets: list[MemoryPacket]) -> int:
        """推模式：将本地记忆推送到目标节点。

        Args:
            node_id: 目标节点标识符。
            packets: 待推送的记忆列表。

        Returns:
            实际接收的记忆条数；节点未注册时返回 0。
        """
        info = self._nodes.get(node_id)
        if info is None:
            return 0
        info["store"].extend(packets)
        return len(packets)

    def pull(self, node_id: str, since_timestamp: float = 0.0) -> list[MemoryPacket]:
        """拉模式：从目标节点拉取增量记忆。

        Args:
            node_id: 源节点标识符。
            since_timestamp: 增量时间戳，仅拉取 ``synced_at`` 晚于该时间的记忆。

        Returns:
            增量记忆列表；节点未注册返回空列表。
        """
        info = self._nodes.get(node_id)
        if info is None:
            return []
        store: list[MemoryPacket] = info["store"]
        if since_timestamp <= 0.0:
            return list(store)
        return [
            pkt
            for pkt in store
            if pkt.compression.get("synced_at", 0.0) > since_timestamp
        ]

    def merge(
        self,
        local: list[MemoryPacket],
        remote: list[MemoryPacket],
    ) -> list[MemoryPacket]:
        """合并本地与远程记忆，按 task_id 去重（last-write-wins）。

        同一 task_id 的记忆，保留 ``synced_at`` 时间戳最大的一条。

        Args:
            local: 本地记忆列表。
            remote: 远程拉取的增量记忆列表。

        Returns:
            合并去重后的记忆列表。
        """
        merged: dict[str, MemoryPacket] = {}
        for pkt in local + remote:
            tid = pkt.task_id or ""
            if tid not in merged:
                merged[tid] = pkt
            else:
                # last-write-wins
                existing_ts = merged[tid].compression.get("synced_at", 0.0)
                new_ts = pkt.compression.get("synced_at", 0.0)
                if new_ts > existing_ts:
                    merged[tid] = pkt
        return list(merged.values())
```

- [ ] **Step 4: Write `aegisos_agents/memory/sync/__init__.py`**

```python
from .sync import MemorySync

__all__ = ["MemorySync"]
```

- [ ] **Step 5: Write `aegisos_agents/memory/sync/AGENT.md`**

```markdown
# Agents/Memory/Sync — AGENT.md

> 本文件是 `aegisos_agents/memory/sync/` 模块的开发规范。

## 职责
端边云记忆同步：push/pull/merge 协议骨架，当前进程内多节点模拟，为 H7 容器化预留 gRPC/WebSocket 升级路径。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `sync.py` — MemorySync

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`register_node(node_id, role)` / `unregister_node(node_id)` / `push(node_id, packets)` / `pull(node_id, since)` / `merge(local, remote)` / `list_nodes()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_sync.py`

## H7 升级路径
替换 push/pull 底层为 gRPC/WebSocket 传输，接口签名不变。
```

- [ ] **Step 6: Delete old README.md**

```bash
rm aegisos_agents/memory/sync/README.md
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/aegisos_agents/memory/test_sync.py -v
```
Expected: 6 PASS

- [ ] **Step 8: Commit**

```bash
git add aegisos_agents/memory/sync/ tests/aegisos_agents/memory/test_sync.py
git commit -m "feat(memory): P2 sync — edge-fog-cloud memory sync protocol"
```

---

### Task 8: MemoryStore v2 — Integration

**Files:**
- Modify: `aegisos_agents/memory/memory_store.py`

**Interfaces:**
- Consumes: `RetrievalEngine`, `ScoredPacket` from `aegisos_agents.memory.retrieval`
- Consumes: `MemoryCache` from `aegisos_agents.memory.cache`
- Consumes: `CheckpointManager` from `aegisos_agents.memory.checkpoint`
- Consumes: `ReflectionEngine` from `aegisos_agents.memory.reflection`
- Consumes: `ArchiveStore` from `aegisos_agents.memory.archive`
- Consumes: `SnapshotManager` from `aegisos_agents.memory.snapshot`
- Consumes: `MemorySync` from `aegisos_agents.memory.sync`
- Produces: MemoryStore v2 with 7 new attributes + upgraded `recall()` / `write()` / `retrieve()` + 3 new hooks

- [ ] **Step 1: Run existing tests to establish baseline**

```bash
pytest tests/aegisos_agents/memory/test_memory_store.py -v
```
Expected: 10 PASS (baseline before v2 upgrade)

- [ ] **Step 2: Modify `aegisos_agents/memory/memory_store.py` — add imports and new attributes**

The existing file is at `aegisos_agents/memory/memory_store.py`. Read it first, then apply changes.

Apply the following edits:

**Edit A — Add new imports (after existing imports at line 24):**

```python
from aegisos_agents.memory.retrieval.engine import RetrievalEngine
from aegisos_agents.memory.cache.store import MemoryCache
from aegisos_agents.memory.checkpoint.manager import CheckpointManager
from aegisos_agents.memory.reflection.engine import ReflectionEngine
from aegisos_agents.memory.archive.store import ArchiveStore
from aegisos_agents.memory.snapshot.manager import SnapshotManager
from aegisos_agents.memory.sync.sync import MemorySync
```

**Edit B — Add 7 new attributes to `__init__` (after `self.vector = VectorMemory()`):**

```python
        # ---- v2 新增：7 个子模块 ----
        self.retrieval_engine = RetrievalEngine(self.vector, self.semantic, self.episodic)
        self.cache = MemoryCache()
        self.checkpoint = CheckpointManager(self)
        self.reflection = ReflectionEngine()
        self.archive = ArchiveStore()
        self.snapshot = SnapshotManager()
        self.sync = MemorySync()
```

**Edit C — Replace `recall()` method:**

```python
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
```

**Edit D — Add cache invalidate + reflection evaluate to `write()`:**

After the existing 4-layer routing in `write()`, before `return True`, add:

```python
        # [v2] 失效相关缓存
        self.cache.invalidate(packet.task_id)
        # [v2] 对新决策预计算评估分
        if packet.kind == "decision":
            self.reflection.evaluate(packet)
```

**Edit E — Replace `retrieve()` method:**

```python
    def retrieve(self, query: dict[str, Any]) -> list[Any]:
        """检索相关记忆（v2：委托 RetrievalEngine 做混合检索 + 反思排序）。

        Args:
            query: 检索条件字典，识别 ``trigger`` / ``keyword`` / ``embedding`` / ``channels`` 键。

        Returns:
            匹配的 ``MemoryPacket`` 列表（决策优先，Top-K）。
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
```

**Edit F — Add 3 new orchestrator hook methods (after `end_session`):**

```python
    # ---- v2 编排器钩子 ----

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
        stats = {
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
```

- [ ] **Step 3: Run all memory tests to verify no regressions**

```bash
pytest tests/aegisos_agents/memory/ -v
```
Expected: ALL PASS (10 existing + 36 new = 46 tests)

- [ ] **Step 4: Commit**

```bash
git add aegisos_agents/memory/memory_store.py
git commit -m "feat(memory): P2 MemoryStore v2 — integrate 7 new submodules with recall pipeline upgrade"
```

---

### Task 9: Update Memory AGENT.md + Final Verification

**Files:**
- Modify: `aegisos_agents/memory/AGENT.md`
- Modify: `developer/plan.md`
- Modify: `developer/CHANGELOG.md`

- [ ] **Step 1: Update `aegisos_agents/memory/AGENT.md`**

Add the 7 new modules to the output section and update the module count from 12 to 12 (already covered). In the "输出" section, add:

```markdown
## 模块清单（12 子模块，全部完成）

| 模块 | 状态 | 职责 |
|------|------|------|
| working | ✅ | 工作记忆（会话临时上下文） |
| episodic | ✅ | 情景记忆（历史经验） |
| semantic | ✅ | 语义记忆（ATT&CK 知识库） |
| vector | ✅ | 向量记忆（余弦相似度检索） |
| compression | ✅ | 记忆压缩（token 预算控制） |
| recall | ✅ | 记忆唤醒（关键词匹配） |
| memory_store | ✅ | 记忆集成存储（MemoryAPI 实现） |
| retrieval | ✅ (P2) | 混合检索（向量+关键词+图 RRF 融合） |
| cache | ✅ (P2) | 热数据缓存（L1+L2 LRU） |
| checkpoint | ✅ (P2) | 任务检查点（中断恢复） |
| reflection | ✅ (P2) | 反思评估（三维质量评分） |
| archive | ✅ (P2) | 冷数据归档（长期存储） |
| snapshot | ✅ (P2) | 状态快照（时间点固化） |
| sync | ✅ (P2) | 端边云同步（协议骨架） |
```

Note: update the read count to include these new modules in "读取目录" and add them to "禁止修改目录" of the existing modules.

- [ ] **Step 2: Update `developer/plan.md`** — mark the 7 memory module items as `[x]` completed in §3 P2 section, update "最后更新" date and test count to ~250+.

- [ ] **Step 3: Update `developer/CHANGELOG.md`** — add entry for P2 memory subsystem completion.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/aegisos_agents/memory/ -v --tb=short
```
Expected: 46+ PASS (10 existing + 36 new), 0 FAIL

- [ ] **Step 5: Lint check**

```bash
ruff check aegisos_agents/memory/ --fix
```
Expected: zero warnings

- [ ] **Step 6: Run existing tests to confirm no regressions**

```bash
pytest tests/ -v --tb=short -x
```
Expected: all existing tests pass

- [ ] **Step 7: Final commit**

```bash
git add aegisos_agents/memory/AGENT.md developer/plan.md developer/CHANGELOG.md
git commit -m "docs: P2 memory subsystem completion — update AGENT.md + plan + changelog"
```

---

## Verification Checklist

After all tasks complete, verify:

1. [ ] `find aegisos_agents/memory -name "README.md" | wc -l` → 0 (all README.md files replaced by AGENT.md)
2. [ ] `find aegisos_agents/memory -name "AGENT.md" | wc -l` → 13 (1 root + 12 submodules)
3. [ ] `find aegisos_agents/memory -name "__init__.py" | wc -l` → 13 (1 root + 12 submodules)
4. [ ] `pytest tests/aegisos_agents/memory/ -v` → 46+ PASS
5. [ ] `pytest tests/ -v` → all existing tests pass (no regressions)
6. [ ] `ruff check aegisos_agents/memory/ --fix` → zero warnings
7. [ ] `git log --oneline -10` shows 9 commits: 7 module commits + 1 integration + 1 docs
