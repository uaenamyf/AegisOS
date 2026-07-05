# 05_API_SPEC.md — API 接口契约规范

> 上游：`00_PROJECT_SPEC.md`、`04_PROTOCOL_SPEC.md`。本文件定义全系统 API Contract。
> 模块间解耦：每个域通过 `api/` 子包暴露 `typing.Protocol` 接口（共 **27 个**），参数/返回值一律 `protocol/` 类型。
> `api/` 签名变更 = 破坏性变更（major bump + CHANGELOG + 通知依赖方）。
> **内聚原则**：`api/` 只暴露外部域真正需要调用的接口。Agent 域内部的规划（plan/route/schedule）与感知（reason/reflect）不对外暴露——后端只调 `RuntimeAPI.run(task)`，Agent 域内部自行编排。

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

### 2.1 Frontend

> 前端为纯 SPA（React + TypeScript），不对外暴露 Python API。前端经 `backend.api` REST/WS/SSE 接口与后端通信。前端内部架构（Controller-Service-Lib + Views）位于 `frontend/src/`。

### 2.2 Backend（`backend.api`：SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| SessionAPI.create_session | user_id: str | session_id: str | code:AUTH_FAILED | 10s | 不重试 | v1 |
| SessionAPI.get_session | session_id: str | session: dict | code:NOT_FOUND | 5s | 不重试 | v1 |
| SessionAPI.close_session | session_id: str | bool | code:NOT_FOUND | 5s | 不重试 | v1 |
| TaskAPI.create_task | goal: str, session_id: str | task: Task | code:INVALID_GOAL | 30s | 不重试（异步触发 RuntimeAPI.submit） | v1 |
| TaskAPI.get_task | task_id: str | task: Task | code:NOT_FOUND | 5s | 不重试 | v1 |
| TaskAPI.list_tasks | session_id: str | list[Task] | — | 5s | 不重试 | v1 |
| TaskAPI.cancel_task | task_id: str | bool | code:NOT_CANCELLABLE | 10s | 不重试 | v1 |
| MemoryGatewayAPI.read_memory | session_id: str | MemoryPacket | code:NOT_FOUND | 10s | 1 次 | v1 |
| MemoryGatewayAPI.write_memory | session_id: str, packet: MemoryPacket | bool | code:WRITE_FAILED | 10s | 2 次 | v1 |
| GraphAPI.get_graph | — | Graph | code:UNAVAILABLE | 10s | 1 次 | v1 |
| EventStreamAPI.stream_events | session_id: str, handler | Event 流 (SSE/WS) | code:STREAM_CLOSED | — | 自动重连 | v1 |

> **Graph 数据来源**：后端通过 `EventBusAPI.subscribe("graph.update", handler)` 订阅 `GraphUpdate` 事件维护图缓存，`GraphAPI.get_graph` 返回缓存快照。不暴露 aegisos_agents 内部 topology。
> **EventStreamAPI**：后端通过 `EventBusAPI.subscribe` 订阅事件流，经 SSE/WS 推送前端。后端**只用 subscribe**，不 publish（事件由 Agent 产生）。

### 2.3 Agent（`aegisos_agents.api`：AgentRegistryAPI · ExecutionAPI · RuntimeAPI）

> PlanningAPI（plan/route/schedule）和 PerceptionAPI（reason/reflect）已**收归 aegisos_agents 域内部**，不再对外暴露。后端只调 `RuntimeAPI.submit(task)` 或 `RuntimeAPI.run(agent_id, task)`，agents 域内部自行 plan→route→schedule→execute→reflect。Plan(DAG) 通过 `Task.plan` 字段 + 事件流回传后端展示。

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| AgentRegistryAPI.list_agents | filter: dict | list[Agent] | — | 5s | 不重试 | v1 |
| AgentRegistryAPI.register | agent: Agent | ack: bool | code:DUPLICATE | 5s | 不重试 | v1 |
| AgentRegistryAPI.get | agent_id: str | Agent | code:NOT_FOUND | 5s | 不重试 | v1 |
| RuntimeAPI.submit | task: Task | Task（含 agent_id + status） | code:SUBMIT_FAILED | 30s | 不重试 | v1 |
| RuntimeAPI.run | agent_id: str, task: Task | result: Any | code:AGENT_NOT_FOUND / code:EXEC_FAILED | task.retry | 按 Task.retry | v1 |
| RuntimeAPI.stop | agent_id: str | bool | code:NOT_RUNNING | 10s | 不重试 | v1 |
| RuntimeAPI.heartbeat | agent_id: str | Heartbeat | code:OFFLINE | 5s | 3 次 | v1 |

> **submit vs run 分工**：
> - `submit(task)`：不指定 agent，由 aegisos_agents 域内部路由决定。用于 `POST /tasks`（用户只提供 goal）。
> - `run(agent_id, task)`：指定 agent 直调。用于 `POST /aegisos_agents/{id}/invoke`（IDE 直接调用特定 Agent）。
> - `AgentRegistryAPI` 只管注册/查询，**不含 invoke**（执行统一走 RuntimeAPI）。

