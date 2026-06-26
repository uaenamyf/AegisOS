# API_SPEC.md — API 接口规范

> 前后端 API、WebSocket、SSE、gRPC、内部 RPC 接口规范。所有外部入口经 backend/gateway/。模块间通过各域 `api/` 子包解耦调用。

## 0. 模块间 API 解耦
每个域通过 `api/` 子包暴露公共接口（Python Protocol 类型），其他模块只通过 `from {domain}.api import XxxAPI` 调用，禁止直接导入内部实现子包。

| 域 | api 包 | 暴露接口 |
|----|--------|----------|
| agents/ | `agents.api` | AgentRegistryAPI · MemoryAPI · PlanningAPI · ExecutionAPI · PerceptionAPI · EventBusAPI · RuntimeAPI |
| backend/ | `backend.api` | SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI |
| frontend/ | `frontend.api` | ViewAPI · InteractionAPI · ThemeAPI |
| infrastructure/ | `infrastructure.api` | CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI |
| observability/ | `observability.api` | MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI |
| data/ | `data.api` | DatasetAPI · ModelSchemaAPI |
| tooling/ | `tooling.api` | ConfigAPI · ScriptAPI |

- 接口参数/返回值一律使用 `protocol/` 类型。
- `api/` 签名变更属破坏性变更，需在 CHANGELOG 标注。
- 实现由各域内部注入（依赖反转），便于 mock 测试。

## 1. 传输协议
| 协议 | 用途 |
|------|------|
| REST (HTTP) | 同步请求：任务创建、查询、配置 |
| WebSocket | 双向实时：Agent 状态、协作消息 |
| SSE | 单向流：事件推送、日志流 |
| gRPC | 内部高性能 RPC：子系统间调用 |

## 2. 统一约定
- 所有入口：`/api/v1/...`，经 gateway 鉴权 + 限流。
- 请求/响应体使用 `protocol/` 类型，禁止裸 JSON 自造结构。
- 透传 `X-Trace-Id`、`X-Session-Id`、`X-Task-Id`。
- 错误统一：`{code, message, trace_id}`。

## 3. REST 端点
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

## 4. WebSocket
- `ws://host/ws/v1/stream?session=...`
- 消息为 `protocol/message.py` 的 Message 信封。
- 事件类型见 EVENT_SPEC.md。

## 5. SSE
- `GET /api/v1/events?stream=...` 返回 `text/event-stream`。
- 用于前端实时推送 AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate。

## 6. gRPC（内部）
- `aegos.protocol.v1` 服务：SchedulerService / RouterService / MemoryService / ToolService。
- `.proto` 由 `protocol/` 类型生成，保持单一可信源。

## 7. 版本与兼容
- URL 版本 `/v1/`；字段新增可选；废弃先 deprecated 一个版本。
