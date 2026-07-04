# data/ 模块实现文档

> 数据层 — datasets（数据集） · models（数据模型，Neo4j + Qdrant 接入）。

📁 模块规范：[`AGENT.md`](AGENT.md) · Schema 规范：[`06_SCHEMA_SPEC.md`](../developer/specs/06_SCHEMA_SPEC.md)

---

## 目录结构

```
data/
├── api/
│   └── __init__.py        ✅ 2 个 Protocol 接口定义
├── datasets/              🔲 仅 AGENT.md
├── models/                🔲 仅 AGENT.md
└── aegisos.db             ✅ SQLite 数据库文件（后端运行时生成）
```

---

## 已实现

### `api/__init__.py` — 2 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `DatasetAPI` | `load(name)` · `list()` · `query(spec)` | 数据集加载与查询 |
| `ModelSchemaAPI` | `get(entity)` · `validate(data)` · `migrate(version)` | 数据模型 Schema 管理 |

### `aegisos.db` — SQLite 数据库

后端 `composition.py` 使用 `aiosqlite` 创建的本地数据库，存储：
- `sessions` 表 — 会话记录
- `tasks` 表 — 任务记录

---

## 未实现

### `datasets/` — 数据集（仅 AGENT.md）

计划内容：
- ATT&CK 技战术数据集
- CVE 漏洞数据库
- 网络资产拓扑样本
- 攻防场景测试数据

### `models/` — 数据模型（仅 AGENT.md）

计划内容：
- **Neo4j 图数据库**：网络拓扑图 + ATT&CK 技术关系图
- **Qdrant 向量数据库**：记忆嵌入向量存储 + 相似度检索

---

## 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H2 | Neo4j 拓扑图 + Qdrant 向量库接入 | 🔲 未开始 |
| — | ATT&CK / CVE 数据集导入 | 🔲 未开始 |
