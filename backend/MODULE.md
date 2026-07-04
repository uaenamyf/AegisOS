# backend/ 模块实现文档

> 应用层 — FastAPI + SQLAlchemy(async) + aiosqlite，Router-Service-Repository-Model 四层 + Core 网关入口。

📁 模块规范：[`AGENT.md`](AGENT.md) · 接口规范：[`05_API_SPEC.md`](../developer/specs/05_API_SPEC.md)

---

## 架构

```
backend/
├── main.py              FastAPI 入口（CORS + TraceMiddleware + lifespan）
├── api.py               公共接口（5 个 Protocol）
├── core/                核心层（DI 组合根 + 鉴权 + 中间件 + 路由聚合）
│   ├── composition.py   DI 组合根（装配 DB + 仓储 + 服务 + 14 Agent 注册）
│   ├── routes.py        /api/v1 前缀 + verify_api_key 路由聚合
│   ├── auth.py          X-API-Key header 校验
│   └── middleware.py     TraceMiddleware（请求追踪 ID）
├── routers/             路由层（参数校验 + 响应封装）
│   ├── __init__.py      聚合所有 REST 子路由
│   ├── health.py        健康检查（无鉴权）
│   ├── sessions.py      会话管理端点
│   ├── tasks.py         任务管理端点
│   ├── agents.py        Agent 管理端点
│   ├── memory.py        记忆读写端点
│   ├── graph.py         拓扑图端点
│   ├── tools.py         工具调用端点
│   ├── metrics.py       系统指标端点
│   ├── replay.py        回放端点
│   ├── sse.py           Server-Sent Events
│   └── ws.py            WebSocket
├── services/            业务逻辑层
│   ├── session_service.py    会话管理
│   ├── task_service.py       任务管理
│   ├── agent_service.py      Agent 管理
│   ├── memory_service.py     记忆读写
│   ├── graph_service.py      拓扑图服务
│   └── di_ports.py           DI 端口实现
├── repositories/        仓储层（SQLAlchemy + aiosqlite）
│   ├── database.py      引擎 + 会话工厂
│   └── repositories.py  仓储模式（Session/Task）
├── models/              模型层
│   ├── entities.py      ORM 实体
│   └── converters.py    Domain ↔ Entity 转换器
├── schemas/             Pydantic v2 请求/响应 Schema
└── mocks/               agents.api 端口的 mock 实现
    ├── __init__.py      barrel 导出
    ├── agent_registry.py  MockAgentRegistry + 攻防 Agent specs
    ├── runtime.py        MockRuntime + 攻防 Agent 分发表
    ├── cyber_provider.py _CyberMockProvider + 预置响应
    ├── memory.py         MockMemoryAPI
    ├── execution.py      MockExecutionAPI
    └── event_bus.py      MockEventBusAPI
```

---

## 已实现

### 入口 & 核心

| 文件 | 功能 |
|------|------|
| [`main.py`](main.py) | `create_app()` → FastAPI；CORS(origins: localhost:5173)；TraceMiddleware；lifespan(DB init/shutdown) |
| [`core/routes.py`](core/routes.py) | `APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])` |
| [`core/auth.py`](core/auth.py) | `verify_api_key()` — 校验 `X-API-Key: aegis-dev-key` |
| [`core/middleware.py`](core/middleware.py) | `TraceMiddleware` — 每请求注入 trace_id |

### REST API 端点

| 端点 | 方法 | 路径 | 说明 |
|------|------|------|------|
| [`health.py`](routers/health.py) | GET | `/api/v1/health` | 健康检查（**无鉴权**） |
| [`sessions.py`](routers/sessions.py) | POST | `/api/v1/sessions` | 创建会话 |
| | GET | `/api/v1/sessions` | 列出会话 |
| [`tasks.py`](routers/tasks.py) | POST | `/api/v1/tasks` | 创建任务 |
| | GET | `/api/v1/tasks` | 列出任务 |
| | POST | `/api/v1/tasks/{id}/cancel` | 取消任务 |
| [`agents.py`](routers/agents.py) | GET | `/api/v1/agents` | 列出 Agent（14 个） |
| | POST | `/api/v1/agents/{id}/invoke` | 调用 Agent |
| [`graph.py`](routers/graph.py) | GET | `/api/v1/graph` | 获取拓扑图 |
| [`memory.py`](routers/memory.py) | GET | `/api/v1/memory` | 读取记忆 |
| | POST | `/api/v1/memory` | 写入记忆 |
| [`tools.py`](routers/tools.py) | POST | `/api/v1/tools/invoke` | 调用工具 |
| [`metrics.py`](routers/metrics.py) | GET | `/api/v1/metrics` | 系统指标 |
| [`replay.py`](routers/replay.py) | GET | `/api/v1/replay/{session_id}` | 回放会话 |

