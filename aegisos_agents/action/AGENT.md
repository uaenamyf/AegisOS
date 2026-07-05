# Agents/Action 行动层 — AGENT.md

> 本文件是 `agents/action/` 分类的开发规范，隶属 `agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·行动（Action）：执行与产出

## 职责
执行与产出：代码生成、测试、调试、评审、调研、文档、沙箱执行。各角色 Agent 在此层实际执行任务并产出结果。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/tools/
- agents/planning/
- tooling/configs/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- agents/planning/ 编排逻辑

## 输出
- agents/action/{recon,vuln_correlator,exploit_planner,lateral_move}/ 红队 Agent
- agents/action/{detector,triage,threat_hunt,ir_planner,forensics}/ 蓝队 Agent
- agents/action/{critic,reviewer}/ 紫队 Agent
- agents/action/execution/ 执行能力

## 依赖
- agents/tools/ 工具与模型
- agents/memory/ 上下文
- protocol/ ToolCall

## 接口
receive(task) -> think() -> tool() -> respond() -> Result。

## 测试方式
`pytest tests/agents/action/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/action/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/action/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/action.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：agents/api/ — from agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块
- agents/action/coder/ — 代码生成 Agent
- agents/action/executor/ — 执行角色 Agent（区别于 agents/action/execution/executor/ 沙箱执行器）
- agents/action/tester/ — 测试 Agent
- agents/action/debugger/ — 调试 Agent
- agents/action/critic/ — 代码评审 Agent
- agents/action/reviewer/ — 审查放行 Agent
- agents/action/researcher/ — 调研检索 Agent
- agents/action/docwriter/ — 文档 Agent
- agents/action/execution/ — 执行能力：executor(沙箱执行器) + tools(工具注册)
