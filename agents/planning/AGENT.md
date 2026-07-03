# Agents/Planning 规划层 — AGENT.md

> 本文件是 `agents/planning/` 分类的开发规范，隶属 `agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·规划（Planning）：决策与编排

## 职责
规划与编排：任务分解、动态图路由、调度、工作流推进、群体协同。将目标转化为可执行计划并编排多 Agent 协作。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/perception/
- tooling/configs/
- developer/specs/04_PROTOCOL_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义

## 输出
- agents/planning/planner/ 规划角色 Agent
- agents/planning/orchestrator/ 编排角色 Agent
- agents/planning/engine/ 编排引擎

## 依赖
- protocol/ Task/Plan/Graph
- agents/memory/ 历史计划
- agents/perception/ 理解结果

## 接口
plan(goal) -> Plan(DAG)；route(task) -> Route；schedule(task) -> execution。

## 测试方式
`pytest tests/agents/planning/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/planning/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/planning.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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
- agents/planning/planner/ — 规划角色 Agent：将目标分解为 DAG 计划
- agents/planning/orchestrator/ — 编排角色 Agent：协调多 Agent 协作流程
- agents/planning/engine/ — 编排引擎：planner(系统级规划)、scheduler(调度)、router(动态图低熵路由)、workflow(DAG工作流)、eventbus(事件总线)、topology(动态异构拓扑)
