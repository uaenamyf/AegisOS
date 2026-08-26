# H2 数据层接入 — 设计文档（Neo4j + Qdrant + 记忆子系统对接）

> 日期：2026-08-06 · 作者：dev czy
> 状态：已实施（R1-R3 完成）· 关联计划：`developer/plan.md` §3 H2 数据层接入（H2.1–H2.4）
> 规范依据：`00_PROJECT_SPEC` · `03_IMPORT_SPEC` · `05_API_SPEC` · `06_SCHEMA_SPEC` · `11_AI_CODING_SPEC` · `12_TECH_STACK_SPEC`

---

## 1. 背景与目标

AegisOS 记忆子系统当前 `vector` 为纯内存余弦实现（标注「Qdrant 预留位」）、`semantic` 为内存 dict + 8 条 ATT&CK 种子（标注「Neo4j 预留位」）；`data/models/` 为空目录（仅 api Protocol）。

H2 目标：**接入 Neo4j 拓扑图 + ATT&CK 图、Qdrant 向量库，并对接记忆子系统**，使数据层成为真正的存储后端。

| 子任务 | 内容 | 落点 |
|--------|------|------|
| H2.1 | Neo4j 拓扑图 + ATT&CK 图接入 | `data/models/` |
| H2.2 | Qdrant 向量库接入 | `data/models/` |
| H2.3 | `memory/vector/` 对接 Qdrant | `aegisos_agents/memory/vector/` |
| H2.4 | `memory/semantic/` 对接 Neo4j ATT&CK 图 | `aegisos_agents/memory/semantic/` |

## 2. 关键决策（已与用户确认）

1. **双实现适配层**：`data/models/` 定义抽象接口 + 内存参考实现（零依赖、开箱可用）+ 真实 Neo4j/Qdrant 适配器（配置启用、依赖惰性加载）。默认 in_memory，无基础设施也能跑通测试与演示。
2. **ATT&CK 数据集扩充到 ~35 条**：覆盖 3 个场景（侦察/横向移动/检测响应），含 tactic→technique、technique→technique 关系边。

## 3. 架构

```
data/ 数据层（H2 主体）                          aegisos_agents/memory（H2.3/H2.4）
├── api/__init__.py   新增 GraphStoreAPI + VectorStoreAPI
│                     + 工厂 create_graph_store() / create_vector_store()
├── models/           内部实现（域内包）
│   ├── graph_store.py    InMemoryGraphStore(默认) / Neo4jGraphStore(真实·懒加载)
│   ├── vector_store.py   InMemoryVectorStore(默认) / QdrantVectorStore(真实·懒加载)
│   └── registry.py       按 mode 分发工厂
└── datasets/attck/knowledge.py  扩充版 ATT&CK 数据集（~35 技战术 + 关系边）
```

### 3.1 依赖方向合规（03_IMPORT_SPEC）

- 消费方只 `from data.api import ...`：`aegisos_agents → data.api` ✅、`backend → data.api` ✅。
- `data/api` 内部 import `data/models`（域内 import，合法）。
- `data/models` 只依赖 `protocol/`（`cyber.Asset`、`memory.MemoryPacket`、`graph.Graph`）——数据层零反向依赖。
- `neo4j` / `qdrant-client` **仅**在 `Neo4jGraphStore` / `QdrantVectorStore` 方法内部惰性 import；未安装时抛明确错误。默认 in_memory 模式完全不触碰三方包。

## 4. 新增接口（`data/api/__init__.py`，增量非破坏）

### 4.1 `VectorStoreAPI`（Protocol）

```python
class VectorStoreAPI(Protocol):
    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None: ...
    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]: ...
    def delete(self, vector_id: str) -> None: ...
    def count(self) -> int: ...
    def all(self) -> list[tuple[str, dict]]: ...
```

- `search` 返回 `(vector_id, payload, score)` 按相似度降序；空查询返回 `[]`。
- payload 承载 `MemoryPacket` 序列化（task_id / summary / kind 等）。

### 4.2 `GraphStoreAPI`（Protocol，一库两能力）

拓扑（节点用 `protocol.cyber.Asset`，边用 `(src, rel, dst)` 字符串元组）：

```python
def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None: ...
def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]: ...
def list_topologies(self) -> list[str]: ...
```

