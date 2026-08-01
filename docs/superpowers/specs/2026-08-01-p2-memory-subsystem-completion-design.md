# P2 记忆子系统补全 — 设计文档

> 日期：2026-08-01 · 状态：设计完成，待评审 · 关联：`developer/plan.md` §3 P2

## 1. 目标与范围

### 1.1 目标

补全 `aegisos_agents/memory/` 下 7 个空模块，使记忆子系统具备完整的超长程经验沉淀能力。

### 1.2 范围分层

| 层级 | 模块 | 实现深度 | 理由 |
|------|------|---------|------|
| ★ 核心 | `retrieval` | 完整实现 | 直接影响记忆召回精度，是 recaller 的升级替代 |
| ★ 核心 | `checkpoint` | 完整实现 | 超长程任务中断恢复，赛题"超长程"核心卖点 |
| ★ 核心 | `reflection` | 完整实现 | 经验质量评估 → 群体智能进化，赛题"群体智能"维度 |
| ★ 核心 | `cache` | 完整实现 | 热数据加速，推理性能直接受益 |
| ◇ 骨架 | `archive` | 功能骨架 | 冷数据分层，真正威力依赖 H2 持久化 |
| ◇ 骨架 | `snapshot` | 功能骨架 | 全局状态快照，为 replay/monitor 提供数据源 |
| ◇ 骨架 | `sync` | 功能骨架 | 端边云同步协议，真正威力依赖 H7 容器化 |

### 1.3 不变约束

- `protocol/memory.py` MemoryPacket **零改动**（7 个模块复用现有字段）
- 现有 7 个已实现模块 **零改动**（仅新增，不改旧）
- `MemoryAPI`（read/write/retrieve）**签名不变**
- 所有模块纯内存实现，为 H2/H7 持久化预留升级路径
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 代码规范

---

## 2. 架构总览

### 2.1 MemoryStore v2 结构

```
MemoryStore (v2)
├── [已有] working/ episodic/ semantic/ vector/
├── [已有] compactor recaller
├── [新增★] retrieval  → RetrievalEngine  混合检索引擎
├── [新增★] cache      → MemoryCache      热数据加速
├── [新增★] checkpoint → CheckpointManager 任务中断恢复
├── [新增★] reflection → ReflectionEngine 经验质量评估
├── [新增◇] archive    → ArchiveStore     冷数据归档
├── [新增◇] snapshot   → SnapshotManager  拓扑快照
└── [新增◇] sync       → MemorySync       端边云同步
```

### 2.2 数据流

```
write(packet)
  ├─→ working.add(packet)
  ├─→ episodic.add(packet)     [kind=decision]
  ├─→ vector.add(packet)       [embedding 非空]
  ├─→ semantic.add(packet)     [concept_id 存在]
  ├─→ cache.invalidate(...)    [新增] 失效相关缓存
  └─→ reflection.evaluate(...) [新增] 预计算评分

recall(trigger)
  ├─→ L1 cache.get(trigger)?   [新增] 命中直接返回
  ├─→ retrieval.retrieve(trigger) [新增] 三通道 RRF
  └─→ reflection.rank(results) [新增] 优质经验优先

checkpoint_cycle(session_id, state)  [新增]
  └─→ checkpoint.save(session_id, state)  每 N 步自动

archive_cycle()  [新增]
  └─→ archive.archive(cold_packets)  compress 后触发

snapshot_cycle(session_id, state)  [新增]
  └─→ snapshot.capture(label, state)  阶段完成后触发
```

---

## 3. 模块详细设计

### 3.1 retrieval — 混合检索引擎 ★

**文件**：`aegisos_agents/memory/retrieval/`（`__init__.py` + `engine.py`）

**类**：`RetrievalEngine`

**三通道召回**：
| 通道 | 方法 | 输入 | 输出 | 权重 |
|------|------|------|------|------|
| 向量 | `_vector_channel(query_embedding)` | 查询向量 | Top-K 按余弦相似度 | 0.4 |
| 关键词 | `_keyword_channel(query_text)` | 查询文本 | 子串匹配（summary + working + episodic 字段） | 0.35 |
| 图关联 | `_graph_channel(query_text)` | 查询文本 | ATT&CK tactic/technique 关联遍历语义记忆 | 0.25 |

