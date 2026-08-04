# AegisOS — AGENT.md（仓库总规范）

> 这是整个 AegisOS 仓库的**最高开发规范**。任何 Agent（人或 AI）在开发本仓库前，**第一步必须阅读本文件**，再按需阅读 `developer/specs/` 下相应编号规范，而不是扫描整个项目。
>
> **规范真相源**：`developer/specs/`（编号规范 `00`–`15`）是本项目唯一权威规范。`developer/` 根下旧版散落文档（`API_SPEC.md`/`MESSAGE_PROTOCOL.md`/`EVENT_SPEC.md`/`ARCHITECTURE.md`/`CODING_RULES.md`/`DIRECTORY_GUIDE.md` 等）已删除，统一以 `developer/specs/` 为准。

## 项目定位
AegisOS 是面向「挑战杯揭榜挂帅 + 荣耀群体智能赛题」的 **Agent Operating System (AOS) + AI Native IDE**，方向为**面向超长程网络攻击防御的动态异构群体智能协同推理引擎**, 不仅包含 Agent，而是让整个项目可由 Agent 自主开发。核心特性：动态异构群体智能、长期记忆、低熵通信、端边云协同、可运行系统。

## AI 开发流程（Developer Workflow）
```
Developer Agent
  -> 读取本文件（AGENT.md）
  -> 读取 developer/plan.md（动态开发计划，了解当前待办）
  -> 读取 developer/specs/00_PROJECT_SPEC.md（项目 SSOT）
  -> 读取 developer/specs/03_IMPORT_SPEC.md（依赖矩阵，AI 最易犯错）
  -> 读取 developer/specs/11_AI_CODING_SPEC.md（AI 编码规范）
  -> 读取 developer/roadmap/ 定位当前阶段（P0..P7）
  -> 读取目标模块的 AGENT.md
  -> 读取 protocol/ 契约 + developer/specs/04_PROTOCOL_SPEC.md
  -> 读取目标域 api/ 接口 + developer/specs/05_API_SPEC.md
  -> 读取 tooling/configs/ 配置
  -> 生成代码
  -> 运行 Test（质量门禁：ruff format && ruff check --fix && mypy && pytest）
  -> 检查并更新相关文档（见 `developer/specs/11_AI_CODING_SPEC.md` §7 文档一致性检查）
  -> 生成/更新 Doc + CHANGELOG + plan.md（勾选完成任务）
  -> Commit
```
Agent 永不扫描整个项目；按模块边界精准读写，效率高且不会越界破坏其他子系统。
**铁律**：P0 规范（`developer/specs/`）未完成前，任何人/AI 不得编写业务代码。开发遵循 `Specification → Contract → API → Implementation → Test → Document`。

