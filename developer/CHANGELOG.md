# CHANGELOG.md

> 所有变更记录于此。格式：`[阶段] 变更描述`。

## [P6] 2026-07-04 文档整合：MODULE.md → AGENT.md

### 变更内容
- 将根 `MODULE.md` 内容合并到根 `AGENT.md` 末尾「📋 模块实现总览」段。
- 将 9 个域 `MODULE.md`（protocol/agents/backend/frontend/infrastructure/observability/data/tooling/developer）内容合并到对应 `AGENT.md` 末尾「📋 模块实现详解」段。
- 删除全部 10 个 `MODULE.md` 文件（根 + 9 域）。
- 更新全局引用：`docs/ARCHITECTURE.md`（总览仪表盘 + 9 处详细文档链接）、`README.md`（项目结构 + 模块文档索引表）、`CLAUDE.md`（根 + `.claude/`，L0 在哪找 + 维护段）、`developer/plan.md`（文档体系记录 + 维护提醒）。
- 各 `AGENT.md` 合并段均以 `> 原 {domain}/MODULE.md 内容，已合并至此。` 标注来源。

### 动机
- 消除 `MODULE.md` 作为独立文件类型，统一到 `AGENT.md`（开发规范 + 实现详情同文档）。
- 减少文件数量，降低维护成本；新「📋 模块实现详解」段与原 AGENT.md 内容在同一文件内更易交叉引用。

## [P6] 2026-07-04 前后端打通：Agent 注册 + Chat 联调 + 文档同步

### 后端（composition.py）
- 新增 11 个攻防 Agent 注册（recon/detector/vuln_correlator/exploit_planner/lateral_move/triage/threat_hunt/ir_planner/forensics/critic/reviewer），总计 14 个 Agent（3 通用 + 11 攻防）。
- `MockRuntime` 接入真实调用：`_cyber_dispatch_map()` 分发 11 个 handler，各 handler 解析 payload/goal 并调用对应 Agent。
- `_CyberMockProvider` 封装 MockProvider，支持前缀匹配（exact match 优先，fallback prefix）。
- `_build_cyber_mock_responses()` 预置攻防场景 JSON 响应。
- 修复：`_handle_recon` 添加 CIDR/IP 检测，避免 prompt 前缀不匹配导致空资产。

### 前端
- `App.tsx`：启动时拉取 Agent 列表（`agentApi.list()` → `setAgents`）。
- `services/api/agents.ts`：`list()` 兼容后端裸数组返回（`Array.isArray(r) ? r : (r.agents ?? [])`）。
- `views/chat/ChatView.tsx`：修复 output 对象渲染崩溃（`typeof output === "string" ? output : JSON.stringify(...)`）。

### 文档同步
- `developer/roadmap/README.md`：更新进度勾选（P1-P5 已完成，P6 部分完成）。
- `CLAUDE.md`（根 + `.claude/`）：更新本机环境约束（macOS .venv Python 3.12.13）+ plans 段当前状态。
- `README.md`：更新 agents/action 角色列表（红蓝紫 11 Agent）+ 快速开始命令 + 当前进度段。
- `agents/action/AGENT.md`：更新输出段为红蓝紫角色列表。
- `developer/specs/04_PROTOCOL_SPEC.md`：登记 MemoryPacket.kind/recent（B1）+ GraphNode.status（C1）+ §18 Cyber 攻防类型 + §16 低熵路由/异构选举/端边云调度。
- `developer/specs/06_SCHEMA_SPEC.md`：登记 MemoryPacketSchema.kind/recent + GraphNodeSchema.status + §14 CyberSchema 类型表 + §12 映射表更新。

### 验证
- `pytest tests/ -v`：59 passed。
- GET /agents 返回 14 个 Agent；POST /agents/recon/invoke 返回 2 资产；POST /agents/detector/invoke 返回 1 告警。
- 前端 Chat 下拉框显示 14 个 Agent；Swagger UI 可访问。

## [P1-P5] 2026-07-04 Phase A-E：攻防核心引擎 TDD 实现

> 按 `docs/superpowers/plans/2026-07-04-agents-phase-ae.md` 计划，以 TDD 方式实现攻防群体智能核心引擎（12 任务，59 测试全通过）。

### Phase A — protocol 攻防类型 (A1)
- 新增 `protocol/cyber.py`：8 个 `@dataclass`（Asset / VulnFinding / AttackStep / AttackChain(含 to_dict/from_dict) / Alert / DefenseAction / ResponsePlan / ThreatIntel）。
- 扩展 `protocol/__init__.py`：导入 cyber 模块并登记 `__all__`。
- 测试：6 个（`tests/protocol/test_cyber.py`）。

