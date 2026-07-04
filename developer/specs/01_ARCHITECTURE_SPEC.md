# 01_ARCHITECTURE_SPEC.md — 架构规范

> 上游：`00_PROJECT_SPEC.md`。本文件定义 AegisOS 的系统架构。冲突时以 `00` 为准。

---

## 1. 分层架构（Layered Architecture）

```
┌───────────────────────────────────────────────────────────┐
│  frontend/   表现层  Controller-Service-Mapper + Views     │
│   controllers · services · mappers · views                │
│    (canvas · graph · monitor · replay)                    │
├───────────────────────────────────────────────────────────┤
│  backend/    应用层  Router-Service-Repository-Model + Core  │
│   gateway → controllers → services → mappers              │
├───────────────────────────────────────────────────────────┤
│  agents/     智能体域  认知架构五层                          │
│   perception · planning · action · memory · tools         │
│    engine: planner·scheduler·router·workflow·eventbus·topology │
├───────────────────────────────────────────────────────────┤
│  protocol/   契约层  唯一数据契约（26 类型）                 │
├───────────────────────────────────────────────────────────┤
│  infrastructure/  基础设施层  transport·nodes·delivery      │
└───────────────────────────────────────────────────────────┘
  observability/  可观测与评估  inspect·measure·present
  data/ · tooling/ · docs/ · tests/   支撑
  developer/(含 specs/·roadmap/)  规范层（纵切所有层，不参与运行时）
```

- 依赖方向自上而下；`protocol/` 是唯一被全局依赖的层（零反向依赖）。
- 跨域调用只经各域 `api/`（依赖反转），见 `03_IMPORT_SPEC.md`。

---

## 2. 微内核架构（Microkernel）

AegisOS 以「微内核 + 插件」组织稳定核心与可变扩展：

| 类别 | 内容 | 稳定性 |
|------|------|--------|
| **内核（稳定）** | `protocol/` 契约 + 各域 `api/` 接口签名 + `agents/planning/engine/`（planner·scheduler·router·workflow·eventbus·topology）核心编排 | 冻结 |
| **插件（可变）** | Agent 角色（`agents/action/*`）、工具（`agents/action/execution/tools/`）、LLM 适配（`agents/tools/llms/`）、记忆后端（`agents/memory/*`）、节点（`infrastructure/nodes/*`）、可视化视图（`frontend/src/views/*`） | 可替换/可新增 |

- 内核定义扩展点（接口/注册表）；插件实现接口并通过注册表接入。
- 新增插件不改内核；内核升级须保证插件接口兼容（向后兼容）。

---

## 3. 领域驱动设计（DDD）

| 限界上下文 | 聚合根 | 关键实体/值对象 | 仓库 |
|------------|--------|-----------------|------|
| Planning | `Plan`（DAG） | `Task`、`Schedule`、`Route` | `backend/mappers/repositories/` |
| Agent | `Agent` | `AgentStatus`、`NodeRef` | `agents/api/AgentRegistryAPI` |
| Memory | `MemoryPacket` | working/semantic/episodic/archive/embedding | `agents/api/MemoryAPI` |
| Tool | `ToolCall`/`ToolResult`/`ToolSpec` | args_schema、permission | `agents/action/execution/tools/` |
| Graph | `Graph` | `GraphNode`、`GraphEdge`、`GraphDiff` | `agents/planning/engine/topology/` |
| Communication | `Message` | `Header`、`NodeRef` | `infrastructure/transport/communication/` |
| Observation | `Event`/`Heartbeat` | `EventType` | `observability/` |

- 跨上下文只通过 `protocol/` 值对象 + `api/` 接口通信，禁止跨上下文共享内部实体。

---

## 4. 事件驱动（Event Driven）

- 事件总线：`agents/planning/engine/eventbus/`；事件类型定义在 `protocol/event.py`（8 类）。
- 生产者发布 `Event`（封装于 `Message` 信封）；消费者订阅 topic `{domain}.{type}`。
- 至少一次投递 + `event_id` 幂等去重；同 `task_id` 保序（partition by task_id）；失败 N 次进死信队列。
- 事件驱动确定性回放（`observability/inspect/replay/`）。
- 详见 `07_EVENT_SPEC.md`。

---

## 5. 消息驱动（Message Driven）

- 所有跨模块通信走 `protocol/message.py` 的 `Message` 信封，禁止裸 JSON。
- 信封分层：`Header → Session → Task → Node → Route → Payload → Metadata → Signature`。
- 动态路由：`Task → Semantic Graph → Agent Graph → Dynamic Routing → Sparse Communication → Adaptive Graph → GraphUpdate`。
- 详见 `04_PROTOCOL_SPEC.md`。

---

## 6. 插件架构（Plugin Architecture）

- **注册表模式**：Agent / Tool / LLM / Memory 后端 / Node 均通过注册表接入。
- **DI 注入**：实现由各域内部注入到 `api/` 接口，便于 mock 与替换。
- **规格驱动**：工具以 `ToolSpec`（args_schema/output_schema/permission/resource_limit）声明；Agent 以 `Agent`（capabilities/trust_score/success_rate）声明。
- **沙箱执行**：工具经 `agents/action/execution/executor/` 沙箱执行 + 权限校验。

