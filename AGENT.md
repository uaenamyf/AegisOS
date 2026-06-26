# AegisOS — AGENT.md（仓库总规范）

> 这是整个 AegisOS 仓库的**最高开发规范**。任何 Agent（人或 AI）在开发本仓库前，**第一步必须阅读本文件**，再按需阅读 `developer/` 下相应规范，而不是扫描整个项目。

## 项目定位
AegisOS 是面向「挑战杯揭榜挂帅 + 荣耀群体智能赛题」的 **Agent Operating System (AOS) + AI Native IDE**。不仅包含 Agent，而是让整个项目可由 Agent 自主开发。核心特性：动态异构群体智能、长期记忆、低熵通信、端边云协同、可运行系统。

## AI 开发流程（Developer Workflow）
```
Developer Agent
  -> 读取 developer/ 规范
  -> 读取 developer/roadmap/ 定位当前阶段
  -> 读取目标模块的 AGENT.md
  -> 读取 protocol/ 契约
  -> 读取 tooling/configs/ 配置
  -> 生成代码
  -> 运行 Test
  -> 生成/更新 Doc
  -> Commit
```
Agent 永不扫描整个项目；按模块边界精准读写，效率高且不会越界破坏其他子系统。

## 仓库分层（同域聚合 + 域内分类，目录导航详见 developer/DIRECTORY_GUIDE.md）
1. **developer/** — 规范层（项目大脑）。含 `developer/roadmap/`（P0..P7）。
2. **protocol/** — 契约层，唯一数据契约。
3. **frontend/** — 表现层。Controller-Service-Mapper + Views：`controllers/`(交互/事件) · `services/`(API/实时/状态) · `mappers/`(数据转换/全局状态/共享) · `views/`(canvas·graph·monitor·replay)。
4. **backend/** — 应用层。Controller-Service-Mapper + Gateway：`gateway/`(入口) · `controllers/`(控制器) · `services/`(业务逻辑) · `mappers/`(数据转换/持久化)。
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
2. `developer/ARCHITECTURE.md`、`developer/roadmap/README.md`
3. `developer/MESSAGE_PROTOCOL.md`、`developer/CODING_RULES.md`
4. 目标模块的 `AGENT.md`
5. `protocol/` 相关契约

## 全局铁律
- **模块间解耦**：每个域通过 `api/` 子包暴露公共接口（`from {domain}.api import ...`），其他模块**只通过 api/ 调用**，禁止直接导入内部实现子包。内部可自由重构，只要 api/ 签名不变，依赖方不受影响。
- 对外数据结构必须复用 `protocol/` 类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 修改任一模块前先读该模块 `AGENT.md` 的「禁止修改目录」，不得越界。
- `api/` 接口签名变更属破坏性变更，需在 `developer/CHANGELOG.md` 标注并通知依赖方。
- 提交前运行对应测试并更新 `developer/CHANGELOG.md`。
- 新增接口同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 动态路由遵循低熵稀疏通信：按需链式通信（Agent->Planner->Memory->Coder->Reviewer->Executor），禁止全广播。

## Agent 统一生命周期
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result -> Log -> Heartbeat -> Finish

## Agent 统一接口
- `receive(task)` 接收任务并校验
- `think()` 推理与计划
- `tool()` 调用工具执行
- `reflect()` 反思与自评
- `respond()` 返回结构化结果

## 目录导航
详见 `developer/DIRECTORY_GUIDE.md`。每个目录/子模块均有独立 `AGENT.md` 规定职责、读取目录、禁止修改目录、输出、依赖、接口、测试方式、日志/Prompt/配置位置。

## README 动态维护
根 `README.md` 由 `tooling/scripts/gen_readme.py` 扫描仓库实际结构自动生成（目录树、AGENT.md 计数、api 接口表、文件统计）。目录结构或 api 变动后运行 `python3 tooling/scripts/gen_readme.py` 刷新，勿手改自动生成段。