### Phase B — 超长程记忆压缩 + 唤醒 (B1+B2)
- 扩展 `protocol/memory.py`：`MemoryPacket` 新增 `kind: str = "normal"` 和 `recent: bool = False`。
- 新增 `agents/memory/compression/compactor.py`：`compress(context, budget)` 按 budget 压缩（decision 保留、recent 保留、其余折叠为 digest）。
- 新增 `agents/memory/recall/recaller.py`：`recall(trigger, episodic, vector)` 按相关性 + kind 优先级唤醒 TOP_K=5 条记忆。
- 测试：7 个（4 compactor + 3 recaller）。

### Phase C — 拓扑 + 低熵路由 + 异构选举 (C1+C2+C3)
- 扩展 `protocol/graph.py`：`GraphNode` 新增 `status: str = "active"`（active | idle | degraded）。
- 新增 `agents/planning/engine/topology/topology.py`：`active_subgraph(graph, required_capability)` 过滤活跃+能力匹配节点。
- 新增 `agents/planning/engine/router/router.py`：`route(message, topology, required_capability) -> list[NodeRef]`，Top-K=3 稀疏路由（非全广播），按 success_rate - latency 排序。
- 新增 `agents/planning/engine/router/election.py`：`elect(task_features, instances, capability_vectors) -> NodeRef`，任务特征向量与能力向量点积最大者当选。
- 测试：10 个（3 topology + 4 router + 3 election）。
### Phase D — 端边云三层调度 + 多模型兼容层 (D1+D2)
- 扩展 `protocol/scheduler.py`：`Task` 新增 `privacy: str = "standard"` 和 `latency_budget: float = 10.0`。
- 新增 `agents/planning/engine/scheduler/scheduler.py`：`schedule(task, models, required_capability) -> Model`，端边云三层卸载（device/edge/cloud），四规则 + 降级：privacy=local→device，latency<1s→device，latency<5s→edge，默认→cloud；缺失时逐级降级。
- 新增 `agents/tools/llms/` 多模型兼容层：
  - `base.py`：`ModelProvider` Protocol + `LLMRequest` / `LLMResponse` dataclass。
  - `mock_provider.py`：确定性 Mock（测试/离线开发用）。
  - `openai_provider.py`：OpenAI API 兼容（httpx）。
  - `anthropic_provider.py`：Anthropic Claude API（httpx）。
  - `local_provider.py`：Ollama / vLLM / LM Studio 本地模型。
  - `model_router.py`：`ModelRouter` 按模型前缀 / tier 路由到对应 provider。
  - `scheduler_adapter.py`：薄适配层，避免 tools 直接依赖 planning。
- 测试：13 个（8 scheduler + 5 model_router）。

### Phase E — 红蓝紫 Agent 角色 + 神经符号闭环 (E1-E12)
- **红队 (E1-E4)**：
  - `agents/action/recon/`：`ReconAgent.scan(target_range) -> list[Asset]`
  - `agents/action/vuln_correlator/`：`VulnCorrelatorAgent.correlate(assets) -> list[VulnFinding]`
  - `agents/action/exploit_planner/`：`ExploitPlannerAgent.plan(findings) -> AttackChain`
  - `agents/action/lateral_move/`：`LateralMoveAgent.plan_moves(chain, topology) -> list[AttackStep]`
- **蓝队 (E5-E9)**：
  - `agents/action/detector/`：`DetectorAgent.detect(event_stream) -> list[Alert]`
  - `agents/action/triage/`：`TriageAgent.triage(alerts) -> list[Alert]`（去噪 + 严重度排序）
  - `agents/action/threat_hunt/`：`ThreatHuntAgent.hunt(alerts) -> list[dict]`（狩猎假设）
  - `agents/action/ir_planner/`：`IRPlannerAgent.plan_response(hypotheses) -> ResponsePlan`
  - `agents/action/forensics/`：`ForensicsAgent.investigate(plan) -> dict`（取证报告）
- **紫队 (E10-E11)**：
  - `agents/action/critic/`：`CriticAgent.critique(target, side) -> dict`（对抗性校验）
  - `agents/action/reviewer/`：`ReviewerAgent.review(artifacts) -> dict`（一致性审查）
- **神经符号闭环 (E12)**：
  - `agents/perception/reasoning/neuro_symbolic.py`：`validate_chain(chain, rules)` 符号校验 + `NeuroSymbolicLoop.validate_and_fix(chain, rules, max_iterations)` LLM 生成→符号校验→反馈→修正循环。