ATT&CK 知识（条目用 `protocol.memory.MemoryPacket`，字段含 technique_id/name/tactic/…）：

```python
def seed_attck(self, entries: list[MemoryPacket]) -> int: ...
def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None: ...
def get_technique(self, technique_id: str) -> MemoryPacket | None: ...
def search_techniques(self, keyword: str) -> list[MemoryPacket]: ...
def all_techniques(self) -> list[MemoryPacket]: ...
def add_relation(self, src: str, rel: str, dst: str) -> None: ...
def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]: ...
```

- `upsert_technique`：按 technique_id 单条写入/覆盖（供 `SemanticMemory.add` 委托）。

### 4.3 工厂函数

```python
def create_graph_store(mode: str = "in_memory", **kwargs) -> GraphStoreAPI: ...
def create_vector_store(mode: str = "in_memory", **kwargs) -> VectorStoreAPI: ...
```

- `mode`：`"in_memory"`（默认）/ `"neo4j"` / `"qdrant"`。
- 工厂内部委托 `data/models/registry.py`；`mode` 未知时抛 `ValueError`。
- 工厂接受 `**kwargs` 透传连接参数（uri/user/password/url/api_key/collection），由配置装配方提供。

## 5. `data/models/` 实现

### 5.1 `graph_store.py`

**`InMemoryGraphStore`**（默认，零依赖）
- 内部：`_topologies: dict[scope, tuple[list[Asset], list[link]]]` + `_attck: dict[tid, MemoryPacket]` + `_attck_edges: list[(src, rel, dst)]`。
- `seed_attck()` 缺省加载 `datasets/attck/knowledge.py` 数据集；`upsert_technique` 按 tid 写/覆盖 `_attck`。
- 构造参数 `seed_attck: bool = True`。

**`Neo4jGraphStore`**（真实，惰性）
- 构造仅存参数（uri/user/password），`_driver` 为 `None`；首次方法调用时 `import neo4j` 并连接。
- 未安装 `neo4j` 包 → 抛 `RuntimeError("Neo4j 驱动未安装，请 pip install aegisos[storage]")`。
- 拓扑：节点 label `Asset`（属性含 asset_id/host/os/exposure/services），关系 label = relation；`scope` 作为节点属性归组。
- ATT&CK：节点 label `Technique`，属性 technique_id/name/tactic/platform/description；关系 label = relation；`upsert_technique` 用 `MERGE` 幂等写。
- 连接失败 → 抛 `ConnectionError`（不静默降级，由装配方决定回退）。

### 5.2 `vector_store.py`

**`InMemoryVectorStore`**（默认）
- 内部 `list[(id, vector, payload)]` + 余弦相似度（复用 `_cosine` 逻辑，data 域内自带小工具，不跨域 import aegisos_agents）。
- `search` 按相似度降序，同分保写入序。

**`QdrantVectorStore`**（真实，惰性）
- 构造存参数（url/api_key/collection），首次方法调用时 `import qdrant_client` 并建 collection（`create_collection_if_missing`，向量维度以首条为准，cosine 度量）。
- 未安装 `qdrant-client` → 抛 `RuntimeError`。
- `add` = `upsert`（按 vector_id 幂等）；`delete` = `delete(ids=[id])`。

### 5.3 `registry.py`

```python
def create_graph_store(mode: str, **kwargs) -> GraphStoreAPI:
    if mode == "in_memory": return InMemoryGraphStore(**kwargs)
    if mode == "neo4j": return Neo4jGraphStore(**kwargs)
    raise ValueError(f"未知 graph_store mode: {mode}")
# 同 create_vector_store
```

## 6. ATT&CK 数据集（`data/datasets/attck/knowledge.py`）

```python
ATTACK_TECHNIQUES: dict[str, dict] = {
    "T1595": {"name": "Active Scanning", "tactic": "reconnaissance", "platform": "network",
              "description": "主动扫描目标收集可利用信息"},
    ...
}  # ~35 条

ATTACK_RELATIONS: list[tuple[str, str, str]] = [
    ("reconnaissance", "contains", "T1595"),
    ("T1210", "uses", "T1059"),
    ...
]  # tactic 包含 / 技术前置 / 缓解关联
```

