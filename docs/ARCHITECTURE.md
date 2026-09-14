# AegisOS 架构仪表盘

> 本文件对每个顶层域的实际**代码实现状态**做精确描述：已实现什么、未实现什么、关键文件在哪、测试覆盖如何。
> 各域详细实现文档已合并至对应 `AGENT.md` 末尾「📋 模块实现详解」段；全局模块总览已合并至根 `AGENT.md` 末尾「📋 模块实现总览」段。
> 最后更新：2026-09-08 · Python 654 passed · 前端 44 passed · P5/P6 ✅ · 演示版 P7 ✅

---

## 📊 总览仪表盘

| 域 | 代码文件 | 测试数 | 实现状态 | 模块文档 |
|----|---------|--------|---------|---------|
| [`protocol/`](#protocol) | 10 `.py` | 6 | ✅ 核心完成 | [AGENT.md](../protocol/AGENT.md) |
| [`aegisos_agents/`](#agents) | 99 `.py` | Python 全量回归的一部分 | ✅ 核心算法完成 / ✅ SDK S1-S4+R4-R6 / ✅ 编排器 / ✅ Plan+Goal+ReAct 范式 / ✅ P2 感知/记忆/工具补全 | [AGENT.md](../aegisos_agents/AGENT.md) |
| [`backend/`](#backend) | 20+ `.py` | — | ✅ REST+WS+SSE+DB 可用 / ✅ 攻防端点 F | [AGENT.md](../backend/AGENT.md) |
| [`frontend/`](#frontend) | 35+ `.ts/.tsx` | 24 | ✅ Chat/攻防/TaskMap/Monitor/演练历史/端边云配置演示 | [AGENT.md](../frontend/AGENT.md) |
| [`infrastructure/`](#infrastructure) | 15+ `.py` | 50+ | ✅ 节点/注册/派发/JSON-TCP/Docker 沙箱基础；🔲 真实容器实测 | [AGENT.md](../infrastructure/AGENT.md) |
| [`observability/`](#observability) | 10+ `.py` | 41 | ✅ H5 完成（监控/回放/基准/评测/可视化） | [AGENT.md](../observability/AGENT.md) |
| [`data/`](#data) | 9+ `.py` | 18 | ✅ H2 完成（InMemory/Neo4j/Qdrant 双实现 + ATT&CK 数据集 + memory 对接） | [AGENT.md](../data/AGENT.md) |
| [`tooling/`](#tooling) | 4 `.py` | 0 | ✅ 3 个脚本可用 | [AGENT.md](../tooling/AGENT.md) |
| [`developer/`](#developer) | 0 `.py` | — | ✅ 规范+roadmap 就位 | [AGENT.md](../developer/AGENT.md) |
| [`tests/`](#tests) | 60+ `.py` | Python 594 + 前端 24 | ✅ 演示版全量回归通过 | — |

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

### 当前状态
- `ThreatIntel` 已包含 ATT&CK 技术映射字段

📎 详细文档：[`protocol/AGENT.md`](../protocol/AGENT.md) 末尾「📋 模块实现详解」 · 规范：[`04_PROTOCOL_SPEC.md`](../developer/specs/04_PROTOCOL_SPEC.md)

---

## aegisos_agents/ — 智能体域

**定位**：系统的认知核心，五层架构：感知 → 规划 → 行动 → 记忆 → 工具。

### 🔧 openai-agents SDK 集成状态

> ✅ S1-S4 完成 · ✅ R4-R5 完成。详见 `aegisos_agents/AGENT.md` + `developer/plan.md`。

| 能力 | 状态 |
|------|------|
| `StructuredAgent[T]` 基类（SDK `Agent` + `Runner.run_sync` + `output_type`） | ✅ |
| 11 个攻防 Agent（红 4 + 蓝 5 + 紫 2，全部继承 StructuredAgent，无 `json.loads`） | ✅ |
| `SDKProvider` + `MockSDKModel`（双模式：Mock / 火山引擎 ARK） | ✅ |
| `CyberOrchestrator`（9 个 SDK Agent 装配 + handoffs + guardrails + tracing + FunctionTool） | ✅ |
| `neuro_symbolic.py` 迁移 | ✅ R4.1 |
| `react_mode.py` think→act→observe 循环 | ✅ AP2.1 |
| `react_support.py` + 五 Agent `*_react()` | ✅ AP2.2-AP2.6 |
| SDK `handoffs` / `guardrails` / `tracing` | ✅ R4 |
| 旧 `base.py` 接口清理 + 流式 SSE + 事件总线 | ✅ R5 |

### 子模块实现状态

#### `aegisos_agents/planning/` — 规划引擎（✅ 核心算法完成）

| 文件 | 函数/类 | 功能 | 测试 |
|------|--------|------|------|
| [`engine/topology/topology.py`](../aegisos_agents/planning/engine/topology/topology.py) | `active_subgraph()` | 按 capability + status(active/degraded) 过滤活跃子图 | 2 |
| [`engine/router/router.py`](../aegisos_agents/planning/engine/router/router.py) | `route()` | 低熵稀疏路由 Top-K=3，按 affinity - load_penalty 排序 | 3 |
| [`engine/router/election.py`](../aegisos_agents/planning/engine/router/election.py) | `elect()` | 异构选举：task_features · capability_vectors 点积最高者胜出 | 2 |
| [`engine/scheduler/scheduler.py`](../aegisos_agents/planning/engine/scheduler/scheduler.py) | `schedule()` · `Model` | 端边云三层卸载：device/edge/cloud，privacy=local→device，latency<1s→device，latency<5s→edge，否则→cloud，降级端→边→云 | 8 |

> ✅ **全部已实现**：`planner/` · `engine/workflow/` · `engine/eventbus/` 均已实现。
> ✅ **CyberOrchestrator**：`orchestrator/cyber_orchestrator.py` 已用 SDK Agent 实现红蓝紫攻防链编排（含 handoffs/guardrails/tracing/FunctionTool）。

#### `aegisos_agents/memory/` — 记忆子系统（✅ B3 四层+集成层完成，✅ P2 7 子模块完成）

| 文件 | 函数 | 功能 | 测试 |
|------|------|------|------|
| [`compression/compactor.py`](../aegisos_agents/memory/compression/compactor.py) | `compress()` · `_token_estimate()` | 上下文压缩：超 budget 时保留 decision+recent，其余合并为 digest | 4 |
| [`recall/recaller.py`](../aegisos_agents/memory/recall/recaller.py) | `recall()` | 记忆唤醒：trigger 关键词匹配 episodic+vector，decision 优先，Top-5 | 3 |
| [`working/store.py`](../aegisos_agents/memory/working/store.py) | `WorkingMemory` | 工作记忆：按 session_id 隔离的上下文栈 | 4 |
| [`episodic/store.py`](../aegisos_agents/memory/episodic/store.py) | `EpisodicMemory` | 情景记忆：跨会话历史经验累积 | 3 |
| [`semantic/store.py`](../aegisos_agents/memory/semantic/store.py) | `SemanticMemory` | 语义记忆/知识库：8 个 ATT&CK 种子技战术 | 4 |
| [`vector/store.py`](../aegisos_agents/memory/vector/store.py) | `VectorMemory` | 向量记忆：余弦相似度 Top-K 检索 | 5 |
| [`memory_store.py`](../aegisos_agents/memory/memory_store.py) | `MemoryStore` | 集成存储：聚合四层 + compactor + recaller，认知循环中枢 | 10 |

> ✅ **P2 完成（2026-08-01）**：archive/cache/checkpoint/reflection/retrieval/snapshot/sync 7 子模块全部实现。

#### `aegisos_agents/action/` — 攻防 Agent（✅ 11 个全部完成）

| Agent | 文件 | 核心方法 | 输入 → 输出 | 测试 |
|-------|------|---------|------------|------|
| 🔴 `recon` | [`recon/agent.py`](../aegisos_agents/action/recon/agent.py) | `scan(target_range)` · `scan_react(target_range, executor)` | 目标范围 → `list[Asset]` / `ReactResult[list[Asset]]` | 5 |
| 🔴 `vuln_correlator` | [`vuln_correlator/agent.py`](../aegisos_agents/action/vuln_correlator/agent.py) | `correlate(assets)` · `correlate_react(assets, executor)` | 资产+CVE库 → `list[VulnFinding]` / `ReactResult[list[VulnFinding]]` | 3 |
| 🔴 `exploit_planner` | [`exploit_planner/agent.py`](../aegisos_agents/action/exploit_planner/agent.py) | `plan(findings)` | 漏洞列表 → `AttackChain` | 1 |
| 🔴 `lateral_move` | [`lateral_move/agent.py`](../aegisos_agents/action/lateral_move/agent.py) | `plan_moves(chain)` | 攻击链 → 横向移动步骤 | 1 |
| 🔵 `detector` | [`detector/agent.py`](../aegisos_agents/action/detector/agent.py) | `detect(events)` · `detect_react(events, executor)` | 事件流 → `list[Alert]` / `ReactResult[list[Alert]]` | 3 |
| 🔵 `triage` | [`triage/agent.py`](../aegisos_agents/action/triage/agent.py) | `triage(alerts)` | 告警列表 → 按严重度排序 | 2 |
| 🔵 `threat_hunt` | [`threat_hunt/agent.py`](../aegisos_agents/action/threat_hunt/agent.py) | `hunt(alerts)` · `hunt_react(alerts, executor)` | 告警 → ATT&CK 假设 / `ReactResult[list[dict]]` | 3 |
| 🔵 `ir_planner` | [`ir_planner/agent.py`](../aegisos_agents/action/ir_planner/agent.py) | `plan_response(hypotheses)` | 假设 → `ResponsePlan`(含 rollback) | 2 |
| 🔵 `forensics` | [`forensics/agent.py`](../aegisos_agents/action/forensics/agent.py) | `investigate(plan)` · `investigate_react(plan, executor)` | 响应计划 → 取证报告 / `ReactResult[dict]` | 2 |
| 🟣 `critic` | [`critic/agent.py`](../aegisos_agents/action/critic/agent.py) | `critique(chain_or_plan)` | 对抗性校验，红蓝产出反驳 | 2 |
| 🟣 `reviewer` | [`reviewer/agent.py`](../aegisos_agents/action/reviewer/agent.py) | `review(inputs)` | 一致性审查，最终结论 | 2 |

#### `aegisos_agents/perception/` — 感知层（✅ 神经符号闭环 + AP2.1 ReAct 内核完成）

| 文件 | 函数/类 | 功能 | 测试 |
|------|--------|------|------|
| [`reasoning/neuro_symbolic.py`](../aegisos_agents/perception/reasoning/neuro_symbolic.py) | `validate_chain()` · `NeuroSymbolicLoop` | 符号验证（allowed_techniques 规则） + LLM 重新生成 → 迭代修复 | 4 |
| [`reasoning/strategies/react_mode.py`](../aegisos_agents/perception/reasoning/strategies/react_mode.py) | `ReactMode` · `ReactDecision` · `ReactResult` | `think→act→observe` 循环、工具错误反馈、轨迹回放与最大轮数保护 | 10 |

> ✅ **P2 完成（2026-08-01）**：`context/`（TokenBudget + ContextManager）+ `reflection/`（ExecutionCritic + OutputScorer + FeedbackLoop）。

#### `aegisos_agents/tools/` — 工具层（✅ 多模型兼容 + SDK 适配完成）

| 文件 | 类 | 功能 | 测试 |
|------|-----|------|------|
| [`llms/sdk_provider.py`](../aegisos_agents/tools/llms/sdk_provider.py) | `SDKProvider` | SDK 适配器：桥接 `ModelProvider` → SDK `OpenAIChatCompletionsModel`，双模式 Mock/ARK | — |
| [`llms/mock_sdk_model.py`](../aegisos_agents/tools/llms/mock_sdk_model.py) | `MockSDKModel` | SDK Mock 适配器：将 `MockProvider` 包装为 SDK `ModelResponse` | — |
| [`llms/base.py`](../aegisos_agents/tools/llms/base.py) | `LLMRequest` · `LLMResponse` · `ModelProvider` | 旧 LLM 调用抽象基类（⚠️ R5 清理目标） | — |
| [`llms/mock_provider.py`](../aegisos_agents/tools/llms/mock_provider.py) | `MockProvider` | 测试用 Mock 实现 | — |
| [`llms/model_router.py`](../aegisos_agents/tools/llms/model_router.py) | `ModelRouter` | 多模型路由：gpt→OpenAI, claude→Anthropic, local/*→本地, 按 tier(device/edge/cloud) 映射 | 5 |
| [`prompts/registry.py`](../aegisos_agents/tools/prompts/registry.py) | `PromptRegistry` · `PromptRenderer` | 提示词注册与渲染（✅ P2 完成 2026-08-03） | — |
| [`runtime/supervisor.py`](../aegisos_agents/tools/runtime/supervisor.py) | `AgentLifecycle` · `RuntimeSupervisor` | Agent 生命周期管理（✅ P2 完成 2026-08-03） | — |

#### `aegisos_agents/api/` — 公共接口（✅ 5 接口定义完成）

| 接口 | 方法 |
|------|------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` |
| `ExecutionAPI` | `execute(call)` |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` |

> 另有 `ports.py`：`PersistencePort` · `SessionPort` · `TaskUpdatePort`（DI 端口）

📎 详细文档：[`aegisos_agents/AGENT.md`](../aegisos_agents/AGENT.md) 末尾「📋 模块实现详解」 · 规范：[`08_AGENT_SPEC.md`](../developer/specs/08_AGENT_SPEC.md)

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
| | `routers/agents.py` | `GET /agents` · `POST /aegisos_agents/{id}/invoke` |
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

### 已实现
- ✅ 10+ REST + SSE + WS 端点 + **攻防端点**（range/attack/defense/threat）

### 当前状态
- ✅ `Task.payload` 已贯通协议、API、ORM、转换器和运行时

📎 详细文档：[`backend/AGENT.md`](../backend/AGENT.md) 末尾「📋 模块实现详解」

---

## frontend/ — 表现层（React + Vite）

**定位**：AI Native IDE 前端，Controller-Service-Lib + Views 模式 + 5 视图。

### 已实现

| 层 | 关键文件 | 功能 |
|----|---------|------|
| **类型** | [`src/protocol/types.ts`](../frontend/src/protocol/types.ts) | 自动生成（`gen_ts_types.py`），36 个 TS 类型映射 protocol/*.py |
| | `src/protocol/frontend-types.ts` | `ViewName` · 路由类型 |
| **Store** | `lib/store/index.ts` | Zustand 全局状态：session/aegisos_agents/chatMessages/graph/isSending |
| **API Client** | `lib/api-client/client.ts` | 统一 HTTP 客户端（baseURL + X-API-Key） |
| **Services** | `services/api/agents.ts` · `sessions.ts` · `tasks.ts` · `memory.ts` · `graph.ts` | REST API 调用封装 |
| | `services/graph/index.ts` | 图数据服务 |
| | `services/realtime/sse.ts` · `ws.ts` | SSE + WebSocket 实时通信 |
| | `services/session/index.ts` | 会话管理 |
| **Controllers** | `controllers/interaction.ts` · `events.ts` · `routes.ts` | 交互/事件/路由控制 |
| **Views** | `views/chat/ChatView.tsx` | ✅ **完整实现**：Agent 选择 + 消息收发 + 任务提交 |
| | `views/canvas/` · `graph/` · `monitor/` · `replay/` | ✅ 演示版 DAG、拓扑、节点面板和事件列表 |

### ChatView 功能
- Agent 下拉选择（14 个 Agent）
- 消息发送 + 响应展示
- 任务创建 + 状态轮询
- 自动滚动

### 当前状态
- ✅ TaskMap（Graph+Canvas 合并）/ Monitor / 演练历史 基础视图；设置页支持 API/Provider、API URL、Model name
- 🔲 拖拽编辑、实时告警、后端 DAG 持久化

📎 详细文档：[`frontend/AGENT.md`](../frontend/AGENT.md) 末尾「📋 模块实现详解」

---

## infrastructure/ — 基建层

**定位**：传输 · 节点(端·云) · 交付（部署）。

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../infrastructure/api/__init__.py) | 4 个 Protocol 接口定义：`CommunicationAPI` · `NodeRegistryAPI` · `SyncAPI` · `DeploymentAPI` |

### 当前状态
- ✅ JSON Message + asyncio TCP 通信基础
- ✅ Docker Compose、internal 网络和沙箱工具 profile
- 🔲 Docker 镜像/沙箱真实启动实测
- ⏭️ 真实端边云、Kubernetes、TLS、生产 ASGI 按演示范围跳过

📎 详细文档：[`infrastructure/AGENT.md`](../infrastructure/AGENT.md) 末尾「📋 模块实现详解」

---

## observability/ — 可观测层

**定位**：inspect(监控·回放) · measure(基准·评测) · present(可视化)。

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../observability/api/__init__.py) | 6 个 Protocol 接口：`MonitorAPI` · `TraceAPI` · `ReplayAPI` · `BenchmarkAPI` · `EvaluationAPI` · `VisualizationAPI` |

**H5 可观测评测**（✅ 全部完成，41 测试）：

| 子模块 | 功能 |
|--------|------|
| `inspect/monitor/` | `MetricsCollector`：订阅 EventBus 自动采集 Agent 延迟/成功率/Token + `AlertRule` 告警 |
| `inspect/replay/` | `Timeline` 时序记录 + `ReplayPlayer` 步进/跳跃/定时回放 |
| `inspect/monitor/tracing/` | `CyberTraceProcessor` + `CyberAgentHooks`（7 个生命周期回调→EventBus） |
| `measure/benchmark/` | `BenchmarkCase`/`Suite`/`Runner` + min/avg/max/p99 统计 |
| `measure/evaluation/` | `Evaluator` 5 维度评测（accuracy/recall/latency/resource/robustness） |
| `present/visualization/` | `VisualizationService`（ECharts 兼容 + React Flow 兼容） |

### 当前状态
- ✅ 后端数据源和前端基础 Monitor/Replay 视图已接入
- 🔲 深度实时告警、交互回放和快照恢复

📎 详细文档：[`observability/AGENT.md`](../observability/AGENT.md) 末尾「📋 模块实现详解」

---

## data/ — 数据层

### 已实现
| 文件 | 内容 |
|------|------|
| [`api/__init__.py`](../data/api/__init__.py) | 4 个 Protocol 接口：`DatasetAPI` · `ModelSchemaAPI` · `GraphStoreAPI` · `VectorStoreAPI` + 工厂 `create_graph_store` / `create_vector_store` / `load_attck_dataset` |
| [`models/graph_store.py`](../data/models/graph_store.py) | ✅ H2：`InMemoryGraphStore`（默认）/ `Neo4jGraphStore`（惰性）—— 拓扑（`Asset` 节点）+ ATT&CK 图 |
| [`models/vector_store.py`](../data/models/vector_store.py) | ✅ H2：`InMemoryVectorStore`（默认）/ `QdrantVectorStore`（惰性）—— 向量检索 |
| [`datasets/attck/knowledge.py`](../data/datasets/attck/knowledge.py) | ✅ H2：ATT&CK 数据集（~36 技战术 + 关系边） |
| `aegisos.db` | SQLite 数据库文件（后端运行时生成） |

### 记忆子系统对接（H2.3/H2.4）
- `memory/vector` → `VectorMemory(backend)` 注入 `data.api.VectorStoreAPI`（Qdrant）
- `memory/semantic` → `SemanticMemory(graph_backend)` 注入 `data.api.GraphStoreAPI`（Neo4j ATT&CK）
- 默认 in_memory 零依赖，真实库按 `settings.storage`（AEGIS_STORAGE_*）启用

### 当前状态
- ✅ CVE 离线样本和资产服务匹配查询已完成
- 🔲 真实 Neo4j/Qdrant 集成测试和更大规模数据导入

📎 详细文档：[`data/AGENT.md`](../data/AGENT.md) 末尾「📋 模块实现详解」

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

📎 详细文档：[`tooling/AGENT.md`](../tooling/AGENT.md) 末尾「📋 模块实现详解」

---

## developer/ — 规范层

### 已实现
- `specs/` — 15 个规范文件（00-15），唯一真相源（SSOT）
- `roadmap/` — P0-P7 阶段计划，每个阶段独立目录
- `CHANGELOG.md` — 变更记录

📎 详细文档：[`developer/AGENT.md`](../developer/AGENT.md) 末尾「📋 模块实现详解」

---

## tests/ — 测试

### 测试分布（核心模块节选）

| 目录 | 测试文件 | 测试数 | 覆盖内容 |
|------|---------|--------|---------|
| `tests/protocol/` | `test_cyber.py` | 6 | 8 个攻防 dataclass 字段/序列化 |
| `tests/aegisos_agents/memory/` | `test_compactor.py` · `test_recaller.py` | 7 | 上下文压缩 + 记忆唤醒 |
| `tests/aegisos_agents/planning/` | `test_topology.py` · `test_router.py` · `test_election.py` · `test_scheduler.py` | 18 | 活跃子图 + Top-K 路由 + 选举 + 端边云三层调度 |
| `tests/aegisos_agents/tools/` | `test_model_router.py` | 5 | 多模型路由 |
| `tests/aegisos_agents/action/` | 12 个 `test_*.py` | 30 | 11 个攻防 Agent + 五 Agent ReAct 接入 |
| `tests/aegisos_agents/perception/` | 6 个 `test_*.py` | 73 | 上下文 + Plan/Goal/ReAct + 神经符号闭环 + 反思 |

### E2E
- ✅ `tests/e2e/` — 场景 1 红→蓝→紫完整链路 9 个测试 + AP2.7 ReAct 工具循环 1 个测试

---

## 模块依赖关系

```
developer/specs ← 定义规范（SSOT）
        ↓
protocol/ ← 唯一契约（所有域引用）
        ↓
aegisos_agents/api ← 公共接口（5 个 Protocol）
        ↓                ↑
backend/api ← 调用 aegisos_agents.api
        ↓
frontend/services ← 调用 backend REST API
```

**铁律**：跨域调用仅经 `from {domain}.api import ...`，禁止直接 import 内部子包。