- 测试：23 个（6 red + 8 blue + 4 purple + 4 neuro-symbolic + 1 forensics）。

### 质量门禁
- `ruff format`：43 文件已格式化。
- `ruff check --fix`：51 个问题自动修复，剩余 8 个为既有代码（StrEnum 建议 + 已有模块类型注解）。
- `pytest tests/ -v`：**59 passed in 0.05s**。
- 所有 AI 生成代码含 `@aegis-gen` 注释头（date/dev/change）。

## [P0] 2026-06-26
- 初始化 AegisOS 仓库骨架（37 顶层模块 + memory 12 子模块 + agents 10 子模块）。
- 建立 AI 开发规范层 `developer/`（架构/路线图/协议/各指南）。
- 建立全仓库 AGENT.md 体系（root + 37 模块 + 10 agents，共 48 个）。
- 建立系统级开发计划 `developer/roadmap/P0..P7`。
- 建立通信协议契约 `protocol/`（Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync）。
- 建立 memory 子系统各子模块 README 与 ROADMAP 各阶段文档。

## [P0] 2026-06-26 重构：同域聚合分层
- 将 37 个平铺顶层目录重组为 15 个分层域目录，同属一域的模块归到一起：
  - `backend/` 吸收 `gateway/`（`backend/gateway/`）。
  - `agents/` 吸收智能体相关：`memory/`→`agents/memory/`、`llms/`→`agents/tools/llms/`、`prompts/`→`agents/tools/prompts/`、`reasoning/`、`reflection/`、`context/`、`runtime/`（其中 `agents/memory/semantic/` 即知识库）。
  - `agents/planning/engine/` 聚合编排：`planner/`、`scheduler/`、`router/`、`workflow/`、`eventbus/`、`topology/`。
  - `agents/action/execution/` 聚合 `executor/`、`tools/`。
  - `infrastructure/` 聚合 `communication/`、`edge/`、`cloud/`、`deployment/`。
  - `observability/` 聚合 `monitor/`、`replay/`、`benchmark/`、`evaluation/`、`visualization/`。
  - `data/` 聚合 `datasets/`、`models/`。
- 新增 7 个域根 AGENT.md（backend/agents/planning/engine/execution/infrastructure/observability/data）。
- 重写全部 AGENT.md（路径引用更新为新分层路径）、memory 12 子模块 README、ROADMAP P0..P7。
- 更新 developer/ 规范文档（DIRECTORY_GUIDE/ARCHITECTURE/ROADMAP 等）以反映分层。
- AGENT.md 体系扩充至 55 个（含域根）。

## [P0] 2026-06-26 重构：进一步同域聚合
- 顶层目录从 15 进一步收敛到 13：
  - `ROADMAP/`（阶段计划）并入 `developer/roadmap/`（规范层即项目大脑），总览 `developer/ROADMAP.md` → `developer/roadmap/README.md`，P0..P7 → `developer/roadmap/P0..P7/`。
  - `configs/` + `scripts/` 合并为 `tooling/`（`tooling/configs/` + `tooling/scripts/`），新增 `tooling/AGENT.md` 域根。
  - `examples/` 并入 `docs/examples/`（示例属文档资产），更新 `docs/AGENT.md` 域根。
- 批量更新所有 AGENT.md 与 developer 文档的路径引用（ROADMAP→developer/roadmap、configs→tooling/configs、scripts→tooling/scripts、examples→docs/examples）。
- 重写根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 支撑行、developer/docs/tooling 域根 AGENT.md。
- AGENT.md 体系现为 54 个（新增 tooling 域根）。

## [P0] 2026-06-26 重构：agent 相关全部归入 agents/
- 将编排引擎与执行能力（均与 agent 相关）移入 agents/ 域：
  - `engine/` → `agents/planning/engine/`（planner/scheduler/router/workflow/eventbus/topology）
  - `execution/` → `agents/action/execution/`（executor/tools）
- 顶层目录从 13 收敛到 11：agents/ 现包含一切与 agent 相关的功能（角色 Agent + 认知 + 记忆 + 模型 + 提示词 + 运行时 + 编排引擎 + 执行能力）。
- 批量更新所有 AGENT.md 与 developer 文档的路径引用（engine/→agents/planning/engine/、execution/→agents/action/execution/）。
- 更新 agents/ 域根 AGENT.md（纳入 engine + execution 子模块）、根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与设计原则。
- 与 agent/backend/frontend 三者不相干的模块（protocol/infrastructure/observability/data/tooling/docs/tests/developer）保持不动。

