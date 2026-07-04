# backend/ 模块实现文档

> 应用层 — FastAPI + SQLAlchemy(async) + aiosqlite，Controller-Service-Mapper 三层 + Gateway 网关。

📁 模块规范：[`AGENT.md`](AGENT.md) · 接口规范：[`05_API_SPEC.md`](../developer/specs/05_API_SPEC.md)

---

## 架构

```
backend/src/
├── main.py              FastAPI 入口（CORS + TraceMiddleware + lifespan）
├── composition.py       DI 组合根（装配 DB + 仓储 + 服务 + 14 Agent 注册）
├── gateway/             网关层（鉴权 + 中间件 + 路由聚合）
│   ├── routes.py        /api/v1 前缀 + verify_api_key
│   ├── auth.py          X-API-Key header 校验
│   └── middleware.py    TraceMiddleware（请求追踪 ID）
├── controllers/         控制器层（参数校验 + 响应封装）
│   ├── api/             REST API（10 个端点模块）
│   ├── sse/             Server-Sent Events
│   ├── ws/              WebSocket
│   └── schemas/         Pydantic 请求/响应模型
├── services/            业务逻辑层
├── mappers/             数据映射层（SQLAlchemy + aiosqlite）
│   ├── database.py      引擎 + 会话工厂
│   ├── entities.py      ORM 实体
│   └── repositories.py  仓储模式
└── api/                 公共接口（5 个 Protocol）
```

---

## 已实现

### 入口 & 网关

| 文件 | 功能 |
|------|------|
| [`main.py`](src/main.py) | `create_app()` → FastAPI；CORS(origins: localhost:5173)；TraceMiddleware；lifespan(DB init/shutdown) |
| [`gateway/routes.py`](src/gateway/routes.py) | `APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])` |
| [`gateway/auth.py`](src/gateway/auth.py) | `verify_api_key()` — 校验 `X-API-Key: aegis-dev-key` |
| [`gateway/middleware.py`](src/gateway/middleware.py) | `TraceMiddleware` — 每请求注入 trace_id |

### REST API 端点

| 端点 | 方法 | 路径 | 说明 |
|------|------|------|------|
| [`health.py`](src/controllers/api/health.py) | GET | `/api/v1/health` | 健康检查（**无鉴权**） |
| [`sessions.py`](src/controllers/api/sessions.py) | POST | `/api/v1/sessions` | 创建会话 |
| | GET | `/api/v1/sessions` | 列出会话 |
| [`tasks.py`](src/controllers/api/tasks.py) | POST | `/api/v1/tasks` | 创建任务 |
| | GET | `/api/v1/tasks` | 列出任务 |
| | POST | `/api/v1/tasks/{id}/cancel` | 取消任务 |
| [`agents.py`](src/controllers/api/agents.py) | GET | `/api/v1/agents` | 列出 Agent（14 个） |
| | POST | `/api/v1/agents/{id}/invoke` | 调用 Agent |
| [`graph.py`](src/controllers/api/graph.py) | GET | `/api/v1/graph` | 获取拓扑图 |
| [`memory.py`](src/controllers/api/memory.py) | GET | `/api/v1/memory` | 读取记忆 |
| | POST | `/api/v1/memory` | 写入记忆 |
| [`tools.py`](src/controllers/api/tools.py) | POST | `/api/v1/tools/invoke` | 调用工具 |
| [`metrics.py`](src/controllers/api/metrics.py) | GET | `/api/v1/metrics` | 系统指标 |
| [`replay.py`](src/controllers/api/replay.py) | GET | `/api/v1/replay/{session_id}` | 回放会话 |

### 实时通信

| 文件 | 协议 | 路径 | 说明 |
|------|------|------|------|
| [`sse/events.py`](src/controllers/sse/events.py) | SSE | `GET /api/v1/events/stream` | 服务器推送事件流 |
| [`ws/stream.py`](src/controllers/ws/stream.py) | WebSocket | `WS /ws/v1/stream` | 双向实时流 |

### Service 层

| 文件 | 功能 |
|------|------|
| [`services/session.py`](src/services/session.py) | 会话管理（创建/列表/获取） |
| [`services/task.py`](src/services/task.py) | 任务管理（创建/列表/取消/状态更新） |
| [`services/agent.py`](src/services/agent.py) | Agent 管理（注册列表/调用执行） |
| [`services/graph.py`](src/services/graph.py) | 拓扑图服务 |
| [`services/memory.py`](src/services/memory.py) | 记忆读写服务 |
| [`services/ports.py`](src/services/ports.py) | Service 层端口定义 |

### Mapper 层（持久化）

| 文件 | 功能 |
|------|------|
| [`mappers/database.py`](src/mappers/database.py) | `create_engine()` AsyncEngine + `async_sessionmaker`（aiosqlite） |
| [`mappers/entities.py`](src/mappers/entities.py) | ORM 实体：`Base` · `SessionEntity` · `TaskEntity` |
| [`mappers/repositories.py`](src/mappers/repositories.py) | 仓储模式：`SessionRepository` · `TaskRepository` |
| [`mappers/converters.py`](src/mappers/converters.py) | Domain ↔ Entity 转换：`task_to_entity()` · `entity_to_task()` |

### DI 组合根

| 文件 | 功能 |
|------|------|
| [`composition.py`](src/composition.py) | `get_composition()` → 装配全部依赖：DB engine → repositories → services → controllers → **14 Agent 注册**（3 基础 + 11 攻防）+ MockRuntime |

**14 Agent 注册**：
- 基础 3 个：`coder` · `researcher` · `docwriter`
- 红队 4 个：`recon` · `vuln_correlator` · `exploit_planner` · `lateral_move`
- 蓝队 5 个：`detector` · `triage` · `threat_hunt` · `ir_planner` · `forensics`
- 紫队 2 个：`critic` · `reviewer`

### Schemas（Pydantic 模型）

| 文件 | 内容 |
|------|------|
| [`controllers/schemas/__init__.py`](src/controllers/schemas/__init__.py) | `CreateSessionRequest` · `CreateTaskRequest` · `InvokeAgentRequest` · `*Response` 模型 |

### 公共接口（`api/`）

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