**RRF 融合**：
```
RRF_score(d, c) = Σ_c 1 / (k + rank_c(d))
```
其中 k=60，三通道独立排名后取 RRF 总分降序，去重后返回 Top-K。

**数据类型**：
```python
@dataclass
class ScoredPacket:
    packet: MemoryPacket
    score: float          # RRF 融合分
    channels: list[str]   # 命中通道列表，如 ["vector", "keyword"]
```

**接口**：
- `retrieve(query: str, query_embedding: list[float] | None = None, channels: list[str] | None = None, top_k: int = 10) -> list[ScoredPacket]`
- `add_to_index(packet: MemoryPacket)` — 新记忆加入各通道索引
- `rebuild_index()` — 全量重建索引（从 episodic + semantic + vector 拉数据）

**依赖**：`VectorMemory`（只读）· `SemanticMemory`（只读）· `EpisodicMemory`（只读）

---

### 3.2 cache — 热数据加速 ★

**文件**：`aegisos_agents/memory/cache/`（`__init__.py` + `store.py`）

**类**：`MemoryCache`

**两级缓存**：

| 级别 | 键 | 值 | 淘汰策略 | 容量 |
|------|-----|-----|---------|------|
| L1 查询缓存 | `hash(trigger)` | `list[MemoryPacket]` | TTL 60s 过期 | 无上限(带 TTL) |
| L2 热点缓存 | `task_id` | `MemoryPacket` | LRU | 100 条 |

**L2 晋升规则**：`touch(task_id)` 记录访问计数，≥3 次自动从 episodic 加载到 L2。

**接口**：
- `get_query(key: str) -> list[MemoryPacket] | None`
- `set_query(key: str, results: list[MemoryPacket], ttl: float = 60.0)`
- `get_hot(task_id: str) -> MemoryPacket | None`
- `touch(task_id: str)` — 记录访问
- `invalidate(task_id: str)` — 记忆更新时失效 L1 + L2
- `stats() -> dict` — 命中率/大小统计

**LRU 实现**：`collections.OrderedDict`，`move_to_end()` + `popitem(last=False)`。

---

### 3.3 checkpoint — 任务中断恢复 ★

**文件**：`aegisos_agents/memory/checkpoint/`（`__init__.py` + `manager.py`）

**类**：`CheckpointManager`

**检查点内容**（序列化为 dict 存入 `MemoryPacket.archive`）：
```python
{
    "session_id": str,
    "step_index": int,           # 当前步骤索引
    "completed_tasks": [str],    # 已完成 task_id 列表
    "working_summary": str,      # 工作记忆摘要
    "topology_snapshot": dict,   # 编排器拓扑状态（可选）
    "timestamp": float,          # time.monotonic()
    "label": str,                # 可选标签
}
```

**自动检查点**：编排器每步调用 `checkpoint_cycle(session_id, state)`，内部计数，每 N 步（默认 5）自动 `save()`。

**接口**：
- `save(session_id: str, state: dict, label: str = "") -> str` — 保存检查点，返回 checkpoint_id
- `restore(session_id: str) -> dict | None` — 恢复最新检查点
- `list_checkpoints(session_id: str) -> list[dict]` — 列举所有检查点
- `prune(session_id: str, keep_last: int = 5)` — 保留最近 K 个
- `maybe_save(session_id: str, state: dict, interval: int = 5) -> str | None` — 内部计步，每 N 步触发 save；未达阈值返回 None

**内部状态**：`_step_counter: dict[str, int]` 按 session 计步

**存储**：`{session_id: deque[MemoryPacket]}`（`kind="checkpoint"`，`archive` 字段承载状态 dict）

**对接 MemoryStore**：`save()` 同时调用 `MemoryStore.write()` 写入情景记忆（确保持久性语义）。

---

