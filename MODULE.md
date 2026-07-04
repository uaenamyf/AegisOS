# AegisOS 模块总览（MODULE.md）

> **本文档面向开发者**，逐层介绍 AegisOS 每个大模块「是什么、做了什么、下面有哪些子模块」，帮助新人快速理解整个工程的代码实现现状。
>
> 每个大模块有独立的 `MODULE.md` 详解，可点击链接深入查看。
>
> 最后更新：2026-07-04 · 55 个测试全通过

---

## 📊 全局仪表盘

| # | 大模块 | 是什么 | 代码文件 | 测试数 | 实现状态 | 详解 |
|---|--------|--------|---------|--------|---------|------|
| 1 | `protocol/` | 契约层 — 全系统唯一数据类型定义 | 10 `.py` | 6 | ✅ 核心完成 | [MODULE.md](protocol/MODULE.md) |
| 2 | `agents/` | 智能体域 — 认知核心，五层架构 | 20 `.py` | 41 | ✅ 核心算法完成 / 🔲 编排器待补 | [MODULE.md](agents/MODULE.md) |
| 3 | `backend/` | 应用层 — FastAPI REST + WS + SSE + DB | 18 `.py` | — | ✅ 可运行 | [MODULE.md](backend/MODULE.md) |
| 4 | `frontend/` | 表现层 — React + Vite AI Native IDE | 25 `.ts/.tsx` | — | ✅ Chat 联调 / 🔲 攻防视图待补 | [MODULE.md](frontend/MODULE.md) |
| 5 | `infrastructure/` | 基建层 — 传输 · 节点 · 交付 | 1 `.py` | 0 | 🔲 仅 API 协议定义 | [MODULE.md](infrastructure/MODULE.md) |
| 6 | `observability/` | 可观测层 — 监控 · 基准 · 可视化 | 1 `.py` | 0 | 🔲 仅 API 协议定义 | [MODULE.md](observability/MODULE.md) |
| 7 | `data/` | 数据层 — 数据集 · 模型 schema | 1 `.py` | 0 | 🔲 仅 API 协议 + SQLite | [MODULE.md](data/MODULE.md) |
| 8 | `tooling/` | 工程支撑 — 脚本 · 配置 | 4 `.py` | 0 | ✅ 3 脚本可用 | [MODULE.md](tooling/MODULE.md) |
| 9 | `developer/` | 规范层 — SSOT 规范 + roadmap | 0 `.py` | — | ✅ 规范就位 | [MODULE.md](developer/MODULE.md) |
| 10 | `tests/` | 测试 — 55 个测试全通过 | 26 `.py` | 55 | ✅ Phase A-E 覆盖 | — |

**模块依赖关系**：

```
developer/specs  ← 定义规范（唯一真相源 SSOT）
       ↓
protocol/        ← 唯一契约（所有域引用）
       ↓
agents/api       ← 公共接口（5 个 Protocol + 3 个 DI 端口）
       ↓                ↑
backend/api  ← 调用 agents.api
       ↓
frontend/services ← 调用 backend REST API
```

> **铁律**：跨域调用仅经 `from {domain}.api import ...`，禁止直接 import 内部子包。数据契约只用 `protocol/` 类型。

---

## 1. `protocol/` — 契约层

### 是什么
全系统**唯一**的数据类型定义层。所有跨模块通信的参数、返回值、消息载体必须使用 `protocol/` 里定义的类型，禁止任何模块自造并行结构。这是整个工程的「宪法」。

### 做了什么
定义了 10 个 `.py` 文件，覆盖消息通信、事件总线、智能体注册、任务调度、记忆包、动态异构图、工具调用、心跳、端边云同步，以及攻防专用的 8 个 dataclass。

### 子模块（10 个文件）

