# Engine/Planner 规划器 — AGENT.md

> 本文件是 `agents/planning/engine/planner/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
系统级任务分解与计划生成：将目标拆解为 DAG 计划，含依赖、回滚、重试策略。编排引擎成员，区别于 agents/planning/planner 角色 Agent。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/planning/engine/topology/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- agents/planning/engine/router/ 路由实现
- agents/planning/engine/scheduler/ 调度实现
- protocol/ 类型定义

## 输出
- agents/planning/engine/planner/strategies/ 规划策略
- agents/planning/engine/planner/graph/ 计划图

## 依赖
- protocol/ Task/Plan
- agents/memory/ 历史计划
- agents/planning/engine/topology/ 图结构

## 接口
plan(goal) -> Plan(DAG)；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`pytest tests/agents/planning/engine/planner/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/engine/planner/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/planner/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/planner.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。