### 3.4 reflection — 反思记忆评估 ★

**文件**：`aegisos_agents/memory/reflection/`（`__init__.py` + `engine.py`）

**类**：`ReflectionEngine`

**评估维度**（纯算法，不调 LLM）：

| 维度 | 字段 | 计算方式 | 权重 |
|------|------|---------|------|
| 时效性 | `freshness` | `1.0 / (1 + age_in_seconds/3600)` | 0.3 |
| 引用频次 | `reference_count` | `min(ref_count / 10, 1.0)` | 0.3 |
| 结果标记 | `outcome_score` | success=1.0, unknown=0.5, failure=0.0 | 0.4 |

**总分**：`score = 0.3*freshness + 0.3*ref_score + 0.4*outcome`

**接口**：
- `evaluate(packet: MemoryPacket) -> float`
- `rank(memories: list[MemoryPacket]) -> list[tuple[MemoryPacket, float]]` — 批量评分排序
- `tag_outcome(task_id: str, outcome: str)` — 标注结果（success/failure/unknown）
- `record_reference(task_id: str)` — 记录一次引用
- `get_reference_count(task_id: str) -> int` — 查询引用次数
- `is_cold(task_id: str, threshold: int = 0) -> bool` — 判断是否为冷记忆（引用 ≤ threshold）
- `stats() -> dict` — 评估统计

**存储**：`{task_id: {"outcome": str, "reference_count": int, "score": float}}`

---

### 3.5 archive — 冷数据归档 ◇

**文件**：`aegisos_agents/memory/archive/`（`__init__.py` + `store.py`）

**类**：`ArchiveStore`

**归档策略**：
1. 触发时机：`MemoryStore.archive_cycle()` 在 compress 后调用
2. 筛选条件：episodic 中 `reference_count == 0` 且不在最近 100 条内的记忆
3. 操作：从 episodic 移除，追加到 archive 内部 list

**回热机制**：当 retrieval 的关键词/向量通道命中 archive 中的记忆时，调用 `defrost(task_id)` 将其移回 episodic。

**接口**：
- `archive(packets: list[MemoryPacket]) -> int` — 批量归档，返回归档数量
- `recall(task_id: str) -> MemoryPacket | None` — 精确回查
- `defrost(task_id: str) -> bool` — 回热到 episodic（需传入 episodic 引用）
- `search(keyword: str) -> list[MemoryPacket]` — 冷数据关键词检索
- `size() -> int`

**H2 升级路径**：替换 `_store: list` 为文件/SQLite backend，接口不变。

---

### 3.6 snapshot — 拓扑快照 ◇

**文件**：`aegisos_agents/memory/snapshot/`（`__init__.py` + `manager.py`）

**类**：`SnapshotManager`

**快照内容**（序列化到 `MemoryPacket.archive`）：
```python
{
    "label": str,
    "timestamp": float,
    "memory_stats": {
        "working_sessions": int,
        "episodic_total": int,
        "semantic_total": int,
        "vector_total": int,
        "archive_total": int,
    },
    "topology_state": dict | None,   # 编排器拓扑 snapshot
    "recent_decisions": [str],       # 最近决策 summary 列表（最近 5 条）
}
```

**接口**：
- `capture(label: str, state: dict | None = None) -> str` — 拍摄快照，返回 snapshot_id
- `restore(snapshot_id: str) -> dict | None` — 恢复快照
- `list_snapshots(session_id: str = "") -> list[str]` — 列举快照 ID
- `prune(session_id: str, keep: int = 10)` — 保留最近 K 个
- `stats() -> dict` — 快照统计

**存储**：`{snapshot_id: MemoryPacket}`（`kind="snapshot"`）

**对接 replay**：`observability/inspect/replay/player.py` 可读取快照列表做时间线跳转（后续集成）。

---

### 3.7 sync — 端边云同步骨架 ◇

**文件**：`aegisos_agents/memory/sync/`（`__init__.py` + `sync.py`）

**类**：`MemorySync`

**同步策略**：

