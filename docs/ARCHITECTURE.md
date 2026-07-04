# AegisOS 模块实现总览

> 本文件对每个顶层域的实际**代码实现状态**做精确描述：已实现什么、未实现什么、关键文件在哪、测试覆盖如何。
> 最后更新：2026-07-04 · 55 个测试全通过

---

## 📊 总览仪表盘

| 域 | 代码文件 | 测试数 | 实现状态 | 模块文档 |
|----|---------|--------|---------|---------|
| [`protocol/`](#protocol) | 10 `.py` | 6 | ✅ 核心完成 | [MODULE.md](protocol/MODULE.md) |
| [`agents/`](#agents) | 20 `.py` | 41 | ✅ 核心算法完成 / 🔲 编排器+runtime 集成待补 | [MODULE.md](agents/MODULE.md) |
| [`backend/`](#backend) | 18 `.py` | — | ✅ REST+WS+SSE+DB 可用 | [MODULE.md](backend/MODULE.md) |
| [`frontend/`](#frontend) | 25 `.ts/.tsx` | — | ✅ Chat 联调 / 🔲 攻防视图待补 | [MODULE.md](frontend/MODULE.md) |
| [`infrastructure/`](#infrastructure) | 1 `.py` | 0 | 🔲 仅 API 协议定义 | [MODULE.md](infrastructure/MODULE.md) |
| [`observability/`](#observability) | 1 `.py` | 0 | 🔲 仅 API 协议定义 | [MODULE.md](observability/MODULE.md) |
| [`data/`](#data) | 1 `.py` | 0 | 🔲 仅 API 协议定义 + SQLite DB | [MODULE.md](data/MODULE.md) |
| [`tooling/`](#tooling) | 4 `.py` | 0 | ✅ 3 个脚本可用 | [MODULE.md](tooling/MODULE.md) |
| [`developer/`](#developer) | 0 `.py` | — | ✅ 规范+roadmap 就位 | [MODULE.md](developer/MODULE.md) |
| [`tests/`](#tests) | 26 `.py` | 55 | ✅ Phase A-E 覆盖 | — |

---

## protocol/ — 契约层（唯一数据契约）

**定位**：全系统唯一的数据类型定义，所有跨模块通信的参数/返回值必须使用 `protocol/` 类型，禁止自造并行结构。

### 已实现文件（10 个）

| 文件 | 核心类型 | 说明 |
|------|---------|------|
| [`message.py`](../protocol/message.py) | `Message` · `NodeRef` · `Envelope` | 消息信封，跨模块通信的统一载体 |
| [`event.py`](../protocol/event.py) | `EventType`(8 种) · `Event` | 事件总线类型：AgentStart/Finish · ToolCall/Finish · Retry · Rollback · MemoryUpdate · GraphUpdate |
| [`agent.py`](../protocol/agent.py) | `Agent` · `AgentStatus` | 智能体注册表条目 |
| [`task.py`](../protocol/scheduler.py) | `Task` · `TaskStatus` · `RetryPolicy` | 任务调度单元（⚠️ Task 缺 payload 字段） |
| [`memory.py`](../protocol/memory.py) | `MemoryPacket` | 记忆包：task_id/kind/summary/working/episodic/compression/recent |
| [`graph.py`](../protocol/graph.py) | `Graph` · `GraphNode` · `GraphEdge` · `GraphDiff` · `NodeKind` | 动态异构图 |
| [`tool.py`](../protocol/tool.py) | `ToolCall` · `ToolResult` · `ToolSpec` | 工具调用契约 |
| [`heartbeat.py`](../protocol/heartbeat.py) | `Heartbeat` | Agent 心跳 |
| [`sync.py`](../protocol/sync.py) | `SyncStatus` · `SyncOp` | 端边云同步操作 |
| [`cyber.py`](../protocol/cyber.py) | `Asset` · `VulnFinding` · `AttackStep` · `AttackChain` · `Alert` · `DefenseAction` · `ResponsePlan` · `ThreatIntel` | **攻防协议类型**（8 个 dataclass） |

### 测试覆盖（6 个）
`tests/protocol/test_cyber.py` — 验证 8 个攻防类型的字段、序列化、反序列化

### 未实现
- `cyber.py` 中 `ThreatIntel` 仅基础结构，无 ATT&CK 技战术映射

📎 详细文档：[`protocol/MODULE.md`](../protocol/MODULE.md) · 规范：[`04_PROTOCOL_SPEC.md`](../developer/specs/04_PROTOCOL_SPEC.md)

---

## agents/ — 智能体域

**定位**：系统的认知核心，五层架构：感知 → 规划 → 行动 → 记忆 → 工具。

### 子模块实现状态

#### `agents/planning/` — 规划引擎（✅ 核心算法完成）

| 文件 | 函数/类 | 功能 | 测试 |
|------|--------|------|------|
| [`engine/topology/topology.py`](../agents/planning/engine/topology/topology.py) | `active_subgraph()` | 按 capability + status(active/degraded) 过滤活跃子图 | 2 |
| [`engine/router/router.py`](../agents/planning/engine/router/router.py) | `route()` | 低熵稀疏路由 Top-K=3，按 affinity - load_penalty 排序 | 3 |
| [`engine/router/election.py`](../agents/planning/engine/router/election.py) | `elect()` | 异构选举：task_features · capability_vectors 点积最高者胜出 | 2 |
| [`engine/scheduler/scheduler.py`](../agents/planning/engine/scheduler/scheduler.py) | `schedule()` · `Model` | 端边云卸载：privacy=local→edge，latency<5s→edge，否则→cloud | 3 |

> 🔲 **未实现**：`planner/` · `orchestrator/` · `engine/workflow/` · `engine/eventbus/` 仅有 AGENT.md，编排器全空

#### `agents/memory/` — 记忆子系统（✅ 压缩+唤醒完成，🔲 10 子模块空）

| 文件 | 函数 | 功能 | 测试 |
|------|------|------|------|
| [`compression/compactor.py`](../agents/memory/compression/compactor.py) | `compress()` · `_token_estimate()` | 上下文压缩：超 budget 时保留 decision+recent，其余合并为 digest | 4 |
| [`recall/recaller.py`](../agents/memory/recall/recaller.py) | `recall()` | 记忆唤醒：trigger 关键词匹配 episodic+vector，decision 优先，Top-5 | 3 |

> 🔲 **未实现**：working/episodic/semantic/vector/archive/cache/checkpoint/reflection/retrieval/snapshot/sync 全部仅 AGENT.md

#### `agents/action/` — 攻防 Agent（✅ 11 个全部完成）

| Agent | 文件 | 核心方法 | 输入 → 输出 | 测试 |
|-------|------|---------|------------|------|
| 🔴 `recon` | [`recon/agent.py`](../agents/action/recon/agent.py) | `scan(target_range)` | 目标范围 → `list[Asset]` | 2 |
| 🔴 `vuln_correlator` | [`vuln_correlator/agent.py`](../agents/action/vuln_correlator/agent.py) | `correlate(assets, cve_db)` | 资产+CVE库 → `list[VulnFinding]` | 1 |
| 🔴 `exploit_planner` | [`exploit_planner/agent.py`](../agents/action/exploit_planner/agent.py) | `plan(findings)` | 漏洞列表 → `AttackChain` | 1 |
| 🔴 `lateral_move` | [`lateral_move/agent.py`](../agents/action/lateral_move/agent.py) | `plan_moves(chain)` | 攻击链 → 横向移动步骤 | 1 |
| 🔵 `detector` | [`detector/agent.py`](../agents/action/detector/agent.py) | `detect(events)` | 事件流 → `list[Alert]` | 2 |
| 🔵 `triage` | [`triage/agent.py`](../agents/action/triage/agent.py) | `triage(alerts)` | 告警列表 → 按严重度排序 | 1 |
| 🔵 `threat_hunt` | [`threat_hunt/agent.py`](../agents/action/threat_hunt/agent.py) | `hunt(alerts)` | 告警 → ATT&CK 假设 | 1 |
| 🔵 `ir_planner` | [`ir_planner/agent.py`](../agents/action/ir_planner/agent.py) | `plan_response(hypotheses)` | 假设 → `ResponsePlan`(含 rollback) | 2 |
| 🔵 `forensics` | [`forensics/agent.py`](../agents/action/forensics/agent.py) | `investigate(alert)` | 告警 → 取证报告 | 1 |
| 🟣 `critic` | [`critic/agent.py`](../agents/action/critic/agent.py) | `critique(chain_or_plan)` | 对抗性校验，红蓝产出反驳 | 2 |
| 🟣 `reviewer` | [`reviewer/agent.py`](../agents/action/reviewer/agent.py) | `review(inputs)` | 一致性审查，最终结论 | 1 |

#### `agents/perception/` — 感知层（✅ 神经符号闭环完成）

| 文件 | 函数/类 | 功能 | 测试 |
|------|--------|------|------|
| [`reasoning/neuro_symbolic.py`](../agents/perception/reasoning/neuro_symbolic.py) | `validate_chain()` · `NeuroSymbolicLoop` | 符号验证（allowed_techniques 规则） + LLM 重新生成 → 迭代修复 | 4 |

> 🔲 **未实现**：`context/` · `reflection/` 仅有 AGENT.md

#### `agents/tools/` — 工具层（✅ 多模型兼容完成）

| 文件 | 类 | 功能 | 测试 |
|------|-----|------|------|
| [`llms/base.py`](../agents/tools/llms/base.py) | `LLMRequest` · `LLMResponse` · `ModelProvider` | LLM 调用抽象基类 | — |
| [`llms/mock_provider.py`](../agents/tools/llms/mock_provider.py) | `MockProvider` | 测试用 Mock 实现 | — |
| [`llms/model_router.py`](../agents/tools/llms/model_router.py) | `ModelRouter` | 多模型路由：gpt→OpenAI, claude→Anthropic, local/*→本地, 按 tier(edge/cloud) 映射 | 5 |

#### `agents/api/` — 公共接口（✅ 5 接口定义完成）

| 接口 | 方法 |
|------|------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` |
| `ExecutionAPI` | `execute(call)` |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` |

> 另有 `ports.py`：`PersistencePort` · `SessionPort` · `TaskUpdatePort`（DI 端口）

📎 详细文档：[`agents/MODULE.md`](../agents/MODULE.md) · 规范：[`08_AGENT_SPEC.md`](../developer/specs/08_AGENT_SPEC.md)

---

## backend/ — 应用层（FastAPI）

**定位**：Router-Service-Repository-Model 四层 + Core 核心层，提供 REST API + WebSocket + SSE。

### 已实现

| 层 | 文件 | 功能 |
|----|------|------|
| **入口** | [`main.py`](../backend/main.py) | FastAPI app + CORS + TraceMiddleware + lifespan(DB init) |
| **核心层** | [`core/routes.py`](../backend/core/routes.py) | `/api/v1` 前缀 + `verify_api_key` 鉴权 + 路由聚合 |
| | [`core/auth.py`](../backend/core/auth.py) | X-API-Key header 校验 |
| | [`core/middleware.py`](../backend/core/middleware.py) | TraceMiddleware（请求追踪 ID） |
| **REST** | `routers/sessions.py` | `POST /sessions` · `GET /sessions` |
| | `routers/tasks.py` | `POST /tasks` · `GET /tasks` · `POST /tasks/{id}/cancel` |
| | `routers/agents.py` | `GET /agents` · `POST /agents/{id}/invoke` |
| | `routers/graph.py` | `GET /graph` |
| | `routers/memory.py` | `GET /memory` · `POST /memory` |
| | `routers/tools.py` | `POST /tools/invoke` |
| | `routers/metrics.py` | `GET /metrics` |
| | `routers/replay.py` | `GET /replay/{session_id}` |
| | `routers/health.py` | `GET /health`（无鉴权） |
| **SSE** | `routers/sse.py` | `GET /api/v1/events/stream` 服务器推送 |
| **WebSocket** | `routers/ws.py` | `WS /ws/v1/stream` 双向流 |
| **Service** | `services/session_service.py` · `task_service.py` · `agent_service.py` · `graph_service.py` · `memory_service.py` | 业务逻辑层 |
| **Repository** | `repositories/database.py` · `repositories.py` | SQLAlchemy async + aiosqlite |
| **Model** | `models/entities.py` · `converters.py` | ORM 实体 + protocol↔Entity 转换 |
| **DI** | [`core/composition.py`](../backend/core/composition.py) | 组合根：装配 DB + 仓储 + 服务 + 14 Agent 注册 + MockRuntime |

### API 鉴权
所有 `/api/v1/*` 端点需要 `X-API-Key: aegis-dev-key` header（`/health` 除外）。

### 未实现
- 🔲 攻防端点 `/api/v1/range/*`（靶场/拓扑/攻击/攻击链/防御）

📎 详细文档：[`backend/MODULE.md`](../backend/MODULE.md)

---

## frontend/ — 表现层（React + Vite）

**定位**：AI Native IDE 前端，Controller-Service-Mapper 模式 + 5 视图。

### 已实现

| 层 | 关键文件 | 功能 |
|----|---------|------|
| **类型** | [`src/protocol/types.ts`](../frontend/src/protocol/types.ts) | 自动生成（`gen_ts_types.py`），36 个 TS 类型映射 protocol/*.py |
| | `src/protocol/frontend-types.ts` | `ViewName` · 路由类型 |
| **Store** | `mappers/store/index.ts` | Zustand 全局状态：session/agents/chatMessages/graph/isSending |
| **API Client** | `mappers/apimappers/client.ts` | 统一 HTTP 客户端（baseURL + X-API-Key） |
| **Services** | `services/api/agents.ts` · `sessions.ts` · `tasks.ts` · `memory.ts` · `graph.ts` | REST API 调用封装 |
| | `services/graph/index.ts` | 图数据服务 |
| | `services/realtime/sse.ts` · `ws.ts` | SSE + WebSocket 实时通信 |
| | `services/session/index.ts` | 会话管理 |
| **Controllers** | `controllers/interaction.ts` · `events.ts` · `routes.ts` | 交互/事件/路由控制 |
| **Views** | `views/chat/ChatView.tsx` | ✅ **完整实现**：Agent 选择 + 消息收发 + 任务提交 |
| | `views/canvas/` · `graph/` · `monitor/` · `replay/` | 🔲 占位符组件 |

### ChatView 功能
- Agent 下拉选择（14 个 Agent）
- 消息发送 + 响应展示
- 任务创建 + 状态轮询
- 自动滚动

### 未实现
- 🔲 CanvasView：攻击链 DAG 可视化（需 React Flow）
- 🔲 MonitorView：防御看板
- 🔲 ReplayView：时序回放
- 🔲 前端 cyber 类型（protocol/cyber.py 未映射到 TS）

📎 详细文档：[`frontend/MODULE.md`](../frontend/MODULE.md)

---

## infrastructure/ — 基建层

**定位**：传输 · 节点(端·云) · 交付（部署）。

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../infrastructure/api/__init__.py) | 4 个 Protocol 接口定义：`CommunicationAPI` · `NodeRegistryAPI` · `SyncAPI` · `DeploymentAPI` |

### 未实现（全空，仅 AGENT.md）
- 🔲 `transport/communication/` — 传输层
- 🔲 `nodes/edge/` — 端侧节点
- 🔲 `nodes/cloud/` — 云侧节点
- 🔲 `delivery/deployment/` — 部署交付
- 🔲 Docker 沙箱靶场

📎 详细文档：[`infrastructure/MODULE.md`](../infrastructure/MODULE.md)

---

## observability/ — 可观测层

**定位**：inspect(监控·回放) · measure(基准·评测) · present(可视化)。

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../observability/api/__init__.py) | 6 个 Protocol 接口：`MonitorAPI` · `TraceAPI` · `ReplayAPI` · `BenchmarkAPI` · `EvaluationAPI` · `VisualizationAPI` |

### 未实现（全空，仅 AGENT.md）
- 🔲 `inspect/monitor/` · `inspect/replay/`
- 🔲 `measure/benchmark/` · `measure/evaluation/`
- 🔲 `present/visualization/`

📎 详细文档：[`observability/MODULE.md`](../observability/MODULE.md)

---

## data/ — 数据层

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../data/api/__init__.py) | 2 个 Protocol 接口：`DatasetAPI` · `ModelSchemaAPI` |
| `aegisos.db` | SQLite 数据库文件（后端运行时生成） |

### 未实现
- 🔲 `datasets/` — 仅 AGENT.md
- 🔲 `models/` — 仅 AGENT.md（Neo4j 拓扑图 + Qdrant 向量库待接入）

📎 详细文档：[`data/MODULE.md`](../data/MODULE.md)

---

## tooling/ — 工程支撑

### 已实现（3 个脚本可用）

| 脚本 | 功能 |
|------|------|
| [`scripts/gen_readme.py`](../tooling/scripts/gen_readme.py) | 自动生成 README 目录树 + 仓库统计 |
| [`scripts/gen_ts_types.py`](../tooling/scripts/gen_ts_types.py) | 从 protocol/*.py 自动生成前端 TS 类型定义 |
| [`scripts/realign_agent_docs.py`](../tooling/scripts/realign_agent_docs.py) | 对齐各模块 AGENT.md 交叉引用 |
| `scripts/add_agent_crossrefs.pl` | Perl 脚本：批量添加 Agent 交叉引用 |
| `configs/backend.yaml` | 后端配置（CORS origins 等） |
| `configs/gateway.yaml` | 网关配置 |
| `api/__init__.py` | 2 个 Protocol 接口：`ConfigAPI` · `ScriptAPI` |

📎 详细文档：[`tooling/MODULE.md`](../tooling/MODULE.md)

---

## developer/ — 规范层

### 已实现
- `specs/` — 15 个规范文件（00-15），唯一真相源（SSOT）
- `roadmap/` — P0-P7 阶段计划，每个阶段独立目录
- `CHANGELOG.md` — 变更记录

📎 详细文档：[`developer/MODULE.md`](../developer/MODULE.md)

---

## tests/ — 测试

### 测试分布（55 个测试，全通过）

| 目录 | 测试文件 | 测试数 | 覆盖内容 |
|------|---------|--------|---------|
| `tests/protocol/` | `test_cyber.py` | 6 | 8 个攻防 dataclass 字段/序列化 |
| `tests/agents/memory/` | `test_compactor.py` · `test_recaller.py` | 7 | 上下文压缩 + 记忆唤醒 |
| `tests/agents/planning/` | `test_topology.py` · `test_router.py` · `test_election.py` · `test_scheduler.py` | 10 | 活跃子图 + Top-K 路由 + 选举 + 调度 |
| `tests/agents/tools/` | `test_model_router.py` | 5 | 多模型路由 |
| `tests/agents/action/` | 11 个 `test_*.py` | 15 | 11 个攻防 Agent |
| `tests/agents/perception/` | `test_neuro_symbolic.py` | 4 | 神经符号闭环 |

### 未实现
- 🔲 `tests/e2e/` — 端到端集成测试（场景 1 红→蓝→紫完整链路）

---

## 模块依赖关系

```
developer/specs ← 定义规范（SSOT）
        ↓
protocol/ ← 唯一契约（所有域引用）
        ↓
agents/api ← 公共接口（5 个 Protocol）
        ↓                ↑
backend/api ← 调用 agents.api
        ↓
frontend/services ← 调用 backend REST API
```

**铁律**：跨域调用仅经 `from {domain}.api import ...`，禁止直接 import 内部子包。