| 文件 | 核心类型 | 功能说明 |
|------|---------|---------|
| `message.py` | `Message` · `NodeRef` | **消息信封**：跨模块通信的统一载体，携带 message_id/sender/receiver/priority/ttl/payload |
| `event.py` | `EventType`(8 种) · `Event` | **事件总线**：8 种事件类型（agent.start/finish、tool.call/finish、task.retry/rollback、memory.update、graph.update） |
| `agent.py` | `Agent` · `AgentStatus` | **智能体注册**：agent_id/name/role/capabilities/status/trust_score/success_rate |
| `scheduler.py` | `Task` · `TaskStatus` · `RetryPolicy` | **任务调度**：任务生命周期（pending→running→succeeded/failed/rolled_back）。⚠️ Task 缺 payload 字段 |
| `memory.py` | `MemoryPacket` | **记忆包**：task_id/kind/summary/working/episodic/compression/recent |
| `graph.py` | `Graph` · `GraphNode` · `GraphEdge` · `GraphDiff` · `NodeKind` | **动态异构图**：节点（agent/task/memory/tool）+ 边 + 子图差异计算 |
| `tool.py` | `ToolCall` · `ToolResult` · `ToolSpec` | **工具调用契约**：工具的调用/结果/规格定义 |
| `heartbeat.py` | `Heartbeat` | **心跳**：Agent 存活检测 |
| `sync.py` | `SyncStatus` · `SyncOp` | **端边云同步**：同步状态与操作 |
| `cyber.py` | `Asset` · `VulnFinding` · `AttackStep` · `AttackChain` · `Alert` · `DefenseAction` · `ResponsePlan` · `ThreatIntel` | **攻防协议类型**（8 个 dataclass）：资产、漏洞发现、攻击步骤、攻击链、告警、防御动作、响应计划、威胁情报 |

### 测试
`tests/protocol/test_cyber.py` — 6 个测试，验证 8 个攻防类型的字段、序列化、反序列化。

### 未实现
- `cyber.py` 中 `ThreatIntel` 仅基础结构，无 ATT&CK 技战术映射。

📎 详解：[protocol/MODULE.md](protocol/MODULE.md) · 规范：[`04_PROTOCOL_SPEC.md`](developer/specs/04_PROTOCOL_SPEC.md)

---

## 2. `agents/` — 智能体域

### 是什么
系统的**认知核心**，实现五层架构：感知 → 规划 → 行动 → 记忆 → 工具。这是群体智能协同推理引擎的核心代码所在，包含路由、选举、调度、压缩、唤醒等关键算法，以及 11 个红蓝紫攻防 Agent。

### 做了什么
- **规划引擎**：实现了活跃子图过滤、低熵稀疏路由（Top-K=3）、异构选举（点积匹配）、端边云卸载调度
- **记忆子系统**：实现了上下文压缩（超预算时保留 decision+recent）和记忆唤醒（关键词匹配 Top-5）
- **攻防 Agent**：11 个 Agent 全部完成 — 红队 4 个（侦察/漏洞关联/攻击规划/横向移动）、蓝队 5 个（检测/分诊/威胁狩猎/应急响应/取证）、紫队 2 个（对抗校验/一致性审查）
- **感知层**：实现了神经符号闭环（符号规则验证 + LLM 重新生成 → 迭代修复）
- **工具层**：实现了多模型路由（gpt→OpenAI, claude→Anthropic, local→本地）
- **公共接口**：5 个 Protocol 接口 + 3 个 DI 端口

### 子模块

#### 2.1 `agents/planning/` — 规划引擎 ✅ 核心算法完成

| 子模块 | 文件 | 功能 | 测试 |
|--------|------|------|------|
| `engine/topology/` | `topology.py` `active_subgraph()` | 按 capability + status(active/degraded) 过滤活跃子图 | 2 |
| `engine/router/` | `router.py` `route()` | 低熵稀疏路由 Top-K=3，按 affinity - load_penalty 排序，**非全广播** | 3 |
| `engine/router/` | `election.py` `elect()` | 异构选举：task_features · capability_vectors 点积最高者胜出 | 2 |
| `engine/scheduler/` | `scheduler.py` `schedule()` | 端边云卸载：privacy=local→edge，latency<5s→edge，否则→cloud | 3 |

🔲 **未实现**：`planner/` · `orchestrator/` · `engine/workflow/` · `engine/eventbus/` 仅有 AGENT.md，编排器全空。

#### 2.2 `agents/memory/` — 记忆子系统 ✅ 压缩+唤醒完成

| 子模块 | 文件 | 功能 | 测试 |
|--------|------|------|------|
| `compression/` | `compactor.py` `compress()` | 上下文压缩：超 budget 时保留 decision+recent，其余合并为 digest | 4 |
| `recall/` | `recaller.py` `recall()` | 记忆唤醒：trigger 关键词匹配 episodic+vector，decision 优先，Top-5 | 3 |

🔲 **未实现**（仅 AGENT.md）：working · episodic · semantic · vector · archive · cache · checkpoint · reflection · retrieval · snapshot · sync。