| 模式 | 方法 | 触发方 | 描述 |
|------|------|--------|------|
| 推 | `push(node_id, packets)` | 源节点 | 本地新增记忆推送到目标节点 |
| 拉 | `pull(node_id, since)` | 目标节点 | 从源节点拉取增量记忆 |
| 合并 | `merge(local, remote)` | 接收方 | task_id 去重 + last-write-wins |

**节点角色**：`edge` / `fog` / `cloud`（注册时声明）

**冲突解决**：`last-write-wins`，基于 `MemoryPacket.compression` 中的 `synced_at` 时间戳字段。

**接口**：
- `register_node(node_id: str, role: str)` — 注册同步节点
- `unregister_node(node_id: str)`
- `push(node_id: str, packets: list[MemoryPacket]) -> int` — 推送，返回接收数量
- `pull(node_id: str, since_timestamp: float = 0.0) -> list[MemoryPacket]` — 拉取增量
- `merge(local: list[MemoryPacket], remote: list[MemoryPacket]) -> list[MemoryPacket]` — 合并去重
- `list_nodes() -> list[dict]` — 列举注册节点

**当前实现**：进程内 `{node_id: list[MemoryPacket]}` 模拟多节点存储。

**H7 升级路径**：替换 push/pull 底层为 gRPC/WebSocket 传输，接口不变。

---

## 4. MemoryStore 改造清单

### 4.1 `__init__` 新增属性

```python
self.retrieval_engine = RetrievalEngine(self.vector, self.semantic, self.episodic)
self.cache = MemoryCache()
self.checkpoint = CheckpointManager(self)
self.reflection = ReflectionEngine()
self.archive = ArchiveStore()
self.snapshot = SnapshotManager()
self.sync = MemorySync()
```

### 4.2 `recall()` 升级

```python
def recall(self, trigger: str) -> list[MemoryPacket]:
    # 1) L1 缓存
    cached = self.cache.get_query(trigger)
    if cached is not None:
        return cached
    # 2) 混合检索
    scored = self.retrieval_engine.retrieve(trigger, top_k=20)
    # 3) 反思重排序
    ranked = self.reflection.rank([s.packet for s in scored])
    results = [p for p, _ in ranked[:5]]
    # 4) 写入 L1 缓存
    self.cache.set_query(trigger, results)
    return results
```

### 4.3 `write()` 增加副作用

```python
def write(self, packet: MemoryPacket) -> bool:
    # ... 原有 4 层路由不变 ...
    # [新增] 失效缓存
    self.cache.invalidate(packet.task_id)
    # [新增] 评估新决策
    if packet.kind == "decision":
        self.reflection.evaluate(packet)
    return True
```

### 4.4 新增编排器钩子

```python
def checkpoint_cycle(self, session_id: str, state: dict) -> str | None:
    """每步调用，内部计步，每 N 步自动保存。"""
    return self.checkpoint.maybe_save(session_id, state)

def archive_cycle(self) -> int:
    """compress 后触发冷数据下沉。"""
    cold = [m for m in self.episodic.all()
            if self.reflection.is_cold(m.task_id)]
    if len(cold) <= 100:
        return 0
    to_archive = cold[:-100]  # 保留最近 100 条
    return self.archive.archive(to_archive)

def snapshot_cycle(self, session_id: str, state: dict | None = None) -> str:
    """阶段完成后触发快照。"""
    return self.snapshot.capture(
        label=f"checkpoint_{session_id}",
        state=state,
    )
```

### 4.5 新增 `retrieve()` 升级

```python
def retrieve(self, query: dict[str, Any]) -> list[Any]:
    trigger = query.get("trigger") or query.get("keyword") or ""
    embedding = query.get("embedding")  # [新增] 支持向量查询
    channels = query.get("channels")    # [新增] 通道选择
    scored = self.retrieval_engine.retrieve(
        trigger, query_embedding=embedding, channels=channels, top_k=10
    )
    return [s.packet for s in scored]
```

---

## 5. 测试计划

### 5.1 测试文件清单

