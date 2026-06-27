# 05_API_SPEC.md — API 接口契约规范

> 上游：`00_PROJECT_SPEC.md`、`04_PROTOCOL_SPEC.md`。本文件定义全系统 API Contract。
> 模块间解耦：每个域通过 `api/` 子包暴露 `typing.Protocol` 接口（共 **29 个**），参数/返回值一律 `protocol/` 类型。
> `api/` 签名变更 = 破坏性变更（major bump + CHANGELOG + 通知依赖方）。

---

## 0. 传输协议

| 协议 | 用途 | 同步性 |
|------|------|--------|
| REST (HTTP) | 任务创建/查询/配置 | 同步 |
| WebSocket | Agent 状态、协作消息 | 双向实时 |
| SSE | 事件推送、日志流 | 单向流 |
| gRPC | 内部高性能 RPC（子系统间） | 同步/流 |

## 1. 统一约定

- 所有外部入口：`/api/v1/...`，经 `backend/gateway/` 鉴权 + 限流。
- 请求/响应体使用 `protocol/` 类型，禁止裸 JSON 自造结构。
- 透传 Header：`X-Trace-Id`、`X-Session-Id`、`X-Task-Id`。
- 错误统一：`{ "code": str, "message": str, "trace_id": str }`。
- URL 版本 `/v1/`；字段新增可选；废弃先 deprecated 一个版本。

---

## 2. 模块 API 契约（每模块：API / Request / Response / Error / Timeout / Retry / Version）

### 2.1 Frontend（`frontend.api`：ViewAPI · InteractionAPI · ThemeAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| ViewAPI.render(view) | view: str | view 状态 | code:VIEW_NOT_FOUND | 5s | 不重试（UI） | v1 |
| InteractionAPI.dispatch(event) | event: dict | ack: bool | code:INVALID_EVENT | 3s | 不重试 | v1 |
| ThemeAPI.apply(theme) | theme: str | ack: bool | code:UNKNOWN_THEME | 3s | 不重试 | v1 |

> 前端不直接对外暴露 REST；经 backend 代理。前端只调 `backend.api`。

### 2.2 Backend（`backend.api`：SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| SessionAPI.create | user: dict | session_id: str | code:AUTH_FAILED | 10s | 不重试 | v1 |
| SessionAPI.get | session_id: str | session: dict | code:NOT_FOUND | 5s | 不重试 | v1 |
| TaskAPI.create | goal: str | task: Task | code:INVALID_GOAL | 30s | 不重试（异步触发 planner） | v1 |
| TaskAPI.get | task_id: str | task: Task | code:NOT_FOUND | 5s | 不重试 | v1 |
| TaskAPI.cancel | task_id: str | ack: bool | code:NOT_CANCELLABLE | 10s | 不重试 | v1 |
| MemoryGatewayAPI.read | session: str | MemoryPacket | code:NOT_FOUND | 10s | 1 次 | v1 |
| MemoryGatewayAPI.write | session, packet | ack: bool | code:WRITE_FAILED | 10s | 2 次 | v1 |
| GraphAPI.get | — | Graph | code:UNAVAILABLE | 10s | 1 次 | v1 |
| EventStreamAPI.subscribe | stream: str | Event 流 (SSE/WS) | code:STREAM_CLOSED | — | 自动重连 | v1 |

### 2.3 Agent（`agents.api`：AgentRegistryAPI · PlanningAPI · ExecutionAPI · PerceptionAPI · RuntimeAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| AgentRegistryAPI.list | filter: dict | list[Agent] | — | 5s | 不重试 | v1 |
| AgentRegistryAPI.register | agent: Agent | ack: bool | code:DUPLICATE | 5s | 不重试 | v1 |
| AgentRegistryAPI.get | agent_id: str | Agent | code:NOT_FOUND | 5s | 不重试 | v1 |
| PlanningAPI.plan | goal: str | Plan | code:PLAN_FAILED | 60s | 1 次 | v1 |
| PlanningAPI.route | task: Task | Route | code:NO_ROUTE | 30s | 2 次 | v1 |
| PlanningAPI.schedule | task: Task | Schedule | code:NO_RESOURCE | 30s | 2 次 | v1 |
| ExecutionAPI.run | task: Task | ToolResult/result | code:EXEC_FAILED | task.retry | 按 Task.retry | v1 |
| PerceptionAPI.observe | context: dict | reasoning: dict | code:OBSERVE_FAILED | 30s | 1 次 | v1 |
| RuntimeAPI.start | agent_id: str | ack: bool | code:ALREADY_RUNNING | 10s | 不重试 | v1 |
| RuntimeAPI.stop | agent_id: str | ack: bool | code:NOT_RUNNING | 10s | 不重试 | v1 |

