# Engine/Planner 规划器 — AGENT.md

> 本文件是 `aegisos_agents/planning/engine/planner/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
系统级任务分解与计划生成：将目标拆解为 DAG 计划，含依赖、回滚、重试策略。编排引擎成员，区别于 aegisos_agents/planning/planner 角色 Agent。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/
- aegisos_agents/planning/engine/topology/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- aegisos_agents/planning/engine/router/ 路由实现
- aegisos_agents/planning/engine/scheduler/ 调度实现
- protocol/ 类型定义

## 输出
- aegisos_agents/planning/engine/planner/strategies/ 规划策略
- aegisos_agents/planning/engine/planner/graph/ 计划图

## 依赖
- protocol/ Task/Plan
- aegisos_agents/memory/ 历史计划
- aegisos_agents/planning/engine/topology/ 图结构

## 接口
plan(goal) -> Plan(DAG)；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`pytest tests/aegisos_agents/planning/engine/planner/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/planning/engine/planner/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/planner/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/planner.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）
