# 10_INTERFACE_BOUNDARY_SPEC.md — 接口边界规范

> 上游：`00_PROJECT_SPEC.md`、`05_API_SPEC.md`。本文件是**保证真正并行开发的核心**。
> 它精确规定每个调用方可以调用哪些接口、哪些接口只能内部调用、哪些必须异步/经网关/走 EventBus。
> 前端、后端、Agent 三团队（或三个 AI）在本文件约束下可独立开发、并行推进、低冲突集成。

---

## 1. 调用方 × 接口 矩阵

| 接口（API） | 前端 | 后端 | Agent | 内部-only | 必须异步 | 必须经 Gateway | 必须走 EventBus |
|-------------|:----:|:----:|:-----:|:---------:|:--------:|:--------------:|:---------------:|
| **外部 REST（/api/v1/...）** | ✅ | 提供 | ❌ | ❌ | 部分 | ✅ | ❌ |
| **WebSocket /ws/v1/stream** | ✅ | 提供 | ❌ | ❌ | ✅ | ✅ | ❌ |
| **SSE /api/v1/events** | ✅ | 提供 | ❌ | ❌ | ✅ | ✅ | ❌ |
| `backend.api.SessionAPI` | ✅(经REST) | 自用 | ❌ | ❌ | — | ✅ | ❌ |
| `backend.api.TaskAPI` | ✅(经REST) | 自用 | ❌ | ❌ | create 异步触发 | ✅ | 触发事件 |
| `backend.api.MemoryGatewayAPI` | ✅(经REST) | 自用 | ❌ | ❌ | — | ✅ | ❌ |
| `backend.api.GraphAPI` | ✅(经REST) | 自用 | ❌ | ❌ | — | ✅ | ❌ |
| `backend.api.EventStreamAPI` | ✅(SSE/WS) | 自用 | ❌ | ❌ | ✅ | ✅ | ✅(订阅) |
| `agents.api.AgentRegistryAPI` | ❌ | ✅ | ✅ | ❌ | — | ❌ | ❌ |
| `agents.api.PlanningAPI` | ❌ | ✅ | ✅ | plan/route 内核 | ✅ | ❌ | 触发事件 |
| `agents.api.ExecutionAPI` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅(ToolCall/Finish) |
| `agents.api.PerceptionAPI` | ❌ | ❌ | ✅ | ✅ | — | ❌ | ❌ |
| `agents.api.MemoryAPI` | ❌(经后端) | ✅(桥接) | ✅ | ❌ | write 异步 | ❌ | ✅(MemoryUpdate) |
| `agents.api.EventBusAPI` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | 本身即 EventBus |
| `agents.api.RuntimeAPI` | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `infrastructure.api.CommunicationAPI` | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `infrastructure.api.NodeRegistryAPI` | ❌ | ✅ | ✅ | ✅ | — | ❌ | ❌ |
| `infrastructure.api.SyncAPI` | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `infrastructure.api.DeploymentAPI` | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `observability.api.MonitorAPI` | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅(订阅) |
| `observability.api.TraceAPI` | ❌ | ✅ | ❌ | ✅ | — | ❌ | ❌ |
| `observability.api.ReplayAPI` | ✅(经REST) | ✅ | ❌ | ❌ | ✅ | ✅ | ✅(读事件) |
| `observability.api.BenchmarkAPI` | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `observability.api.EvaluationAPI` | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅(订阅) |
| `observability.api.VisualizationAPI` | ✅ | ✅ | ❌ | ❌ | — | ❌ | ❌ |
| `data.api.DatasetAPI` | ❌ | ✅ | ✅ | ✅ | — | ❌ | ❌ |
| `data.api.ModelSchemaAPI` | ❌ | ✅ | ❌ | ✅ | — | ❌ | ❌ |
| `tooling.api.ConfigAPI` | ❌ | ✅ | ✅ | ✅ | — | ❌ | ❌ |
| `tooling.api.ScriptAPI` | ❌ | ✅ | ❌ | ✅ | — | ❌ | ❌ |

> ✅=允许 · ❌=禁止 · 提供=该方实现该接口 · 自用=仅本域使用

---

## 2. 前端可调用接口（Frontend Boundary）

前端**只能**通过 `backend.gateway` 暴露的对外接口与系统交互：

| 通道 | 接口 | 用途 |
|------|------|------|
| REST | `/api/v1/sessions`、`/api/v1/tasks`、`/api/v1/agents`、`/api/v1/graph`、`/api/v1/metrics`、`/api/v1/observability/inspect/replay/{session}` | 同步查询/创建 |
| WebSocket | `ws://host/ws/v1/stream?session=...` | 双向实时（Agent 状态/协作） |
| SSE | `/api/v1/events?stream=...` | 单向事件流（AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate） |

**禁止**：
- 前端直连 `agents.api` / `infrastructure.api` / `observability.api`（除经 backend 暴露的）。
- 前端直接读写 `protocol/` 跨域结构（须经 backend 序列化）。
- 前端直连数据库 / LLM。

前端内部：`frontend.api`（ViewAPI/InteractionAPI/ThemeAPI）供自用与 backend 注入。

