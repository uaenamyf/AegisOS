# Agents/Planning 规划层 — AGENT.md

> 本文件是 `aegisos_agents/planning/` 分类的开发规范，隶属 `aegisos_agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·规划（Planning）：决策与编排

## 职责
规划与编排：任务分解、动态图路由、调度、工作流推进、群体协同。将目标转化为可执行计划并编排多 Agent 协作。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/
- aegisos_agents/perception/
- tooling/configs/
- developer/specs/04_PROTOCOL_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义

## 输出
- aegisos_agents/planning/planner/ 规划角色 Agent
- aegisos_agents/planning/orchestrator/ 编排角色 Agent
- aegisos_agents/planning/engine/ 编排引擎

## 依赖
- protocol/ Task/Plan/Graph
- aegisos_agents/memory/ 历史计划
- aegisos_agents/perception/ 理解结果

## 接口
plan(goal) -> Plan(DAG)；route(task) -> Route；schedule(task) -> execution。

## 测试方式
`pytest tests/aegisos_agents/planning/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/planning/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/planning/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

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
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块
- aegisos_agents/planning/planner/ — 规划角色 Agent：将目标分解为 DAG 计划
- aegisos_agents/planning/orchestrator/ — 编排角色 Agent：协调多 Agent 协作流程
- aegisos_agents/planning/engine/ — 编排引擎：planner(系统级规划)、scheduler(调度)、router(动态图低熵路由)、workflow(DAG工作流)、eventbus(事件总线)、topology(动态异构拓扑)

---

### 🔧 SDK 集成状态

> 2026-07-06 全量排查。✅ **CyberOrchestrator 已用 SDK Agent 装配**，🔲 待深化。
> 2026-07-06 P1 编排器实现完成：EventBus / Workflow / Planner / Orchestrator / CyberRuntime 5 子任务全完成。

| 文件 | SDK 能力 | 状态 |
|------|---------|------|
| `orchestrator/cyber_orchestrator.py` | 9 个 SDK Agent 装配 + 红蓝紫链（`run_red_chain` / `run_blue_chain` / `run_purple_review`） | ✅ 部分 |
| 同上 — handoffs | 手动 `_run()` 串联 → 待用 SDK `Agent.handoffs` 声明式串联 | 🔲 R4 (P1) |
| 同上 — guardrails | 手动 `if critique.valid` 判断 → 待用 SDK `guardrails` 自动校验 + 回退重试 | 🔲 R4 (P1) |
| 同上 — tracing | `print` 日志 → 待用 SDK `tracing`（`RunTrace`）自动记录编排流程 | 🔲 R4 (P2) |
| `engine/eventbus/impl.py` | 纯 Python 实现（topic 发布/订阅 + 死信 + 历史），无 LLM 调用 | ✅ P1 完成 |
| `engine/workflow/engine.py` | 纯 Python DAG 引擎（Kahn 拓扑 + 并行 + 条件分支），无 LLM 调用 | ✅ P1 完成 |
| `planner/planner.py` | 纯算法模板分解（4 场景），不调 LLM | ✅ P1 完成 |
| `orchestrator/orchestrator.py` | 通用编排器（Planner + WorkflowEngine + EventBus 整合），可接入任意 RuntimeAPI | ✅ P1 完成 |
| `orchestrator/runtime.py` | CyberRuntime 实现 RuntimeAPI，委托 CyberOrchestrator 红蓝紫链 | ✅ P1 完成 |
| `engine/` topology/router/scheduler | 纯算法实现，无 LLM 调用 | ✅ 无需 SDK |

> 详见 `aegisos_agents/AGENT.md`「openai-agents SDK 集成状态」段 + `developer/plan.md`。