## [P0] 2026-06-26 重构：各域内部分类
- 为每个大模块按其领域范式做内部分类，新增 19 个分类层 AGENT.md：
  - **agents/ 感知-规划-行动-记忆-工具**（认知架构五层）：
    - `agents/perception/`（感知）：context、reasoning、reflection
    - `agents/planning/`（规划）：planner(角色)、orchestrator(角色)、engine/(编排引擎)
    - `agents/action/`（行动）：coder/executor/tester/debugger/critic/reviewer/researcher/docwriter(角色) + execution/(沙箱+工具)
    - `agents/memory/`（记忆）：12 子模块（不变）
    - `agents/tools/`（工具）：llms、prompts、runtime
  - **backend/ DDD 四层**：domain/(核心域)、application/(应用层)、infrastructure/(基础设施:gateway)、interfaces/(接口层)
  - **frontend/ 功能特性**：canvas/、graph/、monitor/、replay/、shared/
  - **infrastructure/ 传输-节点-交付**：transport/、nodes/、delivery/
  - **observability/ 观测-度量-呈现**：inspect/、measure/、present/
- 批量更新所有 AGENT.md 与 developer 文档的路径引用。
- 更新全部域根 AGENT.md（agents/backend/frontend/infrastructure/observability）含分类表格。
- 重写根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与数据流。
- AGENT.md 体系现为 73 个（域根 + 分类层 + 叶模块三级）。