#### 2.3 `agents/action/` — 攻防 Agent ✅ 11 个全部完成

| 阵营 | Agent | 子模块 | 核心方法 | 功能 | 测试 |
|------|-------|--------|---------|------|------|
| 🔴 红队 | `recon` | `recon/` | `scan(target_range)` | 目标范围 → 资产列表 | 2 |
| 🔴 红队 | `vuln_correlator` | `vuln_correlator/` | `correlate(assets, cve_db)` | 资产+CVE库 → 漏洞发现列表 | 1 |
| 🔴 红队 | `exploit_planner` | `exploit_planner/` | `plan(findings)` | 漏洞列表 → 攻击链 | 1 |
| 🔴 红队 | `lateral_move` | `lateral_move/` | `plan_moves(chain)` | 攻击链 → 横向移动步骤 | 1 |
| 🔵 蓝队 | `detector` | `detector/` | `detect(events)` | 事件流 → 告警列表 | 2 |
| 🔵 蓝队 | `triage` | `triage/` | `triage(alerts)` | 告警列表 → 按严重度排序 | 1 |
| 🔵 蓝队 | `threat_hunt` | `threat_hunt/` | `hunt(alerts)` | 告警 → ATT&CK 假设 | 1 |
| 🔵 蓝队 | `ir_planner` | `ir_planner/` | `plan_response(hypotheses)` | 假设 → 响应计划（含 rollback） | 2 |
| 🔵 蓝队 | `forensics` | `forensics/` | `investigate(alert)` | 告警 → 取证报告 | 1 |
| 🟣 紫队 | `critic` | `critic/` | `critique(chain_or_plan)` | 对抗性校验，红蓝产出反驳 | 2 |
| 🟣 紫队 | `reviewer` | `reviewer/` | `review(inputs)` | 一致性审查，最终结论 | 1 |

另外有 `execution/`（沙箱执行环境）、`coder/`、`debugger/`、`tester/`、`docwriter/`、`researcher/`、`executor/` 子模块（仅有 AGENT.md 或基础结构）。

#### 2.4 `agents/perception/` — 感知层 ✅ 神经符号闭环完成

| 子模块 | 文件 | 功能 | 测试 |
|--------|------|------|------|
| `reasoning/` | `neuro_symbolic.py` `validate_chain()` · `NeuroSymbolicLoop` | 符号验证（allowed_techniques 规则）+ LLM 重新生成 → 迭代修复 | 4 |

🔲 **未实现**：`context/` · `reflection/` 仅有 AGENT.md。

#### 2.5 `agents/tools/` — 工具层 ✅ 多模型兼容完成

