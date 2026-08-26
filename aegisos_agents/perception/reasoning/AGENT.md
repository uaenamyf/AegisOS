# Agents/Reasoning 推理 — AGENT.md

> 本文件是 `aegisos_agents/perception/reasoning/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
推理链/树与策略：CoT/ToT/ReAct 等推理范式封装，产出可追溯推理过程。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/
- aegisos_agents/tools/llms/
- aegisos_agents/tools/prompts/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- aegisos_agents/planning/engine/
- protocol/ 类型定义

## 输出
- aegisos_agents/perception/reasoning/chains/
- aegisos_agents/perception/reasoning/trees/
- aegisos_agents/perception/reasoning/strategies/

## 依赖
- aegisos_agents/tools/llms/ 模型
- aegisos_agents/memory/ 检索
- protocol/ Task

## 接口
reason(task) -> ReasoningTrace；可追溯、可回放。

## 实现状态

| 策略 | 状态 | 核心能力 |
|------|:----:|----------|
| `strategies/plan_mode.py` | ✅ AP1 | 先规划策略，再生成结构化产出 |
| `strategies/goal_mode.py` | ✅ AP3 | 递归目标分解、失败重试和备选路径 |
| `strategies/react_mode.py` | ✅ AP2.1 | 通用 think→act→observe 循环、轨迹回放、错误观察和轮数保护 |
| `strategies/ask_mode.py` | 🔲 AP4 | 人机澄清与超时降级 |

AP2.1 只提供纯编排内核，不直接执行系统命令或网络操作。AP2.2-AP2.6 已由
action 层五个 Agent 通过受控 `ExecutionAPI` 接入；危险工具的真实执行仍必须在
H1 Docker 沙箱中完成。

## 测试方式
`pytest tests/aegisos_agents/perception/reasoning/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

AP2.1 定向测试：`pytest tests/aegisos_agents/perception/test_react_mode.py`（13 用例，
`react_mode.py` 覆盖率 100%）。

## 日志位置
`logs/aegisos_agents/perception/reasoning/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/reasoning/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

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
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）
