# CHANGELOG.md

> 所有变更记录于此。格式：`[阶段] 变更描述`。

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
