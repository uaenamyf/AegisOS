# infrastructure/ 模块实现文档

> 基建层 — 传输 · 节点(端·云) · 交付（部署）。

📁 模块规范：[`AGENT.md`](AGENT.md) · 架构规范：[`01_ARCHITECTURE_SPEC.md`](../developer/specs/01_ARCHITECTURE_SPEC.md)

---

## 目录结构

```
infrastructure/
├── api/
│   └── __init__.py        ✅ 4 个 Protocol 接口定义
├── transport/
│   └── communication/     🔲 仅 AGENT.md
├── nodes/
│   ├── edge/              🔲 仅 AGENT.md
│   └── cloud/             🔲 仅 AGENT.md
└── delivery/
    └── deployment/        🔲 仅 AGENT.md
```

---

## 已实现

### `api/__init__.py` — 4 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `CommunicationAPI` | `send(message)` · `receive()` | 传输层通信 |
| `NodeRegistryAPI` | `register(node)` · `list_nodes()` · `get(node_id)` | 节点注册管理 |
| `SyncAPI` | `sync(op: SyncOp)` · `status(node_id)` | 端边云同步 |
| `DeploymentAPI` | `deploy(spec)` · `status(deployment_id)` · `rollback(deployment_id)` | 部署交付 |

---

## 未实现（全空，仅 AGENT.md）

### `transport/communication/` — 传输层
- 消息传输通道（HTTP/gRPC/MQTT）
- 消息队列与路由

### `nodes/edge/` — 端侧节点
- 端侧运行时（轻量模型推理）
- 本地数据存储
- 隐私数据处理

### `nodes/cloud/` — 云侧节点
- 云侧运行时（大模型推理）
- 分布式调度
- 全局状态管理

### `delivery/deployment/` — 部署交付
- Docker 容器编排
- CI/CD 流水线
- 沙箱靶场环境（H1 待做）

---

## 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H1 | Docker 沙箱靶场（攻防工具隔离运行环境） | 🔲 未开始 |
| H2 | 端边云协同部署 | 🔲 未开始 |
| — | Neo4j + Qdrant 容器化 | 🔲 未开始 |