### 2.4 Memory（`agents.api.MemoryAPI`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| MemoryAPI.read | query: dict | MemoryPacket | code:NOT_FOUND | 10s | 1 次 | v1 |
| MemoryAPI.write | packet: MemoryPacket | bool | code:WRITE_FAILED | 10s | 2 次（幂等） | v1 |
| MemoryAPI.retrieve | query: dict | list | code:RETRIEVE_FAILED | 10s | 1 次 | v1 |

> 写入幂等（packet id 去重）；checkpoint/snapshot 恢复。

### 2.5 Scheduler（`agents.api.PlanningAPI.schedule`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| schedule | task: Task | Schedule | code:NO_RESOURCE / code:DEADLOCK | 30s | 2 次 | v1 |
| reschedule | task_id: str | Schedule | code:NOT_FOUND | 15s | 1 次 | v1 |

> 策略：多级优先级队列 + DAG 拓扑序 + 资源 + 信任度；抢占；指数退避；超时熔断；老化反饥饿。

### 2.6 Planner（`agents.api.PlanningAPI.plan` + `agents/planning/engine/planner/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| plan | goal: str | Plan (DAG) | code:PLAN_FAILED | 60s | 1 次 | v1 |
| replan | plan_id: str, feedback | Plan | code:REPLAN_FAILED | 60s | 1 次 | v1 |

### 2.7 Router（`agents.api.PlanningAPI.route` + `agents/planning/engine/router/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| route | task: Task | Route | code:NO_ROUTE | 30s | 2 次 | v1 |
| updateGraph | diff: GraphDiff | Graph | code:INVALID_DIFF | 15s | 1 次 | v1 |

> 低熵稀疏路由；发 `GraphUpdate` 事件。

### 2.8 Tool（`agents.api.ExecutionAPI` + `agents/action/execution/tools/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| invoke | call: ToolCall | result: ToolResult | code:TOOL_FAILED / code:PERMISSION_DENIED | call.timeout (默认 30s) | 不重试（由上层 Task.retry 决定） | v1 |
| register | spec: ToolSpec | ack: bool | code:DUPLICATE | 5s | 不重试 | v1 |

> 沙箱执行 + 权限校验 + 资源限制；每次调用发 `ToolCall`/`ToolFinish` 事件。

### 2.9 Runtime（`agents.api.RuntimeAPI` + `agents/tools/runtime/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| start | agent_id: str | bool | code:ALREADY_RUNNING | 10s | 不重试 | v1 |
| stop | agent_id: str | bool | code:NOT_RUNNING | 10s | 不重试 | v1 |
| heartbeat | agent_id, Heartbeat | bool | code:OFFLINE | 5s | 3 次 | v1 |
| suspend/resume | agent_id: str | bool | code:INVALID_STATE | 10s | 不重试 | v1 |

### 2.10 EventBus（`agents.api.EventBusAPI` + `agents/planning/engine/eventbus/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| publish | event: Event | ack: bool | code:PUBLISH_FAILED | 5s | 3 次（至少一次） | v1 |
| subscribe | topic: str, handler | subscription_id: str | code:INVALID_TOPIC | 5s | 不重试 | v1 |
| unsubscribe | subscription_id: str | bool | code:NOT_FOUND | 5s | 不重试 | v1 |

> 至少一次投递 + `event_id` 幂等去重；同 `task_id` 保序；失败 N 次进死信队列。详见 `07_EVENT_SPEC.md`。