---

## 3. 后端可调用接口（Backend Boundary）

后端是应用层，编排各域：

- **对外提供**：REST/WS/SSE（经 gateway）。
- **可调**：`agents.api`（全部 7 接口）、`infrastructure.api`（NodeRegistry/Deployment）、`observability.api`（Monitor/Trace/Replay/Benchmark/Evaluation/Visualization）、`data.api`、`tooling.api`、`protocol`。
- **禁止**：调 `frontend.api`（逆向）；直连 `agents`/`infrastructure` 内部子包（须经 `api/`）。
- 后端编排：`TaskAPI.create` 异步触发 `PlanningAPI.plan` → route → schedule → execute，结果经事件流回推前端。

---

## 4. Agent 可调用接口（Agent Boundary）

Agent 域是执行核心：

- **可调**：`agents.api`（全部，含 EventBusAPI/RuntimeAPI）、`infrastructure.api`（Communication/NodeRegistry/Sync）、`data.api`（Dataset）、`tooling.api`（Config）、`protocol`。
- **禁止**：调 `backend.api`（逆向依赖）；调 `frontend.api`；直连他域内部子包。
- Agent 间协作走 **EventBus + 低熵路由**，不直接互调内部。

---

## 5. 仅内部调用接口（Internal-Only）

以下接口**不对外暴露**，仅限系统内部（后端/Agent 域内）调用：

| 接口 | 内部使用者 |
|------|-----------|
| `agents.api.PerceptionAPI` | Agent 域内（runtime/perception） |
| `agents.api.RuntimeAPI` | 后端编排 + Agent 域内 |
| `infrastructure.api.CommunicationAPI` | Agent 域 + infrastructure 内 |
| `infrastructure.api.SyncAPI` | infrastructure 内 + Agent 域 |
| `infrastructure.api.DeploymentAPI` | 后端 + infrastructure 内 |
| `observability.api.MonitorAPI/TraceAPI/BenchmarkAPI/EvaluationAPI` | 后端 + observability 内 |
| `data.api` | 后端 + Agent 域 |
| `tooling.api` | 后端 + Agent 域 |
| gRPC 内部服务（Scheduler/Router/Memory/Tool） | 子系统间，不对外 |

---

## 6. 必须异步的接口（Async-Only）

I/O 密集 / 长耗时 / 流式接口必须 `async`：

| 接口 | 理由 |
|------|------|
| `TaskAPI.create` | 异步触发 planner，不阻塞请求 |
| `PlanningAPI.plan/route/schedule` | LLM 推理 + 图计算，长耗时 |
| `ExecutionAPI.run` | 工具沙箱执行 |
| `MemoryAPI.write` | 压缩/向量索引/同步 |
| `EventBusAPI.publish/subscribe` | 发布订阅 |
| `RuntimeAPI.start/stop/heartbeat` | 生命周期 |
| `CommunicationAPI.send` | 跨网传输 |
| `SyncAPI.sync` | 端边云同步 |
| `DeploymentAPI.deploy` | 部署长流程 |
| `MonitorAPI/ReplayAPI/BenchmarkAPI/EvaluationAPI` | 流式/长计算 |
| WebSocket / SSE | 实时流 |

> 实现语言：Python 侧用 `asyncio`；前端用 Promise/async。

---

## 7. 必须经过 Gateway 的接口（Gateway-Only）

所有**外部入口**必须经 `backend/gateway/`（鉴权 + 限流 + 协议适配）：

- 全部 REST `/api/v1/...`
- WebSocket `/ws/v1/...`
- SSE `/api/v1/events`

**禁止**：绕过 gateway 直连 controllers/services；外部直连内部 gRPC。

---

## 8. 必须走 EventBus 的接口（EventBus-Only）

以下交互**必须**经 EventBus（发布订阅），不得直接同步互调：

| 交互 | 事件 |
|------|------|
| Agent 开始/完成 | `AgentStart` / `AgentFinish` |
| 工具调用/完成 | `ToolCall` / `ToolFinish` |
| 任务重试/回滚 | `Retry` / `Rollback` |
| 记忆变更广播 | `MemoryUpdate` |
| 拓扑图变更广播 | `GraphUpdate` |
| 可观测订阅（monitor/replay/evaluation） | 订阅上述事件 |
| 前端实时推送（经 backend SSE/WS） | 订阅上述事件 |

> EventBus 是解耦点：生产者与消费者不互相 import，天然支持并行开发与确定性回放。

---

## 9. 并行开发契约

- **契约冻结**：`protocol/` 类型 + 各域 `api/` 签名冻结后，三方并行。
- **前端**：只依赖 `backend.api` 的对外接口契约（REST/WS/SSE 形状 + `protocol` 类型），不依赖后端实现。
- **后端**：只依赖 `agents.api`/`infrastructure.api`/`observability.api` 的接口签名，不依赖其实现（DI 注入 + mock 测试）。
- **Agent**：只依赖 `protocol/` + `agents.api` 内部契约 + EventBus 事件契约，独立实现角色与引擎。
- **集成**：三方对契约集成，不对实现集成；接口边界由本文件强约束，冲突在契约层解决。
