# Data 数据层（域根） — AGENT.md

> 本文件是 `data/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
数据层：数据集与数据模型/Schema。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子系统逻辑

## 输出
- data/datasets/ 数据集
- data/models/ 数据模型

## 依赖
- protocol/ 复用基础类型

## 接口
load/register；单一可信数据源。

## 测试方式
`pytest tests/data/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/data/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/data/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/data.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/06_SCHEMA_SPEC.md
- **API 边界**：data/api/ — from data.api import ...
- **数据契约**：protocol/memory.py（MemoryPacket）/ protocol/graph.py
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H2 Neo4j/Qdrant）

## 下辖子模块
- **data/api/** 公共接口层：其他模块通过 `from data.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- `data/datasets/` 数据集加载/预处理/版本
- `data/models/` 数据模型/Schema 注册/迁移

---

## 📋 模块实现详解

> 原 `data/MODULE.md` 内容，已合并至此。

### 目录结构

```
data/
├── api/
│   └── __init__.py        ✅ 4 个 Protocol 接口 + 3 个工厂函数
├── datasets/
│   └── attck/
│       └── knowledge.py   ✅ ATT&CK 数据集（~36 技战术 + 关系边）
├── models/
│   ├── graph_store.py     ✅ InMemoryGraphStore / Neo4jGraphStore
│   ├── vector_store.py    ✅ InMemoryVectorStore / QdrantVectorStore
│   └── registry.py        ✅ mode 分发工厂
└── aegisos.db             ✅ SQLite 数据库文件（后端运行时生成）
```

### 已实现

#### `api/__init__.py` — 4 个公共接口 + 工厂（Protocol）

| 接口/函数 | 方法/说明 | 说明 |
|------|------|------|
| `DatasetAPI` | `load(name)` · `list_datasets()` · `preprocess(config)` | 数据集加载与查询 |
| `ModelSchemaAPI` | `register_schema()` · `validate()` · `get_schema()` · `migrate()` | 数据模型 Schema 管理 |
| `GraphStoreAPI` | `save_topology` · `get_topology` · `list_topologies` · `seed_attck` · `upsert_technique` · `get/search/all_techniques` · `add_relation` · `related_techniques` | 图存储（拓扑 + ATT&CK），Neo4j/内存双实现 |
| `VectorStoreAPI` | `add` · `search` · `delete` · `count` · `all` | 向量存储，Qdrant/内存双实现 |
| `create_graph_store(mode)` / `create_vector_store(mode)` / `load_attck_dataset()` | 工厂 + 数据集加载 | 消费方（memory/backend）只经 `data.api` |

#### `models/` — 存储后端（H2 双实现适配层）

- **`graph_store.py`**：`InMemoryGraphStore`（默认，dict 参考实现）+ `Neo4jGraphStore`（真实客户端，`neo4j>=5` 惰性加载）。网络拓扑用 `protocol.cyber.Asset` 节点 + 带标签关系；ATT&CK 用 `Technique` 节点 + 关系边。
- **`vector_store.py`**：`InMemoryVectorStore`（默认，余弦检索）+ `QdrantVectorStore`（真实客户端，`qdrant-client>=1.8` 惰性加载）。
- **`registry.py`**：按 `mode` 分发（in_memory/neo4j/qdrant），未知 mode 抛 `ValueError`。

#### `datasets/attck/knowledge.py` — ATT&CK 数据集

`ATTACK_TECHNIQUES`（~36 条，覆盖 3 场景）+ `ATTACK_RELATIONS`（contains/precedes/uses/targets）+ `load_attck_dataset()`。保留原 8 条种子，与记忆子系统共享单一知识源。

#### `aegisos.db` — SQLite 数据库

后端 `composition.py` 使用 `aiosqlite` 创建的本地数据库，存储：
- `sessions` 表 — 会话记录
- `tasks` 表 — 任务记录

### 未实现

- 🔲 真实 Neo4j/Qdrant 集成测试（需运行中 DB，留待容器化 H1/P3）
- ✅ CVE 离线样本与资产服务匹配查询（`datasets/cve/`）
- ✅ 后端 range 服务将生成拓扑写入 `GraphStore`
- 🔲 更大规模 CVE/网络资产拓扑样本与真实数据导入器

### 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H2 | Neo4j 拓扑图 + Qdrant 向量库接入 | ✅ 完成（2026-08-06，双实现适配层，默认 in_memory） |
| H2.3/H2.4 | 记忆子系统对接（vector→Qdrant / semantic→Neo4j ATT&CK） | ✅ 完成（`memory/vector` · `memory/semantic` 后端注入） |
