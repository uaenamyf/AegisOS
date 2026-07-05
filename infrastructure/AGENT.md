# Infrastructure 基础设施层（域根） — AGENT.md

> 本文件是 `infrastructure/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
基础设施层：节点间通信、端边云协同、部署交付。按传输-节点-交付三子层组织。

## 内部分层
| 分类 | 说明 |
|------|------|
| infrastructure/transport/ | 传输（通信通道与编解码，低熵稀疏通信） |
| infrastructure/nodes/ | 节点（端侧 device + 边侧 edge + 云侧 cloud，端边云协同） |
| infrastructure/delivery/ | 交付（Docker/K8s/CI/CD 部署） |

## 读取目录（允许读）
- protocol/
- aegisos_agents/planning/engine/
- tooling/configs/
- developer/specs/09_DEVELOPMENT_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- aegisos_agents/ 业务逻辑

## 输出
- infrastructure/transport/communication/ 通信
- infrastructure/nodes/device/ 端侧（PC/手机/IoT，超低延迟本地推理）
- infrastructure/nodes/edge/ 边侧（边缘网关/机架服务器，区域聚合+中型模型）
- infrastructure/nodes/cloud/ 云侧（GPU 集群/厂家 API，全局编排+大模型）
- infrastructure/delivery/deployment/ 部署

## 依赖
- aegisos_agents/planning/engine/ 拓扑/事件
- protocol/ Message/Sync

## 接口
端边云协同与部署；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/infrastructure/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/infrastructure/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/infrastructure.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 12_TECH_STACK_SPEC.md
- **API 边界**：infrastructure/api/ — from infrastructure.api import ...
- **数据契约**：protocol/message.py / protocol/sync.py
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）

## 下辖子模块（传输-节点-交付 + 公共 API）
- **infrastructure/api/** 公共接口层：其他模块通过 `from infrastructure.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **传输 infrastructure/transport/**：`communication/` 低熵稀疏通信（通道/传输/编解码）
- **节点 infrastructure/nodes/**：`device/` 端侧节点（PC/手机/IoT，超低延迟本地推理/断连续传）、`edge/` 边侧节点（边缘网关/机架服务器，区域聚合/中型模型）、`cloud/` 云侧节点（GPU 集群/厂家 API，全局编排/注册发现）
- **交付 infrastructure/delivery/**：`deployment/` Docker/K8s/CI/CD 部署

---

## 📋 模块实现详解

> 原 `infrastructure/MODULE.md` 内容，已合并至此。

### 目录结构

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

### 已实现

#### `api/__init__.py` — 4 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `CommunicationAPI` | `send(message)` · `receive()` | 传输层通信 |
| `NodeRegistryAPI` | `register(node)` · `list_nodes()` · `get(node_id)` | 节点注册管理 |
| `SyncAPI` | `sync(op: SyncOp)` · `status(node_id)` | 端边云同步 |
| `DeploymentAPI` | `deploy(spec)` · `status(deployment_id)` · `rollback(deployment_id)` | 部署交付 |

### 未实现（全空，仅 AGENT.md）

#### `transport/communication/` — 传输层
- 消息传输通道（HTTP/gRPC/MQTT）
- 消息队列与路由

#### `nodes/edge/` — 端侧节点
- 端侧运行时（轻量模型推理）
- 本地数据存储
- 隐私数据处理

#### `nodes/cloud/` — 云侧节点
- 云侧运行时（大模型推理）
- 分布式调度
- 全局状态管理

#### `delivery/deployment/` — 部署交付
- Docker 容器编排
- CI/CD 流水线
- 沙箱靶场环境（H1 待做）

### 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H1 | Docker 沙箱靶场（攻防工具隔离运行环境） | 🔲 未开始 |
| H2 | 端边云协同部署 | 🔲 未开始 |
| — | Neo4j + Qdrant 容器化 | 🔲 未开始 |