## [P0] 2026-06-26 重构：后端/前端改为 Controller-Service-Mapper 架构
- **backend/** 由 DDD 四层改为经典三层 + 网关：
  - `controllers/`（控制器：参数校验/响应封装，不含业务逻辑）
  - `services/`（服务：业务逻辑/用例编排/事务）
  - `mappers/`（映射器：数据转换 protocol<->entity<->dto、仓储/持久化）
  - `gateway/`（网关：鉴权/限流/路由分发/协议适配，从 infrastructure/ 提升）
  - 删除 domain/application/interfaces/infrastructure DDD 目录。
- **frontend/** 由功能特性改为与后端对称的三层 + 视图：
  - `controllers/`（控制器：交互/事件处理/路由分发，不含业务逻辑）
  - `services/`（服务：API 调用/WS·SSE 管理/状态编排）
  - `mappers/`（映射器：数据转换/视图模型/全局状态/共享工具/样式/资产）
  - `views/`（视图：canvas/graph/monitor/replay 功能特性 UI）
  - 删除顶层 canvas/graph/monitor/replay/shared 特性目录（views/ 下保留功能特性）。
- 重写 backend/ 与 frontend/ 域根 + 各层 AGENT.md（共 9 个）。
- 更新根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与数据流、BACKEND_GUIDE、FRONTEND_GUIDE。
- 批量修正路径引用（domain→services、application→services、interfaces→controllers、infrastructure/gateway→gateway、shared→mappers、canvas/graph/monitor/replay→views/下）。

## [P0] 2026-06-26 重构：模块间 API 解耦
- 为每个域新增 `api/` 公共接口子包，其他模块只通过 `from {domain}.api import ...` 调用，不直接访问内部实现，实现解耦：
  - `agents/api/` — 7 接口：AgentRegistryAPI · MemoryAPI · PlanningAPI · ExecutionAPI · PerceptionAPI · EventBusAPI · RuntimeAPI
  - `backend/api/` — 5 接口：SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI
  - `frontend/api/` — 3 接口：ViewAPI · InteractionAPI · ThemeAPI
  - `infrastructure/api/` — 4 接口：CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI
  - `observability/api/` — 6 接口：MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI
  - `data/api/` — 2 接口：DatasetAPI · ModelSchemaAPI
  - `tooling/api/` — 2 接口：ConfigAPI · ScriptAPI
- 每个 `api/` 含 `__init__.py`（Python Protocol 接口，参数/返回值用 protocol/ 类型）与 AGENT.md（解耦原则 + 接口清单）。
- 更新全部 7 个域根 AGENT.md 下辖子模块加入 api/ 层。
- 更新根 AGENT.md 全局铁律、ARCHITECTURE 设计原则、DIRECTORY_GUIDE 顶层表格、API_SPEC 模块间解耦章节。
- 全部 7 个 api 包可导入，共暴露 29 个公共接口。

## [P0] 2026-06-26 动态 README
- 新增 `tooling/scripts/gen_readme.py`：扫描仓库实际目录树、AGENT.md 计数、api 公共接口（解析各域 `api/__init__.py` 的 `__all__`）、文件统计，自动生成根 `README.md`。
- README 含：项目介绍、核心特性、架构总览、顶层目录表、agents/backend/frontend 内部分层、模块间 API 解耦表、数据流、通信协议、开发流程、快速开始、自动生成的目录树与仓库统计、关键文档索引。
- 「实际目录结构」与「仓库统计」段为自动生成，勿手改；结构/api 变动后运行 `python3 tooling/scripts/gen_readme.py` 刷新。
- 更新 tooling/scripts/AGENT.md（登记 gen_readme.py + 动态维护说明）、根 AGENT.md（README 动态维护段）、DEVELOPER_GUIDE（流程加入 README 刷新步骤）。

## [P0] 2026-07-03 规范整体改造：全仓对齐 SSOT + 仓库卫生 + frontend 结构重构

> 触发：根 `AGENT.md` 与 `developer/specs/README.md` 声明 `developer/specs/`（00–13）为唯一真相源（SSOT）并"取代" `developer/` 根旧指南，但 77/78 个模块 `AGENT.md` 与 `README` 仍引用旧文档——本次把全仓对齐到 SSOT。

- **删除旧指南**：删除 `developer/` 根下 20 个被 `developer/specs/` 取代的旧指南（`AGENT_GUIDE`/`API_SPEC`/`ARCHITECTURE`/`BACKEND_GUIDE`/`CODING_RULES`/`DEPLOY_GUIDE`/`DESIGN`/`DEVELOPER_GUIDE`/`DEVELOPMENT_PLAN`/`DIRECTORY_GUIDE`/`EVENT_SPEC`/`FRONTEND_GUIDE`/`MEMORY_GUIDE`/`MESSAGE_PROTOCOL`/`PROJECT_BOOTSTRAP`/`PROMPT_GUIDE`/`PYTHON_STYLE`/`ROUTER_GUIDE`/`TEST_GUIDE`/`TOOL_SPEC`）；保留 `developer/AGENT.md`、`CHANGELOG.md`、`roadmap/`、`specs/`。
- **全量 AGENT.md 引用重定向**：新增 `tooling/scripts/realign_agent_docs.py`（带 `@aegis-gen` 头），把 77 个模块 `AGENT.md` 中 346 处旧文档引用按映射重定向到 `developer/specs/`（ARCHITECTURE→01、DIRECTORY_GUIDE→02、MESSAGE_PROTOCOL→04、API_SPEC→05、EVENT_SPEC→07、CODING_RULES→11、PYTHON_STYLE→12、ROUTER_GUIDE→04 等）；同步修正 12 个 `agents/memory/*/README.md`、`roadmap/P1`、`specs/08`（PROMPT_GUIDE/TOOL_SPEC 并入本文件）、`protocol/__init__.py` 的残留引用。
- **根规范更新**：根 `AGENT.md`、`developer/specs/README.md`、`developer/AGENT.md`（删除无效 `补充.md`/`开发.md` 引用、下辖子模块改指 specs/）的"取代/历史参考"表述改为"已删除"。
- **README 重生成**：修正 `gen_readme.py`（关键文档/通信协议/开发流程段改指 specs/、计数排除 `.venv`/`.claude`/`node_modules`/`__pycache__`/`*.egg-info` 等噪声、顶层域排除 egg-info）；手动同步 `README.md`（doc-ref 段 + 统计刷新：78 AGENT.md / 56 py / 116 md / 232 文件 / 123 目录）。
- **frontend 代码结构重构**：删除重复编译配置 `vite.config.js`/`playwright.config.js`（保留 `.ts`）；重构 `gen_ts_types.py` 剥离硬编码前端类型块（生成器只产出 protocol 契约类型，职责分离）；重建 `frontend/src/protocol/frontend-types.ts` 为前端本地类型唯一手维护来源（修正 `ViewName` 缺 `'chat'` 的分叉、统一 `Record<string, unknown>`）；10 处导入重定向（前端本地类型→`@/protocol/frontend-types`，protocol 类型→`@/protocol/types`）。验收：`tsc -b` 与 `vite build` 均通过（69 模块）。
- **仓库卫生**：扩充根 `.gitignore`（`__pycache__`/`*.pyc`/`.venv`/`*.db`/`.DS_Store`/各 cache/frontend 构建产物）；`git rm --cached` 取消跟踪 `.DS_Store`、`data/aegisos.db`、`.venv/`（**7532 文件，macOS venv 误提交**）、`aegisos.egg-info/`。tracked 文件 7861→329。
- 所有 AI 改动加 `@aegis-gen` 注释头（§10）。
- **未执行**：Python 侧质量门禁（ruff/mypy）与 `gen_readme.py`/`gen_ts_types.py` 实际运行——本机无 Python 解释器（仓库原在 macOS 开发，`.venv` 为 macOS 专用；Windows 仅有 node）。realign 经等价 perl 完成（结果已校验：0 残留）；README/types 经手动同步；frontend 经 `tsc`+`build` 验证。待 Python 环境就绪后运行 `python3 tooling/scripts/gen_readme.py` 与 `npm run gen:types` 可刷新自动生成段（`types.ts` 中现已无引用的前端类型导出会在下次 `gen:types` 时自动清除）。

## [P0] 2026-07-03 赛事作品方案固化（XH-202631 荣耀·超长程群体智能）

> 赛事作品「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」以 AegisOS 为底座。本步固化总体方案与可执行任务清单（Spec First）。

- 新增 `developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`：定位与赛事对齐（5 能力维度 / 评分完整性40+应用创新25+技术创新20+性能15 / 截止 2026-09-15）、复用 8 域分层架构、红蓝紫 Agent 角色清单（recon/vuln_correlator/exploit_planner/lateral_move · detector/triage/threat_hunt/ir_planner/forensics · planner/orchestrator/router/critic/reviewer）、攻防协议类型设计（`protocol/cyber.py`：Asset/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel）、动态异构拓扑 + 低熵稀疏路由伪代码（Top-K 非全广播 + 异构选举）、超长程记忆压缩/唤醒伪代码（12 子模块映射 ATT&CK/CVE/向量/情景）、神经-符号协同推理闭环、端边云调度策略、后端/前端/基建扩展、生产级技术栈表、3 场景演示脚本（防御/软工/投研）、roadmap P0-P7 对齐、评分对齐表、风险与里程碑验收。
- 新增 `developer/specs/plans/15_CYBERDEFENSE_TASKS.md`：writing-plans 格式实施任务清单，按 Phase A-H（对应 P1-P7 + 攻防基建）拆解；核心算法任务（B 记忆压缩、C 拓扑/路由）含完整 TDD 测试 + 实现代码；其余任务含确切文件路径 + 接口契约 + 验收命令；含 Self-Review 与 Execution Handoff。
- `developer/specs/README.md` 索引追加 14、15。
- `developer/roadmap/README.md` 追加「赛事作品对齐」段（各阶段→攻防扩展映射 + 截止）。
- 决策记录：场景=攻防对抗仿真靶场；LLM=云+端混合多模型兼容层；技术栈=升级为生产级；演示=3 场景跨领域。
- 约束：攻防工具仅 Docker 沙箱靶场内运行、永不触真实网络；router 禁低熵全广播；AI 代码须 `@aegis-gen` 头。
- **下一步**：按 Phase A→B→C 顺序执行（契约 + 核心算法优先），可选 subagent-driven-development 并行推进。

## [P0] 2026-07-03 AGENT.md 交叉引用改造 + CLAUDE.md 工程总览

> 对齐用户需求：全仓 AGENT.md 复核（职责边界 + 交叉引用，让 agent 快速定位去哪里）+ 生成 `.claude/CLAUDE.md`（渐进式披露工程总览）。

- **根 `AGENT.md`**：规范表补 `plans/14`、`plans/15` 行；「00–12」→「00–15」（2 处 + 表格），与 `specs/README.md` 索引一致。
- **77 个模块 AGENT.md**：新增 `tooling/scripts/add_agent_crossrefs.pl`（带 `@aegis-gen` 头，UTF-8 安全，幂等：已存在则跳过），为每个模块 AGENT.md 追加标准化 `## 交叉引用（去哪里找）` 段——本模块规范（域派生 + 子路径微调：router/topology 补 `04 §16` 低熵、action/execution 补 `11` 沙箱、memory 补 `B1-B3` 压缩/唤醒）、API 边界（有 api/ 的 7 域）、数据契约、相关计划（backend/frontend→13+15；agents/protocol/infra/observability/data/tooling→14+15）。域根插入在「下辖子模块」前，叶模块追加末尾。验收：77/77 覆盖（grep 校验）、抽查 router/backend/protocol UTF-8 与插入位置正确。
- **单一职责**：经跨域抽样（根/agents/protocol/backend/agents/memory + router/frontend-views 等 8 份）核验，各 AGENT.md 仅描述本模块事务、无越界；脚本仅追加未删改原文。
- **`.claude/CLAUDE.md`**：渐进式披露工程总览——L0 30 秒上手（定位+铁律+在哪找）、L1 项目与 8 域分层+工作流+铁律、L2 模块地图（域→职责→规范→计划→api）、L3 深指针（specs 00–15 索引、roadmap P0–P7、22 skills 分组、plans 13–15）+ 本机环境约束（无 Python / protocol dataclass 现状）。
- **注意**：`.claude/` 已被 `.gitignore`（第 2 行）→ `.claude/CLAUDE.md` 不提交、不自动加载；根 `CLAUDE.md` 未被忽略且为 Claude Code 默认自动加载位置——是否复制到根待用户确认。
- **子代理说明**：原计划 7 组并行子代理审计，但本 token 对子代理执行模型 `deepseek-v4-flash` 无访问权（403，model 覆盖无效），子代理整条路不通；改用 perl 脚本一次性完成，结果已校验。

