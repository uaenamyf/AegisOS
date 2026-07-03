# Agents/Reasoning 推理 — AGENT.md

> 本文件是 `agents/perception/reasoning/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
推理链/树与策略：CoT/ToT/ReAct 等推理范式封装，产出可追溯推理过程。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/tools/llms/
- agents/tools/prompts/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- agents/planning/engine/
- protocol/ 类型定义

## 输出
- agents/perception/reasoning/chains/
- agents/perception/reasoning/trees/
- agents/perception/reasoning/strategies/

## 依赖
- agents/tools/llms/ 模型
- agents/memory/ 检索
- protocol/ Task

## 接口
reason(task) -> ReasoningTrace；可追溯、可回放。

## 测试方式
`pytest tests/agents/perception/reasoning/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/perception/reasoning/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/reasoning/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/reasoning.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：agents/api/ — from agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）