### 实时通信

| 文件 | 协议 | 路径 | 说明 |
|------|------|------|------|
| [`sse.py`](routers/sse.py) | SSE | `GET /api/v1/events/stream` | 服务器推送事件流 |
| [`ws.py`](routers/ws.py) | WebSocket | `WS /ws/v1/stream` | 双向实时流 |

### Service 层

| 文件 | 功能 |
|------|------|
| [`services/session_service.py`](services/session_service.py) | 会话管理（创建/列表/获取） |
| [`services/task_service.py`](services/task_service.py) | 任务管理（创建/列表/取消/状态更新） |
| [`services/agent_service.py`](services/agent_service.py) | Agent 管理（注册列表/调用执行） |
| [`services/graph_service.py`](services/graph_service.py) | 拓扑图服务 |
| [`services/memory_service.py`](services/memory_service.py) | 记忆读写服务 |
| [`services/di_ports.py`](services/di_ports.py) | DI 端口实现（Persistence/Session/TaskUpdate） |

### Repository 层（持久化）

| 文件 | 功能 |
|------|------|
| [`repositories/database.py`](repositories/database.py) | `create_engine()` AsyncEngine + `async_sessionmaker`（aiosqlite） |
| [`repositories/repositories.py`](repositories/repositories.py) | 仓储模式：`SessionRepository` · `TaskRepository` |

### Model 层

| 文件 | 功能 |
|------|------|
| [`models/entities.py`](models/entities.py) | ORM 实体：`Base` · `SessionEntity` · `TaskEntity` |
| [`models/converters.py`](models/converters.py) | Domain ↔ Entity 转换：`task_to_entity()` · `entity_to_task()` |

### DI 组合根

| 文件 | 功能 |
|------|------|
| [`core/composition.py`](core/composition.py) | `get_composition()` → 装配全部依赖：DB engine → repositories → services → routers → **14 Agent 注册**（3 基础 + 11 攻防）+ MockRuntime |

**14 Agent 注册**：
- 基础 3 个：`coder` · `researcher` · `docwriter`
- 红队 4 个：`recon` · `vuln_correlator` · `exploit_planner` · `lateral_move`
- 蓝队 5 个：`detector` · `triage` · `threat_hunt` · `ir_planner` · `forensics`
- 紫队 2 个：`critic` · `reviewer`

### Schemas（Pydantic 模型）

| 文件 | 内容 |
|------|------|
| [`schemas/__init__.py`](schemas/__init__.py) | `CreateSessionRequest` · `CreateTaskRequest` · `InvokeAgentRequest` · `*Response` 模型 |

### 公共接口（`api.py`）

| 接口 | 方法 |
|------|------|
| `SessionAPI` | `create()` · `list()` · `get(id)` |
| `TaskAPI` | `create()` · `list()` · `cancel(id)` |
| `MemoryGatewayAPI` | `read(query)` · `write(packet)` |
| `GraphAPI` | `get()` |
| `EventStreamAPI` | `stream()` |

---

## API 鉴权

```bash
curl -H "X-API-Key: aegis-dev-key" http://localhost:8000/api/v1/agents
```

所有 `/api/v1/*` 端点需 `X-API-Key: aegis-dev-key` header（`/health` 除外）。

---

## 未实现

- 🔲 攻防端点 `/api/v1/range/*`（靶场启停/拓扑/红队攻击/攻击链/防御）
- 🔲 `/api/v1/threat/attack-techniques`（ATT&CK 技术列表）
- 🔲 Task payload 字段（当前 MockRuntime.run() 用 getattr 从 goal 解析）