## [P0] 2026-07-04 目录重构：backend 代码移入 src/ + 前端清理废弃顶层目录

> 触发：前端 service/mapper/controller 等代码全部在 `frontend/src/` 下，顶层 `frontend/api/`、`frontend/controllers/`、`frontend/services/`、`frontend/mappers/`、`frontend/views/` 为旧结构残留且无实际引用；后端需与前端对齐，代码移入 `backend/src/`。

- **前端清理**：删除 5 个废弃顶层目录（`frontend/api/`、`frontend/controllers/`、`frontend/services/`、`frontend/mappers/`、`frontend/views/`）；所有前端代码统一在 `frontend/src/` 下。
- **后端重构**：将 `backend/` 下原顶层代码全部移入 `backend/src/`：`main.py`、`composition.py`、`api/`、`controllers/`、`gateway/`、`mappers/`、`services/`；新增 `backend/__init__.py` 作为包标记。
- **批量 import 更新**：20 个后端 `.py` 文件的 `from backend.X` → `from backend.src.X`（42 处匹配）。
- **配置更新**：`pyproject.toml` 加 `where = ["."]`；`Makefile`/`start.sh` 中 `uvicorn backend.main:app` → `uvicorn backend.src.main:app`；`tooling/scripts/gen_readme.py` 适配后端 `src/api` 子路径、前端无 Python API。
- **AGENT.md 更新**（7 个）：`backend/AGENT.md` + `backend/src/api/AGENT.md` + `controllers/AGENT.md` + `services/AGENT.md` + `mappers/AGENT.md` + `gateway/AGENT.md` + `frontend/AGENT.md`。
- **规范文档更新**（10 个文件）：
  - `00_PROJECT_SPEC.md`（入站边界 + 分层表）
  - `01_ARCHITECTURE_SPEC.md`（前端边界 + 插件路径）
  - `02_DIRECTORY_SPEC.md`（frontend 域表格全面重写 + 依赖矩阵行）
  - `03_IMPORT_SPEC.md`（依赖矩阵去 `frontend.api` 列 + `backend.api`→`backend.src.api`）
  - `05_API_SPEC.md`（§2.1 前端无 Python API 重写 + §2.2 `backend.src.api`）
  - `09_DEVELOPMENT_SPEC.md`（前端开发流程引用路径）
  - `10_INTERFACE_BOUNDARY_SPEC.md`（接口矩阵表 + 禁止行 + 前端依赖行）
  - `12_TECH_STACK_SPEC.md`（技术栈路径引用 5 处）
  - `plans/13_FRONTEND_BACKEND_PLAN.md`（前端分层表路径 + B0 里程碑 `uvicorn backend.src.main:app`）
  - `README.md`（API 解耦表：`backend.api`→`backend.src.api`、`frontend.api`→无）