### 2.4 Memory（`aegisos_agents.api.MemoryAPI`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| MemoryAPI.read | query: dict | MemoryPacket | code:NOT_FOUND | 10s | 1 次 | v1 |
| MemoryAPI.write | packet: MemoryPacket | bool | code:WRITE_FAILED | 10s | 2 次（幂等） | v1 |
| MemoryAPI.retrieve | query: dict | list | code:RETRIEVE_FAILED | 10s | 1 次 | v1 |

> 写入幂等（packet id 去重）；checkpoint/snapshot 恢复。

> **Scheduler / Planner / Router 已收归 aegisos_agents 域内部**（`aegisos_agents/planning/engine/`），不作为公共 API 暴露。后端通过 `RuntimeAPI.run(task)` 触发，agents 域内部完成 plan→route→schedule。调度策略：多级优先级队列 + DAG 拓扑序 + 资源 + 信任度；抢占；指数退避；超时熔断；老化反饥饿。Plan/Route/Schedule 经 `Task.plan` 字段 + `GraphUpdate` 事件回传。

### 2.5 Tool（`aegisos_agents.api.ExecutionAPI` + `aegisos_agents/action/execution/tools/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| ExecutionAPI.execute | call: ToolCall | result: ToolResult | code:TOOL_FAILED / code:PERMISSION_DENIED | call.timeout (默认 30s) | 不重试（由上层 Task.retry 决定） | v1 |

> **直调场景**：`POST /api/v1/tools/{name}/invoke` 供 IDE 用户直接调用工具（不经 Agent 编排），如执行代码、搜索文档。此为受限的辅助场景，**主流程仍经 RuntimeAPI.submit→Agent 内部调工具**。沙箱执行 + 权限校验 + 资源限制；每次调用发 `ToolCall`/`ToolFinish` 事件。`register_tool` 为内部操作（工具在 aegisos_agents 域初始化时注册），不对外暴露。

### 2.6 Runtime（`aegisos_agents.api.RuntimeAPI` + `aegisos_agents/tools/runtime/`）

> **核心入口**：后端通过 `RuntimeAPI.submit(task)`（不指定 agent）或 `RuntimeAPI.run(agent_id, task)`（指定 agent）触发智能体执行，agents 域内部完成 plan→route→schedule→receive→think→tool→reflect→respond 全流程。

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| RuntimeAPI.submit | task: Task | Task（含 agent_id + status） | code:SUBMIT_FAILED | 30s | 不重试 | v1 |
| RuntimeAPI.run | agent_id: str, task: Task | result: Any | code:AGENT_NOT_FOUND / code:EXEC_FAILED | task.retry | 按 Task.retry | v1 |
| RuntimeAPI.stop | agent_id: str | bool | code:NOT_RUNNING | 10s | 不重试 | v1 |
| RuntimeAPI.heartbeat | agent_id: str | Heartbeat | code:OFFLINE | 5s | 3 次 | v1 |

### 2.7 EventBus（`aegisos_agents.api.EventBusAPI` + `aegisos_agents/planning/engine/eventbus/`）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| publish | event: Event | ack: bool | code:PUBLISH_FAILED | 5s | 3 次（至少一次） | v1 |
| subscribe | topic: str, handler | subscription_id: str | code:INVALID_TOPIC | 5s | 不重试 | v1 |
| unsubscribe | subscription_id: str | bool | code:NOT_FOUND | 5s | 不重试 | v1 |

> 至少一次投递 + `event_id` 幂等去重；同 `task_id` 保序；失败 N 次进死信队列。详见 `07_EVENT_SPEC.md`。

### 2.8 Infrastructure（`infrastructure.api`：CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| CommunicationAPI.send | message: Message | ack: bool | code:SEND_FAILED | Message.ttl 跳数 | 2 次 | v1 |
| NodeRegistryAPI.register | node: NodeRef | ack: bool | code:DUPLICATE | 5s | 不重试 | v1 |
| NodeRegistryAPI.list | filter: dict | list[NodeRef] | — | 5s | 不重试 | v1 |
| SyncAPI.sync | packet: SyncPacket | SyncStatus | code:CONFLICT | 30s | 2 次 | v1 |
| DeploymentAPI.deploy | target, config | ack: bool | code:DEPLOY_FAILED | 120s | 1 次 | v1 |

### 2.9 Observability（`observability.api`：MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| MonitorAPI.metrics | scope: str | dict | — | 10s | 1 次 | v1 |
| MonitorAPI.alert | rule: dict | ack: bool | code:INVALID_RULE | 5s | 不重试 | v1 |
| TraceAPI.trace | trace_id: str | list[Event] | code:NOT_FOUND | 10s | 1 次 | v1 |
| ReplayAPI.replay | session: str | 时间线流 | code:NOT_FOUND | 30s | 不重试 | v1 |
| BenchmarkAPI.run | suite: str | result: dict | code:BENCH_FAILED | 600s | 不重试 | v1 |
| EvaluationAPI.evaluate | session: str | score: dict | code:NO_DATA | 60s | 1 次 | v1 |
| VisualizationAPI.render | data: dict | view 状态 | code:INVALID_DATA | 10s | 不重试 | v1 |