- 必须**保留原 8 条**（T1595/T1592/T1210/T1059/T1078/T1046/T1021/T1053），字段兼容现有语义测试断言（`semantic["tactic"] == "lateral-movement"`）。
- 战术阶段：reconnaissance / initial-access / execution / persistence / defense-evasion / discovery / lateral-movement / detection（蓝队知识关联）。
- `to_memory_packets() -> list[MemoryPacket]` 辅助函数：转换为 `MemoryPacket(semantic={...})` 供 seed 使用。

## 7. 记忆子系统对接（行为保持）

### 7.1 `VectorMemory`（`memory/vector/store.py`）

```python
def __init__(self, backend: VectorStoreAPI | None = None) -> None:
    self._backend = backend
    if backend is None:
        self._items: list[MemoryPacket] = []   # 现有内存实现，原样保留
```

- `backend` 存在时：`add(packet)` → `backend.add(packet.task_id, packet.embedding, payload=_serialize(packet))`；`search(query, top_k)` → 委托 backend 后反序列化为 MemoryPacket；`all()`/`__len__` 委托。
- `backend` 为 None：现有逻辑不变（测试全绿）。
- `_serialize/_deserialize`：payload 保存 task_id/summary/kind/session_id；`embedding` 不入 payload（存向量本体）。

### 7.2 `SemanticMemory`（`memory/semantic/store.py`）

```python
def __init__(self, seed: bool = True, graph_backend: GraphStoreAPI | None = None) -> None:
    self._backend = graph_backend
    if graph_backend is None:
        self._knowledge: dict[str, MemoryPacket] = {}
        if seed:
            self.seed_attack_knowledge()   # 现有内存种子，原样保留
```

- `graph_backend` 存在时：
  - `add(concept_id, packet)` → `backend.upsert_technique(concept_id, packet)`。
  - `get/search/all` → 委托后端 ATT&CK 方法（`get_technique` / `search_techniques` / `all_techniques`）；`__len__` 委托 `len(backend.all_techniques())`。
  - `seed=True`：若后端 ATT&CK 为空，则以 `datasets/attck/knowledge.py` 数据集 `seed_attck()` 预载（保持与内存种子同源，避免后端为空的首次查询退化）。
- `graph_backend` 为 None：现有逻辑不变（内部内存种子）。

### 7.3 `MemoryStore`（`memory/memory_store.py`）

```python
def __init__(self, vector_backend: VectorStoreAPI | None = None,
             graph_backend: GraphStoreAPI | None = None) -> None:
    self.vector = VectorMemory(backend=vector_backend)
    self.semantic = SemanticMemory(seed=True, graph_backend=graph_backend)
    ...
```

- 仅新增两个可选参数，默认 None → 现有行为零变化；v2 子模块（retrieval/cache/checkpoint/reflection/archive/snapshot/sync）不动。

## 8. 配置与装配

### 8.1 `tooling/configs/settings.py`

新增 `StorageConfig`：

```python
@dataclass(frozen=True)
class StorageConfig:
    graph_mode: str = "in_memory"    # in_memory | neo4j
    vector_mode: str = "in_memory"   # in_memory | qdrant
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "memory_vectors"
```

`Settings` 根新增 `storage: StorageConfig`，env 前缀 `AEGIS_STORAGE_*`。

### 8.2 `tooling/configs/defaults.yaml`

```yaml
storage:
  graph_mode: "in_memory"
  vector_mode: "in_memory"
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: ""
  qdrant_url: "http://localhost:6333"
  qdrant_api_key: ""
  qdrant_collection: "memory_vectors"
```

### 8.3 装配（`backend/core/composition.py`）

```python
from data.api import create_graph_store, create_vector_store
storage = settings.storage
vector_backend = create_vector_store(storage.vector_mode,
                                     url=storage.qdrant_url, api_key=storage.qdrant_api_key,
                                     collection=storage.qdrant_collection) \
    if storage.vector_mode != "in_memory" else None
graph_backend = create_graph_store(storage.graph_mode,
                                   uri=..., user=..., password=...) \
    if storage.graph_mode != "in_memory" else None
self.memory_api = MemoryStore(vector_backend=vector_backend, graph_backend=graph_backend)
```