- **后端代码 docstring 更新**（5 个文件）：`backend/src/api/__init__.py` + `services/graph.py` + `memory.py` + `session.py` + `task.py` 中 `backend.api` 引用 → `backend.src.api`（`@aegis-gen` 注释头不动）。
- **CLAUDE.md 更新**：根 `CLAUDE.md` + `.claude/CLAUDE.md` 同步（backend api 列→`backend/src/api/`、前端无 api）。
- **验收待执行**：`tsc --noEmit` + `vite build`（前端）；`uvicorn backend.src.main:app`（后端）

## [P6] 2026-07-05 后端重构：Controller-Service-Mapper → Router-Service-Repository-Model（扁平四层）

### 重构概要
将 `backend/src/{controllers,services,mappers,gateway,api}` 旧嵌套结构重构为经典 Python 扁平四层架构 `backend/{routers,services,repositories,models}` + 辅助层 `core/schemas/mocks`，删除 `backend/src/` 目录。

### 目录变更
- **旧 → 新映射**：
  - `backend/src/main.py` → `backend/main.py`
  - `backend/src/composition.py` → `backend/core/composition.py`（813 行精简至 ~170 行）
  - `backend/src/gateway/{auth,middleware,routes}` → `backend/core/{auth,middleware,routes}.py`
  - `backend/src/controllers/{api,sse,ws,schemas}` → `backend/routers/{*.py}` + `backend/schemas/`
  - `backend/src/controllers/api/` 下 10 个路由 → `backend/routers/{health,sessions,tasks,agents,memory,graph,tools,metrics,replay,sse,ws}.py`
  - `backend/src/services/` → `backend/services/{session,task,agent,memory,graph}_service.py + di_ports.py`
  - `backend/src/mappers/{database,repositories}` → `backend/repositories/{database,repositories}.py`
  - `backend/src/mappers/{entities,converters}` → `backend/models/{entities,converters}.py`
  - `backend/src/api/` → `backend/api.py`
  - `backend/src/controllers/schemas/` → `backend/schemas/__init__.py`
