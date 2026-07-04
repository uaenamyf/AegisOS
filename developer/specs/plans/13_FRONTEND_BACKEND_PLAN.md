# 13_FRONTEND_BACKEND_PLAN.md — 前后端开发全流程计划

> 上游：`00_PROJECT_SPEC.md`、`05_API_SPEC.md`、`10_INTERFACE_BOUNDARY_SPEC.md`、`12_TECH_STACK_SPEC.md`。
> 本文件是前端、后端开发全流程的权威计划，并定义「后端暴露接口给智能体模块以调用智能体」的双向架构。
> 存放位置：`developer/specs/plans/`（计划类规范独立子目录）。

---

## 1. 目标与范围

- **后端**：基于 FastAPI 实现 `gateway→controllers→services→mappers` 全栈，暴露 REST/WS/SSE，编排智能体，并提供反向 DI 端口供智能体回调。
- **前端**：React 18 + TS + Vite 实现 `controllers→services→mappers→views`，经 backend gateway 通信，TS 类型由 `protocol/` 脚本生成。
- **后端↔智能体**：正向（后端经 `agents.api` 编排智能体）+ 反向（智能体经 DI 端口回调后端，不破坏 Import 铁律）。

---

## 2. 技术栈补充（已同步写入 `12_TECH_STACK_SPEC.md`）

| 层 | 新增依赖 | 版本约束 | 用途 |
|----|----------|----------|------|
| 后端 | FastAPI | **>=0.110** | REST/WS/SSE + Pydantic 原生 + OpenAPI |
| 后端 | Uvicorn | **>=0.29** | ASGI server |
| 后端 | httpx | **>=0.27** | 测试客户端 / 外部 HTTP 调用 |
| 后端 | SQLAlchemy + aiosqlite | **>=2.0** / **>=0.20** | ORM + 异步 SQLite（dev）；生产可换 PostgreSQL |
| 前端 | Zustand | **>=4.5** | 轻量全局状态 |
| 前端 | Vitest | **>=1.6** | 单元测试 |
| 前端 | Playwright | **>=1.40** | E2E 测试 |
| 工具 | `tooling/scripts/gen_ts_types.py` | — | Pydantic → TypeScript 类型生成 |

---

## 3. 架构：后端↔智能体双向调用设计（核心）

### 3.1 正向：后端编排智能体（Forward，符合现有依赖方向）

```
Client → POST /api/v1/tasks → gateway → controllers/api → services/task
  → services/agent → agents.api.RuntimeAPI.submit(task)  [async]
       (agents 域内部自行编排：plan→route→schedule→receive→think→tool→reflect→respond)
  → emit AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate → EventBus
backend 订阅 EventBus（subscribe） → SSE/WS 推送前端（EventStreamAPI）
Plan(DAG) 通过 Task.plan 字段 + GraphUpdate 事件回传后端展示
```

> **内聚原则**：后端不逐步调 plan→route→schedule，只调 `RuntimeAPI.submit(task)`（不指定 agent，由 agents 域路由决定），agents 域内部完成全部认知编排。PlanningAPI/PerceptionAPI 不对外暴露（收归 `agents/planning/engine/` 和 `agents/perception/` 内部）。
> **submit vs run**：`submit(task)` 用于 `POST /tasks`（用户只提供 goal）；`run(agent_id, task)` 用于 `POST /agents/{id}/invoke`（IDE 直调特定 Agent）。

新增直调端点：`POST /api/v1/agents/{id}/invoke` → `RuntimeAPI.run(agent_id, task)`（指定 agent，同步返回，简单场景）。

### 3.2 反向：智能体回调后端（Reverse，依赖反转 DI）

**问题**：`agents` 禁止 `import backend`（逆向依赖，见 `03_IMPORT_SPEC.md` F5）。
**解法**：在 `agents/api/ports.py` 定义「端口」Protocol（消费侧接口），由后端实现并注入。`agents` 依赖自己域内的端口抽象，后端 import `agents.api.ports` 并实现端口 = 经典 DIP（依赖反转），零逆向 import。

```
┌─────────────────────────────────────────────────────────┐
│  agents/api/ports.py  （定义端口：PersistencePort 等）    │
│       ↑ 消费（同域 import，合规）        ↑ 实现（正向 import，合规）│
│  agents/tools/runtime               backend/services/agent/ports.py │
│  agents/action/*                    （实现 PersistencePort 等）       │
└─────────────────────────────────────────────────────────┘
         组合根 backend/composition.py 负责注入
```