| 子模块 | 文件 | 功能 | 测试 |
|--------|------|------|------|
| `llms/` | `base.py` `LLMRequest` · `LLMResponse` · `ModelProvider` | LLM 调用抽象基类 | — |
| `llms/` | `mock_provider.py` `MockProvider` | 测试用 Mock 实现 | — |
| `llms/` | `model_router.py` `ModelRouter` | 多模型路由：gpt→OpenAI, claude→Anthropic, local/*→本地, 按 tier(edge/cloud) 映射 | 5 |
| `llms/` | `openai_provider.py` · `anthropic_provider.py` · `local_provider.py` · `scheduler_adapter.py` | 各模型 Provider 实现 | — |

🔲 **未实现**：`prompts/` · `runtime/` 仅有 AGENT.md。

#### 2.6 `agents/api/` — 公共接口 ✅ 5 接口 + 3 端口

| 接口/端口 | 方法 |
|-----------|------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` |
| `ExecutionAPI` | `execute(call)` |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` |
| `ports.py` | `PersistencePort` · `SessionPort` · `TaskUpdatePort`（DI 端口） |

📎 详解：[agents/MODULE.md](agents/MODULE.md) · 规范：[`08_AGENT_SPEC.md`](developer/specs/08_AGENT_SPEC.md)

---

## 3. `backend/` — 应用层（FastAPI）

### 是什么
后端应用层，采用 Controller-Service-Mapper 三层架构 + Gateway 网关，对外提供 REST API + WebSocket + SSE 实时通信，并通过 SQLAlchemy async + aiosqlite 做数据持久化。是前后端联调的桥梁。

### 做了什么
- **FastAPI 应用**：完整的 app 创建 + CORS + 请求追踪中间件 + lifespan 数据库初始化
- **网关鉴权**：`/api/v1/*` 前缀路由 + X-API-Key header 鉴权（`aegis-dev-key`）
- **10 个 REST 端点**：health / sessions / tasks / agents / graph / memory / tools / metrics / replay
- **实时通信**：SSE 事件推送 + WebSocket 双向流
- **数据持久化**：SQLAlchemy async + aiosqlite，Session/Task 实体 + 仓储 + 转换器
- **DI 组合根**：`composition.py` 装配 DB + 仓储 + 服务 + 14 Agent 注册 + MockRuntime

### 子模块

| 子模块 | 路径 | 功能 |
|--------|------|------|
| **入口** | `src/main.py` | FastAPI app + CORS + TraceMiddleware + lifespan(DB init) |
| **网关** | `src/gateway/routes.py` | `/api/v1` 前缀 + `verify_api_key` 鉴权 |
| | `src/gateway/auth.py` | X-API-Key header 校验 |
| | `src/gateway/middleware.py` | TraceMiddleware（请求追踪 ID） |
| **REST 端点** | `src/controllers/api/` | 10 个端点文件：health.py · sessions.py · tasks.py · agents.py · graph.py · memory.py · tools.py · metrics.py · replay.py |
| **SSE** | `src/controllers/sse/events.py` | `GET /api/v1/events/stream` 服务器推送 |
| **WebSocket** | `src/controllers/ws/stream.py` | `WS /ws/v1/stream` 双向流 |
| **Service** | `src/services/` | 业务逻辑层：session.py · task.py · agent.py · graph.py · memory.py · ports.py |
| **Mapper** | `src/mappers/` | 数据映射：database.py(AsyncEngine) · entities.py(Base/SessionEntity/TaskEntity) · repositories.py · converters.py |
| **DI** | `src/composition.py` | 组合根：装配 DB + 仓储 + 服务 + 14 Agent 注册 + MockRuntime |

### API 鉴权
所有 `/api/v1/*` 端点需要 `X-API-Key: aegis-dev-key` header（`/health` 除外）。

### 未实现
- 🔲 攻防端点 `/api/v1/range/*`（靶场/拓扑/攻击/攻击链/防御）

📎 详解：[backend/MODULE.md](backend/MODULE.md) · 规范：[`05_API_SPEC.md`](developer/specs/05_API_SPEC.md) · [`10_INTERFACE_BOUNDARY_SPEC.md`](developer/specs/10_INTERFACE_BOUNDARY_SPEC.md)

---

## 4. `frontend/` — 表现层（React + Vite）

### 是什么
AI Native IDE 前端，采用 Controller-Service-Mapper 模式 + 5 个视图（Chat / Canvas / Graph / Monitor / Replay），使用 React 18 + Vite 5 + Zustand + TypeScript 技术栈。提供与后端实时交互的用户界面。

### 做了什么
- **类型系统**：`gen_ts_types.py` 自动生成的 36 个 TS 类型，映射 `protocol/*.py`
- **全局状态**：Zustand store 管理 session/agents/chatMessages/graph/isSending
- **API 客户端**：统一 HTTP 客户端（baseURL + X-API-Key header）
- **5 个 REST 服务**：agents / sessions / tasks / memory / graph
- **实时通信**：SSE + WebSocket 封装
- **ChatView 完整实现**：Agent 选择 + 消息收发 + 任务提交 + 状态轮询 + 自动滚动
- **5 个视图骨架**：chat ✅ / canvas 🔲 / graph 🔲 / monitor 🔲 / replay 🔲

### 子模块

| 子模块 | 路径 | 功能 |
|--------|------|------|
| **类型** | `src/protocol/types.ts` | 自动生成，36 个 TS 类型映射 protocol/*.py |
| | `src/protocol/frontend-types.ts` | `ViewName` · 路由类型 |
| **Store** | `mappers/store/index.ts` | Zustand 全局状态：session/agents/chatMessages/graph/isSending |
| **API Client** | `mappers/apimappers/client.ts` | 统一 HTTP 客户端（baseURL + X-API-Key） |
| **REST Services** | `services/api/` | 5 个服务：agents.ts · sessions.ts · tasks.ts · memory.ts · graph.ts |
| **图服务** | `services/graph/index.ts` | 图数据服务 |
| **实时通信** | `services/realtime/sse.ts` · `ws.ts` | SSE + WebSocket 封装 |
| **会话管理** | `services/session/index.ts` | 会话管理服务 |
| **Controllers** | `controllers/interaction.ts` · `events.ts` · `routes.ts` | 交互/事件/路由控制 |
| **Views** | `views/chat/ChatView.tsx` | ✅ **完整实现**：14 Agent 选择 + 消息收发 + 任务创建 + 状态轮询 |
| | `views/canvas/` · `graph/` · `monitor/` · `replay/` · `agents/` · `dashboard/` · `layout/` | 🔲 占位符/骨架组件 |

### ChatView 已实现功能
- Agent 下拉选择（14 个 Agent）
- 消息发送 + 响应展示
- 任务创建 + 状态轮询
- 自动滚动

### 未实现
- 🔲 CanvasView：攻击链 DAG 可视化（需 React Flow）
- 🔲 GraphView：异构图可视化
- 🔲 MonitorView：防御看板
- 🔲 ReplayView：时序回放
- 🔲 前端 cyber 类型（protocol/cyber.py 未映射到 TS）

📎 详解：[frontend/MODULE.md](frontend/MODULE.md) · 计划：[`plans/13_FRONTEND_BACKEND_PLAN.md`](developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md)

---

## 5. `infrastructure/` — 基建层

### 是什么
基建层，负责传输通信、端边云节点管理、部署交付。赛事要求包含 Docker 沙箱靶场（攻防工具仅在此沙箱内运行，永不触真实网络）。

### 做了什么
- **API 协议定义**：4 个 Protocol 接口定义完成
  - `CommunicationAPI` — 通信传输接口
  - `NodeRegistryAPI` — 节点注册接口
  - `SyncAPI` — 同步接口
  - `DeploymentAPI` — 部署接口

### 子模块

| 子模块 | 路径 | 功能 | 状态 |
|--------|------|------|------|
| **API** | `api/__init__.py` | 4 个 Protocol 接口定义 | ✅ |
| **传输** | `transport/communication/` | 传输层（gRPC/HTTP 通信） | 🔲 仅 AGENT.md |
| **端侧节点** | `nodes/edge/` | 端侧节点管理 | 🔲 仅 AGENT.md |
| **云侧节点** | `nodes/cloud/` | 云侧节点管理 | 🔲 仅 AGENT.md |
| **部署交付** | `delivery/deployment/` | 部署交付 | 🔲 仅 AGENT.md |

### 未实现
- 🔲 Docker 沙箱靶场（赛事 H1 核心需求）
- 🔲 端边云通信与节点管理全部待实现

📎 详解：[infrastructure/MODULE.md](infrastructure/MODULE.md)

---

## 6. `observability/` — 可观测层

### 是什么
可观测层，分为三个子域：inspect（监控 · 回放）、measure（基准 · 评测）、present（可视化）。赛事要求提供 5 维度评测和攻击链回放能力。

### 做了什么
- **API 协议定义**：6 个 Protocol 接口定义完成
  - `MonitorAPI` — 监控接口
  - `TraceAPI` — 追踪接口
  - `ReplayAPI` — 回放接口
  - `BenchmarkAPI` — 基准测试接口
  - `EvaluationAPI` — 评测接口
  - `VisualizationAPI` — 可视化接口

### 子模块

| 子模块 | 路径 | 功能 | 状态 |
|--------|------|------|------|
| **API** | `api/__init__.py` | 6 个 Protocol 接口定义 | ✅ |
| **监控** | `inspect/monitor/` | 实时监控 | 🔲 仅 AGENT.md |
| **回放** | `inspect/replay/` | 攻击链回放 | 🔲 仅 AGENT.md |
| **基准** | `measure/benchmark/` | 性能基准测试 | 🔲 仅 AGENT.md |
| **评测** | `measure/evaluation/` | 5 维度评测 | 🔲 仅 AGENT.md |
| **可视化** | `present/visualization/` | 数据可视化 | 🔲 仅 AGENT.md |

### 未实现
- 🔲 全部子模块仅有 AGENT.md，无代码实现
- 🔲 赛事 H5：5 维度评测 + 攻击链回放

📎 详解：[observability/MODULE.md](observability/MODULE.md)

---

## 7. `data/` — 数据层

### 是什么
数据层，管理数据集和模型 schema。赛事要求接入 Neo4j（拓扑图 + ATT&CK 图）和 Qdrant（向量库）。

### 做了什么
- **API 协议定义**：2 个 Protocol 接口定义完成
  - `DatasetAPI` — 数据集接口
  - `ModelSchemaAPI` — 模型 schema 接口
- **SQLite 数据库**：`aegisos.db` 文件（后端运行时自动生成，存储 Session/Task）

### 子模块

| 子模块 | 路径 | 功能 | 状态 |
|--------|------|------|------|
| **API** | `api/__init__.py` | 2 个 Protocol 接口定义 | ✅ |
| **数据集** | `datasets/` | 数据集管理 | 🔲 仅 AGENT.md |
| **模型** | `models/` | 数据模型（Neo4j 拓扑图 + Qdrant 向量库） | 🔲 仅 AGENT.md |
| **DB 文件** | `aegisos.db` | SQLite 数据库（运行时生成） | ✅ |

### 未实现
- 🔲 Neo4j 拓扑图 + ATT&CK 图接入（赛事 H2）
- 🔲 Qdrant 向量库接入（赛事 H2）

📎 详解：[data/MODULE.md](data/MODULE.md)

---

## 8. `tooling/` — 工程支撑

### 是什么
工程支撑层，提供自动化脚本和配置文件，辅助开发流程。

### 做了什么
- **3 个可用脚本**：
  - `gen_readme.py` — 自动生成 README 目录树 + 仓库统计
  - `gen_ts_types.py` — 从 protocol/*.py 自动生成前端 TS 类型定义
  - `realign_agent_docs.py` — 对齐各模块 AGENT.md 交叉引用
- **API 协议定义**：2 个 Protocol 接口（ConfigAPI · ScriptAPI）
- **配置文件**：backend.yaml（后端 CORS）+ gateway.yaml（网关配置）

### 子模块

| 子模块 | 路径 | 功能 | 状态 |
|--------|------|------|------|
| **API** | `api/__init__.py` | 2 个 Protocol 接口：ConfigAPI · ScriptAPI | ✅ |
| **脚本** | `scripts/gen_readme.py` | 自动生成 README 目录树 | ✅ 可用 |
| | `scripts/gen_ts_types.py` | 从 protocol/*.py 生成前端 TS 类型 | ✅ 可用 |
| | `scripts/realign_agent_docs.py` | 对齐各模块 AGENT.md 交叉引用 | ✅ 可用 |
| | `scripts/add_agent_crossrefs.pl` | Perl 脚本：批量添加 Agent 交叉引用 | ✅ 可用 |
| **配置** | `configs/backend.yaml` | 后端配置（CORS origins 等） | ✅ |
| | `configs/gateway.yaml` | 网关配置 | ✅ |

### 未实现
- 🔲 `check_no_broadcast.py`（C4：检测低熵全广播违规）

📎 详解：[tooling/MODULE.md](tooling/MODULE.md)

---

## 9. `developer/` — 规范层

### 是什么
项目「大脑」，存放唯一真相源（SSOT）的规范文档和 roadmap 阶段计划。**P0 规范未完成前不得写业务代码**（Spec First 原则）。本层无 Python 代码，全部是 Markdown 文档。

### 做了什么
- **15 个规范文件**（00-15），覆盖项目/架构/目录/Import/协议/API/Schema/事件/Agent/开发/接口/AI编码/技术栈/前后端计划/赛事方案/任务清单
- **roadmap P0-P7**：P0-P5 已完成，P6 部分完成，P7 未开始
- **CHANGELOG.md**：变更记录

### 子模块

| 子模块 | 路径 | 内容 |
|--------|------|------|
| **规范** | `specs/00_PROJECT_SPEC.md` | 项目 SSOT：目标/边界/原则/分层/生命周期/commit/review |
| | `specs/01_ARCHITECTURE_SPEC.md` | 系统架构：分层/微内核/DDD/事件驱动 |
| | `specs/02_DIRECTORY_SPEC.md` | 目录规范：每目录职责/边界/可改性 |
| | `specs/03_IMPORT_SPEC.md` | Import 规范：依赖矩阵/禁循环（AI 最重要） |
| | `specs/04_PROTOCOL_SPEC.md` | 通信协议：Message/Event/Task/Graph/低熵稀疏§16 |
| | `specs/05_API_SPEC.md` | API 契约：27 接口 × Request/Response/Error |
| | `specs/06_SCHEMA_SPEC.md` | 数据 Schema（现 dataclass，§12 向 Pydantic 迁移） |
| | `specs/07_EVENT_SPEC.md` | 事件总线：8 事件/生命周期/可靠性 |
| | `specs/08_AGENT_SPEC.md` | Agent Runtime：生命周期/API/Prompt/Memory/Tool |
| | `specs/09_DEVELOPMENT_SPEC.md` | 开发流程：Spec→Contract→API→Impl→Test→Doc |
| | `specs/10_INTERFACE_BOUNDARY_SPEC.md` | 接口边界：并行开发核心 |
| | `specs/11_AI_CODING_SPEC.md` | AI 编码规范：范围/禁改协议 API/测试/@aegis-gen |
| | `specs/12_TECH_STACK_SPEC.md` | 技术栈：语言/运行时/框架/库/版本约束 |
| **计划** | `specs/plans/13_FRONTEND_BACKEND_PLAN.md` | 前后端全流程计划 |
| | `specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md` | 赛事总体方案 |
| | `specs/plans/15_CYBERDEFENSE_TASKS.md` | 实施任务清单（Phase A-H） |
| **roadmap** | `roadmap/README.md` | P0-P7 阶段计划总览 |
| | `roadmap/P0/` ~ `P7/` | 各阶段详细计划 |
| **变更日志** | `CHANGELOG.md` | 变更记录 |

### roadmap 进度
| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 初始化（规范/目录/git） | ✅ 完成 |
| P1 | Protocol（契约层） | ✅ 完成 |
| P2 | Memory（记忆子系统） | ✅ 完成 |
| P3 | Router（路由） | ✅ 完成 |
| P4 | Scheduler（调度） | ✅ 完成 |
| P5 | Planner+Agents（规划+攻防 Agent） | ✅ 完成 |
| P6 | Frontend（前端） | ✅ 部分完成（ChatView ✅，其余 🔲） |
| P7 | Deployment（部署） | 🔲 未开始 |

> 冲突优先级：`00` > `04` ≈ `05` ≈ `06` > 其余编号 > 各模块 `AGENT.md`。

📎 详解：[developer/MODULE.md](developer/MODULE.md)

---

## 10. `tests/` — 测试

### 是什么
测试目录，覆盖 Phase A-E 的全部单元测试。当前 55 个测试全部通过。

### 做了什么
55 个测试覆盖了协议类型、记忆压缩/唤醒、规划引擎（拓扑/路由/选举/调度）、多模型路由、11 个攻防 Agent、神经符号闭环。

### 子模块

| 子模块 | 测试文件 | 测试数 | 覆盖内容 |
|--------|---------|--------|---------|
| `tests/protocol/` | `test_cyber.py` | 6 | 8 个攻防 dataclass 字段/序列化 |
| `tests/agents/memory/` | `test_compactor.py` · `test_recaller.py` | 7 | 上下文压缩 + 记忆唤醒 |
| `tests/agents/planning/` | `test_topology.py` · `test_router.py` · `test_election.py` · `test_scheduler.py` | 10 | 活跃子图 + Top-K 路由 + 选举 + 调度 |
| `tests/agents/tools/` | `test_model_router.py` | 5 | 多模型路由 |
| `tests/agents/action/` | 11 个 `test_*.py` | 15 | 11 个攻防 Agent |
| `tests/agents/perception/` | `test_neuro_symbolic.py` | 4 | 神经符号闭环 |

### 未实现
- 🔲 `tests/e2e/` — 端到端集成测试（场景 1：红→蓝→紫完整链路）

---

## 技术栈速查

| 层 | 技术栈 |
|----|--------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy(async) · aiosqlite · uvicorn |
| 前端 | React 18 · Vite 5.4.21 · Zustand 4.5 · TypeScript 5.6 |
| 协议 | Python `@dataclass`（§12 计划迁移 Pydantic） |
| 数据库 | SQLite（`aegisos.db`）→ Neo4j + Qdrant（待接入） |
| 测试 | pytest · ruff · mypy |

## 快速启动

```bash
# 后端
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev

# 测试
.venv/bin/pytest tests/ -v
```

## 相关文档

| 文档 | 说明 |
|------|------|
| [AGENT.md](AGENT.md) | 仓库最高规范 |
| [CLAUDE.md](CLAUDE.md) | 工程总览（渐进式披露） |
| [README.md](README.md) | 项目说明 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 模块实现状态仪表盘 |
| 各域 `MODULE.md` | 每个大模块的详细实现文档（见上表链接） |
| 各域 `AGENT.md` | 每个子模块的规范（职责/边界/接口/测试） |
