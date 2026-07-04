# 02_DIRECTORY_SPEC.md — 目录规范

> 上游：`00_PROJECT_SPEC.md`、`01_ARCHITECTURE_SPEC.md`。本文件规定每个目录的职责、输入输出、边界与可改性。
> 每个目录/子模块均有独立 `AGENT.md`（共 78 个）规定「职责/读取目录/禁止修改目录/输出/依赖/接口/测试/日志/Prompt/配置」。本文件是这些 `AGENT.md` 的总纲。

---

## 0. 全局约定

| 约定 | 规则 |
|------|------|
| `AGENT.md` 位置 | 每个域根、分类层、叶模块均须有 `AGENT.md`（记忆子模块用同结构 `README.md`） |
| `README.md` 位置 | 仓库根 `README.md`（由 `tooling/scripts/gen_readme.py` 自动生成，勿手改自动段）；记忆子模块用 `README.md` |
| `TEST` 位置 | 镜像结构放 `tests/`（`unit/`·`integration/`·`e2e/`·`fixtures/`·`benchmarks/`），与源码目录一一对应 |
| `CONFIG` 位置 | `tooling/configs/`（environments/agents/models/prompts/各模块 yaml）；密钥走环境变量 |
| 跨域调用 | 只经目标域 `api/` 子包；禁止直接导入他域内部子包 |
| 被引用资格 | 只有 `protocol/` 与各域 `api/` 可被他域引用；其余内部实现禁止被他域引用 |
| 修改资格 | 见每目录「谁可改 / 谁不可改」；修改前必读该目录 `AGENT.md` 的「禁止修改目录」 |

---

## 1. 顶层域总表

| 目录 | 角色 | 可被他域引用 | 跨域调用 | 谁可改 | 谁不可改 |
|------|------|--------------|----------|--------|----------|
| `developer/` | 规范层 | 否（运行时不依赖） | 否 | 架构师 / spec 维护者 | 业务实现者不得以代码依赖它 |
| `protocol/` | 契约层 | **是（唯一全局被依赖）** | 否（零反向依赖） | 架构师（破坏性需 major bump） | 任何域不得在 protocol/ 之外造并行结构 |
| `frontend/` | 表现层 | 纯 SPA，无 Python API | 只调 `backend.api` | 前端团队/AI | 后端/Agent 团队不得改前端内部 |
| `backend/` | 应用层 | 仅经 `backend/api/` | 调 `agents.api`/`infrastructure.api`/`observability.api`/`data.api`/`protocol` | 后端团队/AI | 前端/Agent 不得改后端内部 |
| `agents/` | 智能体域 | 仅经 `agents/api/` | 调 `protocol`/`infrastructure.api`/`data.api` | Agent 团队/AI | 前端不得直连 agents 内部 |
| `infrastructure/` | 基础设施 | 仅经 `infrastructure/api/` | 调 `protocol` | 基础设施团队/AI | 业务域不得改其内部 |
| `observability/` | 可观测 | 仅经 `observability/api/` | 调 `protocol`/订阅事件 | 可观测团队/AI | 业务域不得改其内部 |
| `data/` | 数据层 | 仅经 `data/api/` | 调 `protocol` | 数据团队/AI | 业务域不得改其内部 |
| `tooling/` | 工程支撑 | 仅经 `tooling/api/` | 调 `protocol` | 工程团队/AI | 业务域不得改其内部 |
| `docs/` | 文档资产 | 否 | 否 | 文档维护者/AI | — |
| `tests/` | 测试 | 否（不被依赖） | 可 import 任何被测域 `api/` + `protocol` | 各域对应团队/AI | — |

---

## 2. developer/（规范层）

| 项 | 值 |
|----|-----|
| 职责 | 项目大脑：规范、roadmap、指南。纵切所有层，不参与运行时 |
| 输入 | 架构决策、roadmap 进度 |
| 输出 | `*.md` 规范（含 `specs/` 编号规范、`roadmap/P0..P7`、各 GUIDE） |
| API | 无 |
| 被引用 | 否（运行时代码不得 import developer） |
| 跨域调用 | 否 |
| 谁可改 | 首席架构师 / spec 维护者 |
| 谁不可改 | 业务实现者不得以代码依赖它 |
| 子目录 | `specs/`（编号规范 SSOT）、`roadmap/`（P0..P7） |