`agents/api/ports.py` 定义（见已创建文件）：
- `PersistencePort`：`save_task_result(task_id, result)→bool`、`save_artifact(task_id, name, content)→str`
- `SessionPort`：`get_session(session_id)→dict`、`get_user_context(session_id)→dict`
- `TaskUpdatePort`：`update_status(task_id, status)→bool`

**依赖校验**：

| import 关系 | 方向 | 合规 | 理由 |
|-------------|------|------|------|
| `agents.* → agents.api.ports` | 同域 | ✅ | 端口定义在 agents 域内 |
| `backend → agents.api.ports`（实现端口） | 正向 | ✅ | backend 依赖 agents 抽象（DIP） |
| `agents → backend` | 逆向 | ❌ 永不发生 | 被端口 + DI 替代 |
| `backend → agents.api.*`（编排） | 正向 | ✅ | 现有编排链路 |

### 3.3 端口使用约束

- 端口仅用于「智能体运行时必需、但属于后端职责的能力」（持久化/会话上下文/任务状态回写）。
- **凡能走 EventBus 的交互不设端口**（事件广播类走 EventBus，避免与 EventBus 职责重叠）。
- 端口实现由组合根 `backend/composition.py` 构造并注入 `agents.tools.runtime.Runtime(ports={...})`。
- 端口新增须经 `05_API_SPEC.md` + `10_INTERFACE_BOUNDARY_SPEC.md` 登记 + CHANGELOG。

---

## 4. 后端开发计划（B0–B6）

| 阶段 | 任务 | 产物 | 依赖 |
|------|------|------|------|
| **B0 工程骨架** | `pyproject.toml`（FastAPI/uvicorn/pydantic/sqlalchemy/aiosqlite/pytest/ruff/mypy/httpx）、`backend/composition.py`（DI 组合根）、`Makefile`、`tooling/configs/{backend,gateway}.yaml` + `environments/` | 可启动空壳 | protocol P1 |
| **B1 Gateway** | `gateway/auth`（JWT/API-key）、`middleware`（限流/trace 注入）、`routes`（挂载 controllers）、`adapters`（HTTP/WS/SSE）；透传 `X-Trace-Id`/`X-Session-Id`/`X-Task-Id`；错误信封 `{code,message,trace_id}` | 入口可用 | B0 |
| **B2 Mappers** | `entities`（SQLAlchemy）、`dto`、`repositories`（session/task/agent/memory/graph）、`converters`（protocol↔entity↔dto） | 持久化层 | B0 |
| **B3 Services** | `session/`·`task/`（create→`RuntimeAPI.submit`）·`agent/`（invoke→`RuntimeAPI.run` + 端口实现）·`memory/`（桥接 `MemoryAPI`）·`graph/`（订阅 `GraphUpdate` 缓存）；实现 `PersistencePort`/`SessionPort`/`TaskUpdatePort` | 业务逻辑 | B2 |
| **B4 Controllers** | `api/`（REST 端点见 §5）·`ws/`（stream）·`sse/`（events）·`schemas/`（由 protocol 生成）·`middleware/`；只校验 + 调 service | 对外接口 | B3 |
| **B5 智能体集成** | `composition.py` 注入 agents.api 实现 + 后端端口；`TaskAPI.create_task`→`RuntimeAPI.submit`（async）；`/agents/{id}/invoke`→`RuntimeAPI.run`；事件经 EventBus.subscribe→SSE；graph 经 EventBus 订阅缓存 | 端到端编排 | B4 + agents P5 |
| **B6 测试** | unit（services/mappers/controllers）·integration（gateway→…→agents mock）·contract（API 签名）·e2e（goal→plan→execute→result） | 覆盖率≥80% | B5 |

### 后端分层职责（FastAPI 映射）

| 层 | 目录 | FastAPI 角色 |
|----|------|--------------|
| Gateway | `backend/gateway/` | FastAPI `APIRouter` 挂载 + middleware（auth/ratelimit/trace） |
| Controllers | `backend/controllers/api/` | `APIRouter` + 路径操作（`@router.post`）；参数用 Pydantic Schema |
| Controllers | `backend/controllers/ws/` | `WebSocketRoute` |
| Controllers | `backend/controllers/sse/` | `StreamingResponse`（`text/event-stream`） |
| Services | `backend/services/` | 业务逻辑类，被 controller 依赖注入 |
| Mappers | `backend/mappers/` | SQLAlchemy `AsyncSession` + repositories |
| 组合根 | `backend/composition.py` | 构造 service/repository/agents-api/ports 并注入 |

