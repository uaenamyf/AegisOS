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
  -> 生成/更新 Doc + CHANGELOG + plan.md（勾选完成任务）
  -> Commit
```
Agent 永不扫描整个项目；按模块边界精准读写，效率高且不会越界破坏其他子系统。
**铁律**：P0 规范（`developer/specs/`）未完成前，任何人/AI 不得编写业务代码。开发遵循 `Specification → Contract → API → Implementation → Test → Document`。

## 仓库分层（同域聚合 + 域内分类，目录导航详见 developer/specs/02_DIRECTORY_SPEC.md）
1. **developer/** — 规范层（项目大脑）。含 `developer/specs/`（编号规范 SSOT，`00`–`15`）+ `developer/roadmap/`（P0..P7）。
2. **protocol/** — 契约层，唯一数据契约。
3. **frontend/** — 表现层。Controller-Service-Mapper + Views：`controllers/`(交互/事件) · `services/`(API/实时/状态) · `mappers/`(数据转换/全局状态/共享) · `views/`(canvas·graph·monitor·replay)。
4. **backend/** — 应用层。Router-Service-Repository-Model + Core：`core/`(组合根DI/鉴权/中间件/路由聚合) · `routers/`(路由层) · `services/`(业务逻辑) · `repositories/`(数据访问) · `models/`(ORM实体) · `schemas/`(契约) · `mocks/`(端口mock)。
5. **agents/** — 智能体域。认知架构五层：
   - `agents/perception/` 感知：context · reasoning · reflection
   - `agents/planning/` 规划：planner · orchestrator · engine/(planner·scheduler·router·workflow·eventbus·topology)
   - `agents/action/` 行动：coder·executor·tester·debugger·critic·reviewer·researcher·docwriter + execution/(executor·tools)
   - `agents/memory/` 记忆：12 子模块（含 semantic 知识库）
   - `agents/tools/` 工具：llms · prompts · runtime
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
11. 目标域 `MODULE.md`（模块实现详解）+ 根 `MODULE.md`（全局总览）

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