---

## 3. protocol/（契约层）

| 项 | 值 |
|----|-----|
| 职责 | 全系统唯一数据契约（26 类型） |
| 输入 | 规范（`04_PROTOCOL_SPEC`、`06_SCHEMA_SPEC`） |
| 输出 | `message/event/scheduler/tool/memory/agent/graph/heartbeat/sync.py` + `__init__.py` |
| API | 本身即全局契约；导出 `Message,NodeRef,Header,Event,EventType,Heartbeat,Task,TaskStatus,Plan,Schedule,RetryPolicy,RollbackPlan,ToolCall,ToolResult,ToolSpec,MemoryPacket,Agent,AgentStatus,Graph,GraphNode,GraphEdge,Route,GraphDiff,NodeKind,SyncPacket,SyncStatus` |
| 被引用 | **是（唯一被全局依赖）** |
| 跨域调用 | 否（零反向依赖，仅依赖标准库） |
| 谁可改 | 架构师（破坏性需 major bump + CHANGELOG + 通知依赖方） |
| 谁不可改 | 任何域不得在 protocol/ 之外造并行结构 |
| 测试 | `tests/unit/protocol/`（往返序列化、schema 校验） |

---

## 4. frontend/（表现层）

| 项 | 值 |
|----|-----|
| 职责 | React+TS+Vite；Controller-Service-Mapper + Views；canvas/graph/monitor/replay 可视化 |
| 输入 | 用户交互、`backend.api` 实时数据（WS/SSE） |
| 输出 | UI 视图、交互事件 |
| API | 无 Python API（纯 SPA）；内部架构 Controller-Service-Mapper + Views |
| 被引用 | 前端为纯 SPA，不被他域 import；仅通过 REST/WS/SSE 调用后端 |
| 跨域调用 | **只调 `backend.api`**；禁止直连 `agents`/`infrastructure` |
| 谁可改 | 前端团队 / 前端 AI |
| 谁不可改 | 后端/Agent 团队不得改前端内部 |
| 子目录 | `src/`（含 `controllers/`(interaction·events·routes) · `services/`(api·realtime·session·graph) · `mappers/`(viewmodels·apimappers·store·utils·styles·assets) · `views/`(canvas·graph·monitor·replay)） · `public/` |

---

## 5. backend/（应用层）

| 项 | 值 |
|----|-----|
| 职责 | Router-Service-Repository-Model + Core；会话/任务/记忆/图桥接；外部请求唯一入口 |
| 输入 | 外部请求（gateway）、`agents.api`/`infrastructure.api`/`observability.api`/`data.api` |
| 输出 | REST/WS/SSE 端点、`protocol` 类型响应 |
| API | `backend/api/`：SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI |
| 被引用 | 仅 `backend/api/` |
| 跨域调用 | 调 `agents.api`/`infrastructure.api`/`observability.api`/`data.api`/`protocol` |
| 谁可改 | 后端团队 / 后端 AI |
| 谁不可改 | 前端/Agent 团队不得改后端内部 |
| 子目录 | `gateway/`(routes·auth·middleware·adapters) · `controllers/`(api·ws·sse·schemas·middleware) · `services/`(session·task·agent·memory·graph) · `mappers/`(entities·dto·repositories·converters) |

---

## 6. agents/（智能体域）

| 项 | 值 |
|----|-----|
| 职责 | 认知架构五层：感知-规划-行动-记忆-工具 |
| 输入 | Task/Plan、`protocol` 类型、`infrastructure.api`/`data.api` |
| 输出 | 执行结果、Event、MemoryPacket、GraphUpdate、Route、Schedule |
| API | `agents/api/`：AgentRegistryAPI · RuntimeAPI · MemoryAPI · ExecutionAPI · EventBusAPI（规划/感知内聚不暴露） |
| 被引用 | 仅 `agents/api/` |
| 跨域调用 | 调 `protocol`/`infrastructure.api`/`data.api` |
| 谁可改 | Agent 团队 / Agent AI |
| 谁不可改 | 前端不得直连 agents 内部 |