---

## 5. 后端 REST 端点

| 方法 | 路径 | → service | → agents.api / 端口 |
|------|------|-----------|---------------------|
| GET | /api/v1/health | — | — |
| POST | /api/v1/sessions | session.create | — |
| GET | /api/v1/sessions/{id} | session.get | — |
| DELETE | /api/v1/sessions/{id} | session.close | — |
| POST | /api/v1/tasks | task.create | RuntimeAPI.submit（async；agents 域内部 plan→route→schedule→execute） |
| GET | /api/v1/tasks | task.list | — |
| GET | /api/v1/tasks/{id} | task.get | — |
| POST | /api/v1/tasks/{id}/cancel | task.cancel | — |
| GET | /api/v1/agents | agent.list | AgentRegistryAPI.list_agents |
| GET | /api/v1/agents/{id} | agent.get | AgentRegistryAPI.get |
| POST | /api/v1/agents/{id}/invoke | agent.invoke | RuntimeAPI.run（指定 agent，直调） |
| GET | /api/v1/memory/{session} | memory.read | MemoryAPI.read |
| POST | /api/v1/memory/{session} | memory.write | MemoryAPI.write |
| GET | /api/v1/graph | graph.get | EventBus 订阅 GraphUpdate 缓存 |
| POST | /api/v1/tools/{name}/invoke | tool.invoke | ExecutionAPI.execute（直调，不经 Agent） |
| GET | /api/v1/metrics | metrics | observability.api.MonitorAPI |
| GET | /api/v1/replay/{session} | replay | ReplayAPI.replay |
| WS | /ws/v1/stream?session= | EventStream | EventBus.subscribe → 推前端 |
| SSE | /api/v1/events?stream= | EventStream | EventBus.subscribe → 推前端 |

> **路径规范**：REST 路径不暴露内部目录结构。路径简化映射：`/agents/action/execution/tools/`→`/tools/`、`/agents/memory/`→`/memory/`、`/observability/inspect/replay/`→`/replay/`。

### 5.1 新增端点：`POST /api/v1/agents/{id}/invoke`

| 项 | 值 |
|----|-----|
| Request | `{ "goal": str, "session_id": str }` → 构造 `Task(goal=goal)` |
| Response | `Task`（含 status + result） |
| Error | `code:AGENT_NOT_FOUND` / `code:EXEC_FAILED` |
| Timeout | 60s |
| Retry | 不重试（由上层 Task.retry 决定） |
| Version | v1 |
| 同步性 | async（内部 `RuntimeAPI.run(agent_id, task)`） |
| 说明 | 指定 agent 直调，不经路由选择；`POST /tasks` 则用 `RuntimeAPI.submit` 由 agents 域路由 |

---

## 6. 前端开发计划（F0–F5）

| 阶段 | 任务 | 产物 | 依赖 |
|------|------|------|------|
| **F0 工程骨架** | `package.json`（React18/TS5/Vite5/Zustand/Vitest/Playwright）、`tsconfig.json`、`vite.config.ts`、eslint/prettier、`tooling/scripts/gen_ts_types.py`（Pydantic→TS）+ npm script `gen:types`、`src/`入口、`public/` | 可启动空壳 | protocol P1 |
| **F1 Mappers** | `apimappers/`（REST 客户端封装，经 gateway）、`viewmodels/`（protocol→VM）、`store/`（Zustand 全局状态）、`utils/`·`styles/`·`assets/`；TS 类型用 `gen_ts_types.py` 生成结果 | 数据层 | F0 |
| **F2 Services** | `api/`（REST 经 gateway）·`realtime/`（WS+SSE 管理 + 自动重连）·`session/`（会话/任务状态）·`graph/`（图数据 + 订阅 GraphUpdate） | 业务逻辑 | F1 |
| **F3 Controllers** | `interaction/`（用户交互）·`events/`（后端事件分发）·`routes/`（页面路由）；调 service → 分发 views | 交互层 | F2 |
| **F4 Views** | `canvas/`（DAG 画布）·`graph/`（WebGL/Canvas 动态图增量渲染）·`monitor/`（Agent 监控面板）·`replay/`（回放时间线）；暗色主题 + 键盘可达 | UI | F3 |
| **F5 集成 E2E** | 接 backend 实时更新；Playwright E2E（创建任务→看图→看监控→回放） | 可交互 | F4 + B5 |

### 前端分层职责