### 2.10 Data（`data.api`：DatasetAPI · ModelSchemaAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| DatasetAPI.load | name, version | dataset | code:NOT_FOUND | 60s | 1 次 | v1 |
| ModelSchemaAPI.register | schema: dict | ack: bool | code:INVALID_SCHEMA | 10s | 不重试 | v1 |

### 2.11 Tooling（`tooling.api`：ConfigAPI · ScriptAPI）

| API | Request | Response | Error | Timeout | Retry | Version |
|-----|---------|----------|-------|---------|-------|---------|
| ConfigAPI.get | key: str | value: Any | code:NOT_FOUND | 5s | 不重试 | v1 |
| ScriptAPI.run | name: str, args | result: dict | code:SCRIPT_FAILED | 视脚本 | 不重试 | v1 |

### 2.12 DI 端口（`aegisos_agents.api.ports`：反向依赖反转，由后端实现并注入）

> 智能体运行时回调后端能力的端口。定义在 `aegisos_agents/api/ports.py`（agents 域内），由 `backend/services/agent/ports.py` 实现，组合根 `backend/composition.py` 注入。详见 `plans/13_FRONTEND_BACKEND_PLAN.md` §3.2、`10_INTERFACE_BOUNDARY_SPEC.md` §5。

| 端口 | 方法 | Request | Response | Error | Version |
|------|------|---------|----------|-------|---------|
| `PersistencePort` | save_task_result | task_id: str, result: dict | bool | code:SAVE_FAILED | v1 |
| `PersistencePort` | save_artifact | task_id: str, name: str, content: bytes | str (artifact_id) | code:SAVE_FAILED | v1 |
| `SessionPort` | get_session | session_id: str | dict | code:NOT_FOUND | v1 |
| `SessionPort` | get_user_context | session_id: str | dict | code:NOT_FOUND | v1 |
| `TaskUpdatePort` | update_status | task_id: str, status: TaskStatus | bool | code:UPDATE_FAILED | v1 |

> 端口约束：仅用于「智能体必需的后端能力」；凡能走 EventBus 的交互不设端口；新增端口须在此登记 + CHANGELOG。

---

## 3. REST 端点（经 gateway）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/health | 健康检查 |
| POST | /api/v1/sessions | 创建会话 |
| GET | /api/v1/sessions/{id} | 查询会话 |
| DELETE | /api/v1/sessions/{id} | 关闭会话 |
| POST | /api/v1/tasks | 创建任务（→ RuntimeAPI.submit，async） |
| GET | /api/v1/tasks | 列任务（按 session 过滤） |
| GET | /api/v1/tasks/{id} | 查询任务状态 |
| POST | /api/v1/tasks/{id}/cancel | 取消任务 |
| GET | /api/v1/agents | Agent 列表 |
| GET | /api/v1/aegisos_agents/{id} | Agent 详情 |
| POST | /api/v1/aegisos_agents/{id}/invoke | 直调 Agent（→ RuntimeAPI.run，指定 agent） |
| GET | /api/v1/memory/{session} | 读取记忆 |
| POST | /api/v1/memory/{session} | 写入记忆 |
| GET | /api/v1/graph | 获取动态图（EventBus 订阅缓存） |
| POST | /api/v1/tools/{name}/invoke | 直接调用工具（不经 Agent 编排） |
| GET | /api/v1/metrics | 指标 |
| GET | /api/v1/replay/{session} | 回放时间线 |

> **路径规范**：REST 路径不暴露内部目录结构（如 ~~`/aegisos_agents/action/execution/tools/`~~ → `/tools/`，~~`/aegisos_agents/memory/`~~ → `/memory/`，~~`/observability/inspect/replay/`~~ → `/replay/`）。

---

## 4. WebSocket & SSE & gRPC

- **WebSocket**：`ws://host/ws/v1/stream?session=...`；消息为 `protocol/message.py` 的 `Message` 信封；事件类型见 `07_EVENT_SPEC.md`。
- **SSE**：`GET /api/v1/events?stream=...` → `text/event-stream`；推送 AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate。后端通过 `EventBusAPI.subscribe` 订阅事件并推送，**只用 subscribe，不 publish**。
- **gRPC（内部，待 P5 后评估）**：Scheduler/Router 已收归 aegisos_agents 域内部，不再作为跨域 gRPC 服务。若未来需要跨进程调用，仅保留 `MemoryService`/`ToolService`；`.proto` 由 `protocol/` 类型生成，单一可信源。

---

## 5. 版本与兼容

- URL 版本 `/v1/`；字段新增可选；废弃先 deprecated 一个版本。
- `api/` 接口新增方法：优先作为可选方法/新接口，避免破坏既有实现。
- `api/` 签名变更：major bump + CHANGELOG + 通知依赖方。