## 仓库分层（同域聚合 + 域内分类，目录导航详见 developer/specs/02_DIRECTORY_SPEC.md）
1. **developer/** — 规范层（项目大脑）。含 `developer/specs/`（编号规范 SSOT，`00`–`15`）+ `developer/roadmap/`（P0..P7）。
2. **protocol/** — 契约层，唯一数据契约。
3. **frontend/** — 表现层。Controller-Service-Lib + Views：`controllers/`(交互/事件) · `services/`(API/实时/状态) · `lib/`(HTTP 客户端/全局状态) · `views/`(chat·canvas·graph·monitor·replay)。
4. **backend/** — 应用层。Router-Service-Repository-Model + Core：`core/`(组合根DI/鉴权/中间件/路由聚合) · `routers/`(路由层) · `services/`(业务逻辑) · `repositories/`(数据访问) · `models/`(ORM实体) · `schemas/`(契约) · `mocks/`(端口mock)。
5. **aegisos_agents/** — 智能体域。认知架构五层：
   - `aegisos_agents/perception/` 感知：context · reasoning · reflection
   - `aegisos_agents/planning/` 规划：planner · orchestrator · engine/(planner·scheduler·router·workflow·eventbus·topology)
   - `aegisos_agents/action/` 行动：coder·executor·tester·debugger·critic·reviewer·researcher·docwriter + execution/(executor·tools)
   - `aegisos_agents/memory/` 记忆：12 子模块（含 semantic 知识库）
   - `aegisos_agents/tools/` 工具：llms · prompts · runtime
6. **infrastructure/** — 基础设施层。分类：`transport/`(通信) · `nodes/`(端·云) · `delivery/`(部署)。
7. **observability/** — 可观测与评估层。分类：`inspect/`(监控·回放) · `measure/`(基准·评估) · `present/`(可视化)。
8. **data/** — 数据层：`datasets/` · `models/`。
9. **tooling/** — 工程支撑层：`configs/` · `scripts/`。
10. **docs/** — 文档资产层：`{api,architecture,guides,assets}/` · `examples/`。
11. **tests/** — 测试。

## 必读顺序
1. 本文件（AGENT.md）
2. `developer/plan.md`（动态开发计划，了解当前待办和下一步）
3. `developer/specs/00_PROJECT_SPEC.md`（项目 SSOT）
4. `developer/specs/03_IMPORT_SPEC.md`（Import 规范，AI 最重要）
5. `developer/specs/11_AI_CODING_SPEC.md`（AI 编码规范）
6. `developer/specs/12_TECH_STACK_SPEC.md`（技术栈）
7. `developer/roadmap/README.md`（定位当前阶段）
8. 目标模块的 `AGENT.md`
9. `protocol/` 相关契约 + `developer/specs/04_PROTOCOL_SPEC.md`
10. 目标域 `api/` 接口 + `developer/specs/05_API_SPEC.md`
11. 目标域 `AGENT.md` 末尾的「📋 模块实现详解」段 + 根 `AGENT.md` 末尾的「📋 模块实现总览」段

## 全局铁律
- **模块间解耦**：每个域通过 `api/` 子包暴露公共接口（`from {domain}.api import ...`），其他模块**只通过 api/ 调用**，禁止直接导入内部实现子包。内部可自由重构，只要 api/ 签名不变，依赖方不受影响。详见 `developer/specs/03_IMPORT_SPEC.md`。
- 对外数据结构必须复用 `protocol/` 类型，禁止自造并行结构。详见 `developer/specs/04_PROTOCOL_SPEC.md`、`06_SCHEMA_SPEC.md`。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 修改任一模块前先读该模块 `AGENT.md` 的「禁止修改目录」，不得越界。
- `api/` 接口签名变更属破坏性变更，需在 `developer/CHANGELOG.md` 标注并通知依赖方。详见 `developer/specs/05_API_SPEC.md`。
- 提交前运行质量门禁（`ruff format && ruff check --fix && mypy && pytest`）并更新 `developer/CHANGELOG.md`。详见 `developer/specs/09_DEVELOPMENT_SPEC.md`。
- 新增接口同步更新 `developer/specs/05_API_SPEC.md`；新增/变更事件同步 `developer/specs/07_EVENT_SPEC.md`；变更协议同步 `developer/specs/04_PROTOCOL_SPEC.md`。
- 接口边界（谁调谁/异步/网关/EventBus）见 `developer/specs/10_INTERFACE_BOUNDARY_SPEC.md`，三端并行开发以此为准。
- 动态路由遵循低熵稀疏通信：按需链式通信（Agent->Planner->Memory->Coder->Reviewer->Executor），禁止全广播。详见 `developer/specs/04_PROTOCOL_SPEC.md` §16。
- 技术栈只能使用 `developer/specs/12_TECH_STACK_SPEC.md` 登记的语言/框架/库；新增依赖须评估并登记。
- AI 改动须符合 `developer/specs/11_AI_CODING_SPEC.md`（必读文件、单次范围、禁擅改协议/API、测试/文档/冲突处理）。
- **代码注释强制**：首次创建文件须在文件顶部写文件说明 + `date` + `dev`（见 §10.1）；后续增改函数/方法/接口须在改动处写 `date` + `dev` + `changelog` + 代码注释（见 §10.2）。缺失注释的代码视为未完成。
- **文档一致性检查**：每次修改代码后，须检查 `AGENT.md` 总览/`CLAUDE.md`/`docs/ARCHITECTURE.md`/域名 `AGENT.md`/`plan.md` 是否仍反映最新状态，如有过期立即同步更新。详见 `developer/specs/11_AI_CODING_SPEC.md` §7。

## Agent 统一生命周期
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result -> Log -> Heartbeat -> Finish

## Agent 统一接口
- `receive(task)` 接收任务并校验
- `think()` 推理与计划
- `tool()` 调用工具执行
- `reflect()` 反思与自评
- `respond()` 返回结构化结果

## 开发规范体系（developer/specs/，唯一真相源）
> 以下编号规范是本项目权威开发指引。任何开发（人或 AI）均以此为准。

| 编号 | 文件 | 内容 |
|------|------|------|
| 00 | `00_PROJECT_SPEC.md` | 项目 SSOT：目标/边界/原则/分层/生命周期/commit/review |
| 01 | `01_ARCHITECTURE_SPEC.md` | 系统架构：分层/微内核/DDD/事件驱动/各 Runtime |
| 02 | `02_DIRECTORY_SPEC.md` | 目录规范：每目录职责/边界/可改性 |
| 03 | `03_IMPORT_SPEC.md` | Import 规范：依赖矩阵/禁循环（AI 最重要） |
| 04 | `04_PROTOCOL_SPEC.md` | 通信协议：Message/Event/Task/Graph/... |
| 05 | `05_API_SPEC.md` | API 契约：27 接口 × Request/Response/Error/Timeout/Retry/Version |
| 06 | `06_SCHEMA_SPEC.md` | 数据 Schema（Pydantic v2，含迁移计划） |
| 07 | `07_EVENT_SPEC.md` | 事件总线：8 事件/生命周期/可靠性/追踪 |
| 08 | `08_AGENT_SPEC.md` | Agent Runtime：生命周期/API/Prompt/Memory/Tool/... |
| 09 | `09_DEVELOPMENT_SPEC.md` | 开发流程：Spec→Contract→API→Impl→Test→Doc |
| 10 | `10_INTERFACE_BOUNDARY_SPEC.md` | 接口边界：并行开发核心（谁调谁/异步/网关/EventBus） |
| 11 | `11_AI_CODING_SPEC.md` | AI 编码规范：给 AI Agent 的必读/范围/禁改/测试/冲突 |
| 12 | `12_TECH_STACK_SPEC.md` | 技术栈：语言/运行时/框架/库/工具链/版本约束 |
| 13 | `plans/13_FRONTEND_BACKEND_PLAN.md` | 前后端开发全流程计划（含后端↔智能体双向调用/DI 端口） |
| 14 | `plans/14_CYBERDEFENSE_SOLUTION_PLAN.md` | 赛事作品总体方案（超长程攻防/动态异构拓扑/低熵路由/记忆压缩/端边云/3 场景） |
| 15 | `plans/15_CYBERDEFENSE_TASKS.md` | 赛事作品实施任务清单（P1-P7 增量交付，含核心算法 TDD） |

> 冲突优先级：`00_PROJECT_SPEC` > `04_PROTOCOL_SPEC` ≈ `05_API_SPEC` ≈ `06_SCHEMA_SPEC` > 其余编号规范 > 各模块 `AGENT.md`。

## 目录导航
详见 `developer/specs/02_DIRECTORY_SPEC.md`。每个目录/子模块均有独立 `AGENT.md` 规定职责、读取目录、禁止修改目录、输出、依赖、接口、测试方式、日志/Prompt/配置位置。

## README 动态维护
根 `README.md` 由 `tooling/scripts/gen_readme.py` 扫描仓库实际结构自动生成（目录树、AGENT.md 计数、api 接口表、文件统计）。目录结构或 api 变动后运行 `python3 tooling/scripts/gen_readme.py` 刷新，勿手改自动生成段。

---

## 📋 模块实现总览

> 原 `MODULE.md` 内容，已合并至此。逐层介绍 AegisOS 每个大模块「是什么、做了什么、下面有哪些子模块」，帮助新人快速理解整个工程的代码实现现状。

### 📊 全局仪表盘

| # | 大模块 | 是什么 | 代码文件 | 测试数 | 实现状态 |
|---|--------|--------|---------|--------|---------|
| 1 | `protocol/` | 契约层 — 全系统唯一数据类型定义 | 10 `.py` | 6 | ✅ 核心完成 |
| 2 | `aegisos_agents/` | 智能体域 — 认知核心，五层架构 | 30+ `.py` | 100+ | ✅ 核心算法完成 / ✅ SDK S1-S4+R4-R6 / ✅ 编排器 / ✅ Plan+Goal 范式 / ✅ P2 记忆/感知/工具补全 |
| 3 | `backend/` | 应用层 — FastAPI REST + WS + SSE + DB | 20+ `.py` | — | ✅ REST+WS+SSE+DB 可用 / ✅ 攻防端点 F |
| 4 | `frontend/` | 表现层 — React + Vite AI Native IDE | 30+ `.ts/.tsx` | — | ✅ Chat 联调 / ✅ 攻防视图 G / 🔲 Canvas/Monitor/Replay |
| 5 | `infrastructure/` | 基建层 — 传输 · 节点 · 交付 | 1 `.py` | 0 | 🔲 仅 API 协议定义 |
| 6 | `observability/` | 可观测层 — 监控 · 基准 · 可视化 | 10+ `.py` | 41 | ✅ H5 完成（MetricsCollector/Timeline/Benchmark/Evaluator/Visualization） |
| 7 | `data/` | 数据层 — 数据集 · 模型 schema | 1 `.py` | 0 | 🔲 仅 API 协议 + SQLite |
| 8 | `tooling/` | 工程支撑 — 脚本 · 配置 | 4 `.py` | 0 | ✅ 3 脚本可用 |
| 9 | `developer/` | 规范层 — SSOT 规范 + roadmap | 0 `.py` | — | ✅ 规范就位 |
| 10 | `tests/` | 测试 — 346 个测试全通过 | 52 `.py` | 346 | ✅ 全覆盖 |

**模块依赖关系**：

```
developer/specs  ← 定义规范（唯一真相源 SSOT）
       ↓
protocol/        ← 唯一契约（所有域引用）
       ↓
aegisos_agents/api       ← 公共接口（5 个 Protocol + 3 个 DI 端口）
       ↓                ↑
backend/api  ← 调用 aegisos_agents.api
       ↓
frontend/services ← 调用 backend REST API
```

> **铁律**：跨域调用仅经 `from {domain}.api import ...`，禁止直接 import 内部子包。数据契约只用 `protocol/` 类型。

---

### 1. `protocol/` — 契约层

#### 是什么
全系统**唯一**的数据类型定义层。所有跨模块通信的参数、返回值、消息载体必须使用 `protocol/` 里定义的类型，禁止任何模块自造并行结构。这是整个工程的「宪法」。

#### 做了什么
定义了 10 个 `.py` 文件，覆盖消息通信、事件总线、智能体注册、任务调度、记忆包、动态异构图、工具调用、心跳、端边云同步，以及攻防专用的 8 个 dataclass。

#### 子模块（10 个文件）

| 文件 | 核心类型 | 功能说明 |
|------|---------|---------|
| `message.py` | `Message` · `NodeRef` | **消息信封**：跨模块通信的统一载体 |
| `event.py` | `EventType`(8 种) · `Event` | **事件总线**：8 种事件类型 |
| `agent.py` | `Agent` · `AgentStatus` | **智能体注册**：agent_id/name/role/capabilities/status/trust_score |
| `scheduler.py` | `Task` · `TaskStatus` · `RetryPolicy` | **任务调度**：任务生命周期。⚠️ Task 缺 payload 字段 |
| `memory.py` | `MemoryPacket` | **记忆包**：task_id/kind/summary/working/episodic/compression/recent |
| `graph.py` | `Graph` · `GraphNode` · `GraphEdge` · `GraphDiff` · `NodeKind` | **动态异构图** |
| `tool.py` | `ToolCall` · `ToolResult` · `ToolSpec` | **工具调用契约** |
| `heartbeat.py` | `Heartbeat` | **心跳**：Agent 存活检测 |
| `sync.py` | `SyncStatus` · `SyncOp` | **端边云同步** |
| `cyber.py` | `Asset` · `VulnFinding` · `AttackStep` · `AttackChain` · `Alert` · `DefenseAction` · `ResponsePlan` · `ThreatIntel` | **攻防协议类型**（8 个 dataclass） |

#### 测试
`tests/protocol/test_cyber.py` — 6 个测试，验证 8 个攻防类型的字段、序列化、反序列化。

#### 未实现
- `cyber.py` 中 `ThreatIntel` 仅基础结构，无 ATT&CK 技战术映射。

📎 各文件字段详解：[`protocol/AGENT.md`](protocol/AGENT.md) · 规范：[`04_PROTOCOL_SPEC.md`](developer/specs/04_PROTOCOL_SPEC.md)

---

### 2. `aegisos_agents/` — 智能体域

#### 是什么
系统的**认知核心**，实现五层架构：感知 → 规划 → 行动 → 记忆 → 工具。群体智能协同推理引擎的核心代码所在。

#### 做了什么
- **规划引擎**：活跃子图过滤、低熵稀疏路由（Top-K=3）、异构选举（点积匹配）、端边云卸载调度
- **记忆子系统**：上下文压缩（超预算时保留 decision+recent）和记忆唤醒（关键词匹配 Top-5）
- **攻防 Agent**：11 个 Agent 全部完成 — 红队 4 个、蓝队 5 个、紫队 2 个
- **感知层**：神经符号闭环（符号规则验证 + LLM 重新生成 → 迭代修复）
- **工具层**：多模型路由（gpt→OpenAI, claude→Anthropic, local→本地）
- **公共接口**：5 个 Protocol 接口 + 3 个 DI 端口

#### openai-agents SDK 集成

> ✅ S1-S4 完成 · ✅ R4-R5 完成。详见 `aegisos_agents/AGENT.md`「🔧 openai-agents SDK 集成状态」段 + `developer/plan.md`。

| 能力 | 状态 | 说明 |
|------|------|------|
| `StructuredAgent[T]` 基类 | ✅ | 封装 SDK `Agent` + `Runner.run_sync` + `output_type`（Pydantic BaseModel） |
| 11 个攻防 Agent 迁移 | ✅ | 全部继承 `StructuredAgent[T]`，无 `json.loads` |
| `SDKProvider` + `MockSDKModel` | ✅ | 双模式：Mock（`AEGIS_USE_MOCK=1`）/ 火山引擎 ARK 真实 API |
| `CyberOrchestrator` 编排器 | ✅ | 9 个 SDK Agent 装配 + handoffs + guardrails + tracing + FunctionTool |
| `neuro_symbolic.py` 迁移 | ✅ R4.1 | 已迁移到 `NeuroSymbolicAgent(StructuredAgent)` |
| 旧 `base.py` 接口清理 | ✅ R5.1 | `ModelProvider` Protocol 已删除 |
| 流式 SSE | ✅ R5.3 | `_run_streamed` + `backend/routers/stream.py` |
| 事件总线 | ✅ R5.4 | AgentHooks → EventBus 发布 |

📎 五层架构详解 + 子模块状态：[`aegisos_agents/AGENT.md`](aegisos_agents/AGENT.md) · 规范：[`08_AGENT_SPEC.md`](developer/specs/08_AGENT_SPEC.md)

---

### 3. `backend/` — 应用层（FastAPI）

#### 是什么
后端应用层，采用 **Router-Service-Repository-Model** 四层架构 + Core 网关入口，对外提供 REST API + WebSocket + SSE 实时通信。

#### 做了什么
- **FastAPI 应用**：完整的 app 创建 + CORS + 请求追踪中间件 + lifespan 数据库初始化
- **网关鉴权**：`/api/v1/*` 前缀路由 + X-API-Key header 鉴权（`aegis-dev-key`）
- **10+ REST 端点**：health / sessions / tasks / agents / graph / memory / tools / metrics / replay / stream + **攻防端点** range/attack/defense/threat
- **实时通信**：SSE 事件推送 + WebSocket 双向流 + 流式输出
- **数据持久化**：SQLAlchemy async + aiosqlite，Session/Task 实体 + 仓储 + 转换器
- **DI 组合根**：`composition.py` 装配 DB + 仓储 + 服务 + 14 Agent 注册 + CyberOrchestrator 注入

#### 未实现
- 🔲 WebSocket 双向流完善
- 🔲 Task payload 字段（当前 MockRuntime.run() 用 getattr 从 goal 解析）

📎 架构 + 端点详解：[`backend/AGENT.md`](backend/AGENT.md) · 规范：[`05_API_SPEC.md`](developer/specs/05_API_SPEC.md) · [`10_INTERFACE_BOUNDARY_SPEC.md`](developer/specs/10_INTERFACE_BOUNDARY_SPEC.md)

---

### 4. `frontend/` — 表现层（React + Vite）

#### 是什么
AI Native IDE 前端，采用 Controller-Service-Lib + Views 模式 + 5 个视图（Chat / Canvas / Graph / Monitor / Replay）。

#### 做了什么
- **类型系统**：`gen_ts_types.py` 自动生成的 36 个 TS 类型
- **全局状态**：Zustand store 管理 session/aegisos_agents/chatMessages/graph/isSending
- **API 客户端**：统一 HTTP 客户端（baseURL + X-API-Key header）
- **5 个 REST 服务**：agents / sessions / tasks / memory / graph
- **实时通信**：SSE + WebSocket 封装
- **ChatView 完整实现**：Agent 选择 + 消息收发 + 任务提交 + 状态轮询 + 自动滚动
- **攻防视图（4 面板）**：RedTeamPanel（攻击链 DAG）+ BlueTeamPanel（防御看板）+ PurpleTeamPanel（时序回放）+ ThreatIntelPanel（ATT&CK 情报表）
- **5 个视图骨架**：chat ✅ / cyber ✅ / canvas 🔲 / monitor 🔲 / replay 🔲

#### 未实现
- 🔲 CanvasView / MonitorView / ReplayView（replay 数据源 H5.2 已完成）

📎 架构 + ChatView 详解：[`frontend/AGENT.md`](frontend/AGENT.md) · 计划：[`plans/13_FRONTEND_BACKEND_PLAN.md`](developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md)

---

### 5. `infrastructure/` — 基建层

#### 是什么
基建层，负责传输通信、端边云节点管理、部署交付。赛事要求包含 Docker 沙箱靶场。

#### 做了什么
- **API 协议定义**：4 个 Protocol 接口（CommunicationAPI / NodeRegistryAPI / SyncAPI / DeploymentAPI）

#### 未实现
- 🔲 Docker 沙箱靶场（赛事 H1 核心需求）
- 🔲 端边云通信与节点管理全部待实现

📎 目录 + 赛事需求：[`infrastructure/AGENT.md`](infrastructure/AGENT.md)

---

### 6. `observability/` — 可观测层

#### 是什么
可观测层，分为三个子域：inspect（监控 · 回放）、measure（基准 · 评测）、present（可视化）。

#### 做了什么
- **API 协议定义**：6 个 Protocol 接口（MonitorAPI / TraceAPI / ReplayAPI / BenchmarkAPI / EvaluationAPI / VisualizationAPI）
- **H5 可观测评测**：✅ 全部完成 — `MetricsCollector`（监控+告警）+ `Timeline`/`ReplayPlayer`（回放）+ `BenchmarkRunner`（性能基准）+ `Evaluator`（5 维度评测）+ `VisualizationService`（ECharts/React Flow 可视化）
- **Tracing**：`CyberTraceProcessor` + `CyberAgentHooks`（7 个生命周期回调）

#### 未实现
- 🔲 前端 MonitorView/ReplayView 对接（数据源已完成）

📎 目录 + 赛事需求：[`observability/AGENT.md`](observability/AGENT.md)

---

### 7. `data/` — 数据层

#### 是什么
数据层，管理数据集和模型 schema。赛事要求接入 Neo4j 和 Qdrant。

#### 做了什么
- **API 协议定义**：2 个 Protocol 接口（DatasetAPI / ModelSchemaAPI）
- **SQLite 数据库**：`aegisos.db` 文件（后端运行时自动生成）

#### 未实现
- 🔲 Neo4j 拓扑图 + ATT&CK 图接入（赛事 H2）
- 🔲 Qdrant 向量库接入（赛事 H2）

📎 目录 + 赛事需求：[`data/AGENT.md`](data/AGENT.md)

---

### 8. `tooling/` — 工程支撑

#### 是什么
工程支撑层，提供自动化脚本和配置文件。

#### 做了什么
- **3 个可用脚本**：`gen_readme.py` / `gen_ts_types.py` / `realign_agent_docs.py`
- **API 协议定义**：2 个 Protocol 接口（ConfigAPI / ScriptAPI）
- **配置文件**：backend.yaml + gateway.yaml

#### 未实现
- 🔲 `check_no_broadcast.py`（C4：检测低熵全广播违规）

📎 脚本 + 配置详解：[`tooling/AGENT.md`](tooling/AGENT.md)

---

### 9. `developer/` — 规范层

#### 是什么
项目「大脑」，存放唯一真相源（SSOT）的规范文档和 roadmap 阶段计划。**P0 规范未完成前不得写业务代码**。

#### 做了什么
- **15 个规范文件**（00-15）
- **roadmap P0-P7**：P0-P5 已完成，P6 部分完成，P7 未开始
- **CHANGELOG.md**：变更记录

📎 规范索引 + roadmap 进度：[`developer/AGENT.md`](developer/AGENT.md)

---

### 10. `tests/` — 测试

#### 是什么
测试目录，覆盖 Phase A-E 的全部单元测试。当前 59 个测试全部通过。

#### 测试分布

| 目录 | 测试数 | 覆盖内容 |
|------|--------|---------|
| `tests/protocol/` | 6 | 8 个攻防 dataclass |
| `tests/aegisos_agents/memory/` | 33 | 4 层记忆存储 + MemoryStore 闭环 + 压缩/唤醒 |
| `tests/aegisos_agents/planning/` | 10 | 活跃子图 + Top-K 路由 + 选举 + 调度 |
| `tests/aegisos_agents/tools/` | 5 | 多模型路由 |
| `tests/aegisos_agents/action/` | 23 | 11 个攻防 Agent + 神经符号闭环 |
| `tests/e2e/` | 5 | 场景 1 红→蓝→紫端到端 + B3 记忆闭环 |
| `tests/基础/` | 4 | 基础测试 |

#### 未实现
- 🔲 `tests/e2e/` 场景 2/3 端到端测试（超长程攻击链 / 端-边-云协同防御）

---

### 技术栈速查

| 层 | 技术栈 |
|----|--------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy(async) · aiosqlite · uvicorn |
| 前端 | React 18 · Vite 5.4.21 · Zustand 4.5 · TypeScript 5.6 |
| 协议 | Python `@dataclass`（§12 计划迁移 Pydantic） |
| AI SDK | openai-agents SDK · `StructuredAgent[T]` + `output_type`（Pydantic）· Mock/真实 API 双模式 |
| 数据库 | SQLite（`aegisos.db`）→ Neo4j + Qdrant（待接入） |
| 测试 | pytest · ruff · mypy · 94 tests passing |

### 快速启动

```bash
# 后端
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev

# 测试
.venv/bin/pytest tests/ -v
```