### 2.11 Infrastructure（`infrastructure.api`：CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| CommunicationAPI.send | message: Message | ack: bool | code:SEND_FAILED | Message.ttl 跳数 | 2 次 | v1 |
| NodeRegistryAPI.register | node: NodeRef | ack: bool | code:DUPLICATE | 5s | 不重试 | v1 |
| NodeRegistryAPI.list | filter: dict | list[NodeRef] | — | 5s | 不重试 | v1 |
| SyncAPI.sync | packet: SyncPacket | SyncStatus | code:CONFLICT | 30s | 2 次 | v1 |
| DeploymentAPI.deploy | target, config | ack: bool | code:DEPLOY_FAILED | 120s | 1 次 | v1 |

### 2.12 Observability（`observability.api`：MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| MonitorAPI.metrics | scope: str | dict | — | 10s | 1 次 | v1 |
| MonitorAPI.alert | rule: dict | ack: bool | code:INVALID_RULE | 5s | 不重试 | v1 |
| TraceAPI.trace | trace_id: str | list[Event] | code:NOT_FOUND | 10s | 1 次 | v1 |
| ReplayAPI.replay | session: str | 时间线流 | code:NOT_FOUND | 30s | 不重试 | v1 |
| BenchmarkAPI.run | suite: str | result: dict | code:BENCH_FAILED | 600s | 不重试 | v1 |
| EvaluationAPI.evaluate | session: str | score: dict | code:NO_DATA | 60s | 1 次 | v1 |
| VisualizationAPI.render | data: dict | view 状态 | code:INVALID_DATA | 10s | 不重试 | v1 |

### 2.13 Data（`data.api`：DatasetAPI · ModelSchemaAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| DatasetAPI.load | name, version | dataset | code:NOT_FOUND | 60s | 1 次 | v1 |
| ModelSchemaAPI.register | schema: dict | ack: bool | code:INVALID_SCHEMA | 10s | 不重试 | v1 |

### 2.14 Tooling（`tooling.api`：ConfigAPI · ScriptAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| ConfigAPI.get | key: str | value: Any | code:NOT_FOUND | 5s | 不重试 | v1 |
| ScriptAPI.run | name: str, args | result: dict | code:SCRIPT_FAILED | 视脚本 | 不重试 | v1 |

---

## 3. REST 端点（经 gateway）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/sessions | 创建会话 |
| GET | /api/v1/sessions/{id} | 查询会话 |
| POST | /api/v1/tasks | 创建任务（触发 planner） |
| GET | /api/v1/tasks/{id} | 查询任务状态 |
| POST | /api/v1/tasks/{id}/cancel | 取消任务 |
| GET | /api/v1/agents/memory/{session} | 读取记忆 |
| POST | /api/v1/agents/memory/{session} | 写入记忆 |
| GET | /api/v1/graph | 获取动态图 |
| GET | /api/v1/agents | Agent 列表 |
| POST | /api/v1/agents/action/execution/tools/{name}/invoke | 调用工具 |
| GET | /api/v1/metrics | 指标 |
| GET | /api/v1/observability/inspect/replay/{session} | 回放时间线 |

---

## 4. WebSocket & SSE & gRPC

- **WebSocket**：`ws://host/ws/v1/stream?session=...`；消息为 `protocol/message.py` 的 `Message` 信封；事件类型见 `07_EVENT_SPEC.md`。
- **SSE**：`GET /api/v1/events?stream=...` → `text/event-stream`；推送 AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate。
- **gRPC（内部）**：`aegis.protocol.v1` 服务：`SchedulerService`/`RouterService`/`MemoryService`/`ToolService`；`.proto` 由 `protocol/` 类型生成，单一可信源。

---

## 5. 版本与兼容

- URL 版本 `/v1/`；字段新增可选；废弃先 deprecated 一个版本。
- `api/` 接口新增方法：优先作为可选方法/新接口，避免破坏既有实现。
- `api/` 签名变更：major bump + CHANGELOG + 通知依赖方。