| 文件 | 模块 | 最小测试数 |
|------|------|-----------|
| `tests/aegisos_agents/memory/test_retrieval.py` | retrieval | 6 |
| `tests/aegisos_agents/memory/test_cache.py` | cache | 5 |
| `tests/aegisos_agents/memory/test_checkpoint.py` | checkpoint | 5 |
| `tests/aegisos_agents/memory/test_reflection.py` | reflection | 5 |
| `tests/aegisos_agents/memory/test_archive.py` | archive | 4 |
| `tests/aegisos_agents/memory/test_snapshot.py` | snapshot | 4 |
| `tests/aegisos_agents/memory/test_sync.py` | sync | 4 |
| `tests/aegisos_agents/memory/test_memory_store.py` | MemoryStore v2 集成 | 6 (追加) |

**总计**：~39 新测试 + 10 已有 = ~49 测试

### 5.2 关键测试场景

- retrieval：三通道各自召回 + RRF 融合 + 空查询/空索引边界
- cache：L1 TTL 过期 + L2 LRU 淘汰 + invalidate 级联
- checkpoint：save→restore 往返 + 每 N 步自动 + prune 截断
- reflection：评分排序 + outcome 标记 + reference_count 累计
- archive：冷热分层 + defrost 回热 + 与 episodic 一致性
- snapshot：capture→restore 往返 + prune + 空状态
- sync：push→pull 往返 + merge 去重 + 多节点隔离
- MemoryStore v2：recall 缓存命中 + checkpoint_cycle + archive_cycle + snapshot_cycle 端到端

---

## 6. 文件清单

### 6.1 新增文件（21 个）

```
aegisos_agents/memory/
├── retrieval/
│   ├── __init__.py
│   ├── engine.py              # RetrievalEngine + ScoredPacket
│   └── AGENT.md
├── cache/
│   ├── __init__.py
│   ├── store.py               # MemoryCache
│   └── AGENT.md
├── checkpoint/
│   ├── __init__.py
│   ├── manager.py             # CheckpointManager
│   └── AGENT.md
├── reflection/
│   ├── __init__.py
│   ├── engine.py              # ReflectionEngine
│   └── AGENT.md
├── archive/
│   ├── __init__.py
│   ├── store.py               # ArchiveStore
│   └── AGENT.md
├── snapshot/
│   ├── __init__.py
│   ├── manager.py             # SnapshotManager
│   └── AGENT.md
└── sync/
    ├── __init__.py
    ├── sync.py                # MemorySync
    └── AGENT.md
```

### 6.2 修改文件（2 个）

- `aegisos_agents/memory/memory_store.py` — 集成 7 个新模块，升级 recall/write/retrieve + 3 个钩子
- `aegisos_agents/memory/AGENT.md` — 更新模块文档

### 6.3 新增测试文件（7 个）

```
tests/aegisos_agents/memory/
├── test_retrieval.py
├── test_cache.py
├── test_checkpoint.py
├── test_reflection.py
├── test_archive.py
├── test_snapshot.py
└── test_sync.py
```

---

## 7. 风险与约束

| 风险 | 缓解 |
|------|------|
| RRF 融合参数（k=60）未经实际数据调优 | 预设常用值，接口保留 k 参数可调 |
| 检查点的编排器状态字典结构未定义 | 首版存 `dict`，不做 schema 校验 |
| archive/reflection 冷热判断依赖 reference_count，初始全为 0 | 新记忆有 freshness 兜底分，不会立即归档 |
| sync 进程内模拟与真实分布式差距大 | 明确标注 H7 升级路径，接口稳定 |

---

## 8. 验收标准

1. 7 个模块的 `__init__.py` + 核心类文件 + `AGENT.md` 全部创建
2. `MemoryStore` 集成 7 个模块，`recall()`/`write()`/`retrieve()` 升级为 v2
3. 33+ 新测试全部通过
4. 10 已有测试无回归
5. `ruff format && ruff check --fix` 零告警
6. `aegisos_agents/memory/AGENT.md` 更新
7. `developer/CHANGELOG.md` 记录变更