| 层 | 目录 | 职责 |
|----|------|------|
| Controllers | `frontend/src/controllers/` | 交互/事件处理 + 调 service + 分发 views，不含业务逻辑 |
| Services | `frontend/src/services/` | API 调用（经 gateway）、WS/SSE 管理、状态编排 |
| Mappers | `frontend/src/mappers/` | protocol→VM 转换、REST 客户端、全局 store、工具/样式/资产 |
| Views | `frontend/src/views/` | canvas/graph/monitor/replay UI 渲染，不含业务逻辑 |

### 6.1 TS 类型生成（`gen_ts_types.py`）

- 位置：`tooling/scripts/gen_ts_types.py`。
- 输入：`protocol/*.py`（Pydantic 模型，P1 完成后）。
- 输出：`frontend/src/protocol/types.ts`（或 `frontend/src/types/`）。
- 命令：`python3 tooling/scripts/gen_ts_types.py`（或 `npm run gen:types`）。
- CI 强制：提交的 `types.ts` 须与生成结果一致，禁止手改。
- protocol 变更后须重跑生成。

---

## 7. 并行与依赖编排

```
P1 protocol(Pydantic) ──┬─→ B0 后端骨架 ──→ B1→B2→B3→B4 ──→ B5(需 agents P5) ──→ B6
                        └─→ F0 前端骨架 ──→ F1→F2→F3→F4 ──→ F5(需 B5)
tooling/scripts/gen_ts_types.py（F0 后即用于前端类型同步，protocol 变更后重跑）
agents P5（planner+agents）─→ B5 后端智能体集成
```

- 前端（F0–F4）与后端（B0–B4）在契约冻结后可**完全并行**，前端不阻塞后端。
- B5（智能体集成）需 agents P5 完成；未就绪时用 mock `agents.api` 实现占位。
- F5（前端集成 E2E）需 B5 完成（真实后端）。
- `gen_ts_types.py` 是前后端契约同步的桥梁，protocol 每次变更后 CI 重跑。

---

## 8. 已同步更新的规范

| 文件 | 改动 |
|------|------|
| `12_TECH_STACK_SPEC.md` | §3 加 FastAPI/Uvicorn/httpx/SQLAlchemy/aiosqlite；§4 加 Zustand/Vitest/Playwright；§6 加 gen_ts_types.py |
| `agents/api/ports.py` | 新增 3 个 DI 端口 Protocol（PersistencePort/SessionPort/TaskUpdatePort） |
| `05_API_SPEC.md` | §3 REST 端点加 `POST /api/v1/agents/{id}/invoke`；§2.3 Agent 加 invoke；新增 §2.15 DI 端口契约 |
| `10_INTERFACE_BOUNDARY_SPEC.md` | §5 加「反向 DI 端口」行；§9 并行契约加 DI 端口说明 |
| `03_IMPORT_SPEC.md` | §5 补注：`agents.api.ports` 由 agents 消费、backend 实现，属 DIP 不算逆向 |
| `00_PROJECT_SPEC.md` / `specs/README.md` / `AGENT.md` | 索引加 13 |

---

## 9. 风险与对策

| 风险 | 对策 |
|------|------|
| 反向 DI 端口滥用 | 端口限定为「智能体必需的后端能力」；凡能走 EventBus 的不设端口；新增端口须登记 |
| FastAPI 同步/异步混用 | 编排链全程 async；`/invoke` 直调返回 `Task` 但内部 async；controller 用 `async def` |
| 前端类型漂移 | CI 强制 `gen_ts_types.py` 产物与提交一致；禁止手改 `types.ts` |
| agents P5 未就绪阻塞 B5 | B5 用 mock `agents.api` 实现占位，agents P5 完成后替换 |
| 端口接口膨胀 | 端口方法保持粗粒度（save/update/get），避免细碎 CRUD 暴露给 agents |

---

## 10. 里程碑验收

| 里程碑 | 验收标准 |
|--------|----------|
| B0 | `make setup && uvicorn backend.main:app` 可启动，`/api/v1/health` 返回 200 |
| B4 | 全部 REST/WS/SSE 端点可调用（agents 用 mock），返回 `protocol` 类型 |
| B5 | 真实 agents 接入，`POST /tasks` 完成端到端 goal→plan→execute→result |
| B6 | 覆盖率≥80%，关键路径≥90%，E2E 通过 |
| F0 | `npm run dev` 可启动，`gen:types` 生成 `types.ts` |
| F4 | canvas/graph/monitor/replay 四视图可渲染（接 mock 数据） |
| F5 | Playwright E2E 通过（创建任务→看图→看监控→回放） |
