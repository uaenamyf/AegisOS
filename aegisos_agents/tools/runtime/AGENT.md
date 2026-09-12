# Agents/Runtime 运行时 — AGENT.md

> 本文件是 `aegisos_agents/tools/runtime/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
Agent 运行时与生命周期管理：上下文注入、心跳、挂起/恢复、资源隔离。托管各角色 Agent 生命周期。

## 读取目录（允许读）
- protocol/
- aegisos_agents/
- aegisos_agents/memory/
- tooling/configs/
- developer/specs/08_AGENT_SPEC.md

## 禁止修改目录
- frontend/
- aegisos_agents/planning/engine/ 编排逻辑
- protocol/ 类型定义

## 输出
- aegisos_agents/tools/runtime/contexts/
- aegisos_agents/tools/runtime/hooks/
- aegisos_agents/tools/runtime/lifecycle/

## 依赖
- aegisos_agents/ 角色定义
- aegisos_agents/memory/ 状态
- protocol/ Heartbeat

## 接口
run(agent, task) -> Result；管理 Initialize->...->Finish 生命周期。

## 测试方式
`pytest tests/aegisos_agents/tools/runtime/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/tools/runtime/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/runtime/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/runtime.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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