### 6.1 agents/perception/（感知）
| 项 | 值 |
|----|-----|
| 职责 | context（Token 预算/裁剪/会话隔离）· reasoning（CoT/ToT/ReAct）· reflection（反思评估，区别于 memory/reflection 存储） |
| 输入 | Task、上下文 |
| 输出 | 推理结果、反思评分 |
| 谁可改 | 感知模块负责人 |

### 6.2 agents/planning/（规划）
| 项 | 值 |
|----|-----|
| 职责 | planner（角色，目标分解 DAG）· orchestrator（角色，多 Agent 协作）· engine/（planner·scheduler·router·workflow·eventbus·topology） |
| 输入 | goal/Task |
| 输出 | Plan(DAG)、Route、Schedule、Graph、Event |
| 谁可改 | 规划模块负责人 |
| 关键 | `engine/router/`（低熵路由·赛事亮点）、`engine/topology/`（动态异构拓扑）、`engine/scheduler/`（调度）、`engine/eventbus/`（事件总线）、`engine/workflow/`（DAG 工作流） |

### 6.3 agents/action/（行动）
| 项 | 值 |
|----|-----|
| 职责 | 8 角色（coder·executor·tester·debugger·critic·reviewer·researcher·docwriter）+ execution/（executor 沙箱·tools 注册） |
| 输入 | Task、MemoryPacket、ToolCall |
| 输出 | ToolResult、执行结果、Event |
| 谁可改 | 各角色负责人 |
| 注意 | `action/executor/`（角色）≠ `action/execution/executor/`（沙箱执行器） |

### 6.4 agents/memory/（记忆）
| 项 | 值 |
|----|-----|
| 职责 | 12 子模块：working·episodic·semantic(知识库)·vector·archive·compression·retrieval·reflection·checkpoint·cache·snapshot·sync |
| 输入 | 写入数据、检索 query |
| 输出 | MemoryPacket、检索命中 |
| 接口 | MemoryAPI：read/write/retrieve |
| 谁可改 | 记忆模块负责人 |

### 6.5 agents/tools/（工具）
| 项 | 值 |
|----|-----|
| 职责 | llms（LLM 适配/路由/限流/回退）· prompts（模板库/版本/roles）· runtime（生命周期托管/上下文注入/心跳/挂起恢复） |
| 谁可改 | 工具模块负责人 |

---

## 7. infrastructure/（基础设施层）

| 项 | 值 |
|----|-----|
| 职责 | transport（低熵稀疏通信）· nodes(edge·cloud 端边云协同)· delivery(deployment Docker/K8s/CI) |
| API | `infrastructure/api/`：CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI |
| 跨域调用 | 调 `protocol` |
| 谁可改 | 基础设施团队 / AI |
| 谁不可改 | 业务域不得改其内部 |

---

## 8. observability/（可观测与评估层）

| 项 | 值 |
|----|-----|
| 职责 | inspect(monitor·replay 确定性回放)· measure(benchmark·evaluation 评分)· present(visualization) |
| API | `observability/api/`：MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI |
| 跨域调用 | 调 `protocol`/订阅 EventBus |
| 谁可改 | 可观测团队 / AI |

---

## 9. data/ · tooling/ · docs/ · tests/

| 目录 | 职责 | API | 跨域调用 | 谁可改 |
|------|------|-----|----------|--------|
| `data/` | datasets（加载/预处理/版本）· models（Schema 注册/迁移） | DatasetAPI · ModelSchemaAPI | 调 `protocol` | 数据团队 |
| `tooling/` | configs（environments/agents/models/prompts）· scripts（setup/build/test/deploy） | ConfigAPI · ScriptAPI | 调 `protocol` | 工程团队 |
| `docs/` | api·architecture·guides·assets·examples | 无 | 否 | 文档维护者 |
| `tests/` | unit·integration·e2e·fixtures·benchmarks | 无 | import 被测域 `api/` + `protocol` | 各域对应团队 |

---

## 10. 规范文件位置汇总

- 最高规范：`developer/specs/00..11_*.md`（本目录 SSOT）
- 阶段计划：`developer/roadmap/P*/README.md`
- 模块边界：各目录 `AGENT.md`（域根 + 分类 + 叶模块三级）
- 数据契约：`protocol/*.py`
- 配置：`tooling/configs/*.yaml`
- 测试：`tests/{unit,integration,e2e,fixtures,benchmarks}/`