- 默认 in_memory 时 `vector_backend/graph_backend` 为 None → 与现状等价。
- 真实模式下懒加载 + 失败抛错（装配方自行捕获降级，后续可加 try/except 回退内存）。

### 8.4 依赖登记

- `pyproject.toml`：新增 `[project.optional-dependencies] storage = ["neo4j>=5", "qdrant-client>=1.8"]`。
- `12_TECH_STACK_SPEC.md` §3 登记：`neo4j >=5`（图存储，可选）、`qdrant-client >=1.8`（向量存储，可选），注明「惰性加载，仅 storage extra」。

## 9. 测试计划

### 9.1 新增 `tests/data/`

- `test_graph_store.py`：
  - InMemory：`seed_attck` 默认加载（≥35 条、含原 8 条）、`get/search/all/related`、拓扑 `save/get/list`、`add_relation`。
  - 工厂：`create_graph_store("in_memory")` 返回 InMemory；`create_graph_store("neo4j")` 未装驱动抛 `RuntimeError`；未知 mode 抛 `ValueError`。
- `test_vector_store.py`：
  - InMemory：add/search 降序/count/delete/all、空查询返回空。
  - 工厂：`create_vector_store("in_memory")`；`create_vector_store("qdrant")` 未装客户端抛 `RuntimeError`。
- （真实 Neo4j/Qdrant 适配器逻辑用 mock 或留待容器环境，不在本机连真库。）

### 9.2 扩展 memory 测试

- `test_vector.py`：新增 backend 注入模式（`VectorMemory(backend=InMemoryVectorStore())` 走委托路径）。
- `test_semantic.py`：新增 graph_backend 注入模式（`SemanticMemory(graph_backend=InMemoryGraphStore(seed_attck=False))`）。

### 9.3 回归

- 全量 `pytest`（现有 75 memory + data 新增 + 其余域）全绿。
- `mypy` 严格模式；`ruff`（需补装）format + lint。

## 10. 实施切分（遵守 11_AI_CODING_SPEC §2 ≤1 域/次）

| 轮次 | 域 | 内容 | 验证 |
|------|----|------|------|
| R1 | `data/` | datasets/attck + models（graph/vector/registry）+ api 接口与工厂 + settings/defaults + pyproject + tests/data + 12_TECH_STACK/05_API_SPEC 登记 | `pytest tests/data` + 全量回归 + mypy + ruff |
| R2 | `aegisos_agents/memory/` | VectorMemory/SemanticMemory/MemoryStore 后端注入 + 测试扩展 | 同上 |
| R3 | 装配+文档 | backend/composition 接线 + 文档同步（data/memory/根 AGENT.md、CLAUDE.md、ARCHITECTURE.md、plan.md 勾选、CHANGELOG）+ 刷新 README | 完整质量门禁 |

## 11. 文档一致性（11_AI_CODING_SPEC §7）

- `data/AGENT.md`：模块实现详解更新（models 两实现、datasets/attck、api 四接口）。
- `aegisos_agents/memory/AGENT.md`：vector/semantic 状态更新（支持后端注入）。
- `aegisos_agents/AGENT.md` + 根 `AGENT.md`：「模块实现总览」测试数/状态更新。
- `CLAUDE.md`：测试数、H2 完成状态。
- `docs/ARCHITECTURE.md`：data 域仪表盘更新。
- `developer/plan.md`：H2.1–H2.4 勾选、移到 §7、更新最近变更。
- `developer/CHANGELOG.md`：记录。
- `05_API_SPEC.md` §2.10 补充 GraphStoreAPI/VectorStoreAPI 契约表；`12_TECH_STACK_SPEC.md` 登记依赖。
- 根 `README.md`：运行 `python3 tooling/scripts/gen_readme.py` 刷新（本机可跑 python）。

## 12. 范围外（后续可做，本次不做）

- 新增 REST 端点暴露图/向量数据（现有 `GET /api/v1/graph` 保持不动）。
- 后端 range 服务把拓扑写入 Neo4j（本次仅提供 store 能力 + 种子样例）。
- `data/api` 的 `DatasetAPI`/`ModelSchemaAPI` 实现（本次不涉及）。
- 真实 Neo4j/Qdrant 集成测试（留待容器化 H1/P3）。