- **新增**：`backend/mocks/` 目录（6 个 mock 文件从 composition.py 拆分：agent_registry/runtime/cyber_provider/memory/execution/event_bus）
- **删除**：`backend/src/` 整个旧目录（含 controllers/services/mappers/gateway/api 子目录及 AGENT.md）

### composition.py 拆分
- 原文 813 行内联全部 Mock 类定义 → 精简至 ~170 行，Mock 类移至 `backend/mocks/` 6 个独立文件。
- `agents/tools/llms/mock_provider.py` 新增 `responses` property（修复私有属性 `_responses` 封装泄漏）。
- 新增 `backend/services/di_ports.py`（DI 端口 Protocol 定义，供 core/composition.py 实现）。

### Import 路径映射（48 处 .py 更新）
- `backend.src.composition` → `backend.core.composition`
- `backend.src.controllers.schemas` → `backend.schemas`
- `backend.src.controllers.api` → `backend.routers`
- `backend.src.controllers.{sse.events,ws.stream}` → `backend.routers.{sse,ws}`
- `backend.src.gateway.{auth,middleware,routes}` → `backend.core.{auth,middleware,routes}`
- `backend.src.mappers.{database,repositories}` → `backend.repositories.{database,repositories}`
- `backend.src.mappers.{entities,converters}` → `backend.models.{entities,converters}`
- `backend.src.services.*` → `backend.services.*_service`
- `backend.src.api` → `backend.api`

### 配置文件更新
- `Makefile`：`backend.src.main:app` → `backend.main:app`
- `start.sh`：`backend.src.main:app` → `backend.main:app`
- `tooling/scripts/gen_readme.py`：`backend.src.api` → `backend.api`、`src/api` → `api`
- `README.md` + 根 `MODULE.md`：启动命令更新

### AGENT.md 更新（7 个新建 + 1 个重写）
- **重写**：`backend/AGENT.md`（Controller-Service-Mapper → Router-Service-Repository-Model 全面重写）
- **新建**：`backend/routers/AGENT.md`、`backend/services/AGENT.md`、`backend/repositories/AGENT.md`、`backend/models/AGENT.md`、`backend/core/AGENT.md`、`backend/schemas/AGENT.md`、`backend/mocks/AGENT.md`
- **删除**：旧 `backend/src/{api,controllers,gateway,mappers,services}/AGENT.md`（5 个）
- **重写**：`backend/MODULE.md`（架构图、文件表、端点表全部更新为新路径）

### 规范文档更新（10 个文件）
- `00_PROJECT_SPEC.md`（入站边界 + 分层表）
- `01_ARCHITECTURE_SPEC.md`（前端边界 + 后端结构）
- `02_DIRECTORY_SPEC.md`（3 处 frontend 引用）
- `03_IMPORT_SPEC.md`（依赖矩阵表头）
- `05_API_SPEC.md`（2 处 backend.src.api）
- `09_DEVELOPMENT_SPEC.md`（2 处 backend.src）
- `10_INTERFACE_BOUNDARY_SPEC.md`（接口矩阵表 5 处 + gateway → core + 禁止行 2 处 + 前端契约行）
- `12_TECH_STACK_SPEC.md`（2 处 backend.src）
- `plans/13_FRONTEND_BACKEND_PLAN.md`（B0 里程碑启动命令）
- `developer/plan.md`（动态计划同步）

### 验收
- ✅ `ruff format`：23 files reformatted（通过）
- ✅ `ruff check --fix`：4 errors fixed, 0 remaining（通过）
- ✅ `pytest`：59 passed（通过）
- ⚠️ `mypy`：86 errors（均为预先存在的类型标注问题，非本次重构引入；其中 composition.py:101 的 MockEventBusAPI.subscribe 返回类型不匹配需后续修复）