---

## 7. Agent Runtime（智能体运行时）

- 位置：`agents/tools/runtime/`。
- 职责：Agent 生命周期托管、上下文注入、心跳、挂起/恢复。
- 生命周期：`Initialize → Load Config → Load Prompt → Load Skills → Receive Task → Reasoning → Memory Read → Tool Call → Reflection → Return Result → Log → Heartbeat → Finish`。
- 统一接口：`receive(task)` → `think()` → `tool()` → `reflect()` → `respond()`。
- 详见 `08_AGENT_SPEC.md`。

---

## 8. Memory Runtime（记忆运行时）

- 位置：`agents/memory/`（12 子模块）。
- 写入流：`data → compression → split(working/semantic/episodic/archive) → vector index → reflection → cache → sync`。
- 读取流：`query → retrieval(vector+keyword+graph) → rerank → assemble MemoryPacket`。
- 接口：`read(query)→MemoryPacket`、`write(packet)→bool`、`retrieve(query)→list`。
- 幂等写入（packet id 去重）；checkpoint/snapshot 恢复。

---

## 9. Scheduler（调度器）

- 位置：`agents/planning/engine/scheduler/`。
- 策略：多级优先级队列 + DAG 拓扑序 + 资源 + 信任度调度；抢占；指数退避重试；超时熔断；死锁检测；老化反饥饿。
- 产物：`Schedule`（schedule_id/task_id/assigned_to/queued_at/priority）。
- 依赖：`Task`（retry/rollback/dependency/priority/status）。

---

## 10. Router（路由器）

- 位置：`agents/planning/engine/router/`（赛事亮点）。
- 目标：最小化通信熵，选择高信任/低延迟稀疏链路。
- 流程：`Task → Semantic Graph → Agent Graph → Dynamic Routing → Sparse Communication → Adaptive Graph → GraphUpdate`。
- 产物：`Route`（task_id/path/cost/entropy）；图差分 `GraphDiff`。
- 边属性：weight/entropy/latency/trust_score/success_rate。

---

## 11. Workflow（工作流引擎）

- 位置：`agents/planning/engine/workflow/`。
- 模型：DAG（`Plan.dag`）；节点 = `Task`；边 = `dependency`。
- 生命周期：`Created → Planned → Routed → Scheduled → Running → Checkpointed → (Retry|Rollback) → Succeeded|Failed|Cancelled`。

---

## 12. Frontend（前端）

- 技术栈：React + TypeScript + Vite；轻量 store；WebGL/Canvas 图渲染。
- 结构：`controllers`（interaction/events/routes）→ `services`（api/realtime/session/graph）→ `mappers`（viewmodels/apimappers/store/utils/styles/assets）→ `views`（canvas/graph/monitor/replay）。
- 实时：WebSocket（双向）+ SSE（单向事件流）。
- 边界：只调 `backend.api` 暴露的 REST/WS/SSE，不直连 `agents`/`infrastructure`。

---

## 13. Backend（后端）

- 技术栈：Python 3.11+、asyncio。
- 结构：`core`（composition/auth/middleware/routes）→ `routers`（REST/WS/SSE 端点）→ `services`（session/task/agent/memory/graph + di_ports）→ `repositories`（database/repositories）→ `models`（entities/converters）。
- 对外：`/api/v1/...` 经 gateway；透传 `X-Trace-Id`/`X-Session-Id`/`X-Task-Id`。

---

## 14. Infrastructure（基础设施）

- `transport/communication/`：低熵稀疏通信。
- `nodes/edge/` + `nodes/cloud/`：端边云协同，离线优先，`SyncPacket`（vector_clock）按需同步。
- `delivery/deployment/`：Docker/K8s/CI/CD。

---

## 15. Deployment（部署）

- 容器化（Docker）+ 编排（K8s）；`make setup/test/build/deploy`。
- 端边云分离部署：边缘节点离线优先，云侧聚合评估。
- 配置走 `tooling/configs/`（environments/agents/models/prompts yaml）；密钥走环境变量。
- 详见 `09_DEVELOPMENT_SPEC.md` 的 Release/Hotfix。

---

## 16. Fault Tolerance（容错）

| 机制 | 位置 |
|------|------|
| 任务重试 | `Task.retry`（RetryPolicy: max_attempts/backoff） |
| 任务回滚 | `Task.rollback`（RollbackPlan: enabled/steps） |
| 检查点/快照 | `agents/memory/checkpoint/`、`agents/memory/snapshot/` |
| 事件回放 | `agents/planning/engine/eventbus/` + `observability/inspect/replay/` |
| 心跳超时 | `Heartbeat`（cpu/gpu/latency/memory/token/status） |
| LLM 回退 | `agents/tools/llms/` |
| 死信队列 | EventBus（失败 N 次） |

---

## 17. Scalability（可扩展性）

- 水平扩展：节点注册（`infrastructure.api.NodeRegistryAPI`）+ 心跳；调度按资源/信任度分配。
- 异步 I/O：eventbus/transport/llms/gateway 用 asyncio。
- 解耦扩展：新增 Agent/工具/节点/视图不改内核（见 §2、`00` §9）。
- 度量：`observability/measure/`（延迟、Token 成本、通信熵、覆盖率）。
