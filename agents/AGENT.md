# Agents 智能体域（域根） — AGENT.md

> 本文件是 `agents/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
智能体域：一切与 agent 相关的功能。按认知架构「感知-规划-行动-记忆-工具」五层组织，是系统的智能核心。

## 内部分层（感知-规划-行动-记忆-工具）
| 分类 | 范式 | 说明 |
|------|------|------|
| agents/perception/ | 感知 | 上下文管理、推理、反思（接收理解输入、评估结果） |
| agents/planning/ | 规划 | 规划角色 Agent、编排 Agent、编排引擎（规划/调度/路由/工作流/事件总线/拓扑） |
| agents/action/ | 行动 | 执行角色 Agent（代码/测试/调试/评审/调研/文档）+ 执行能力（沙箱/工具） |
| agents/memory/ | 记忆 | 多层长期记忆（12 子模块，含 semantic 知识库） |
| agents/tools/ | 工具 | 模型调用、提示词模板、运行时托管 |

## 读取目录（允许读）
- protocol/
- agents/planning/engine/
- agents/action/execution/
- tooling/configs/
- developer/specs/08_AGENT_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- developer/

## 输出
- agents/*/ 角色 Agent
- agents/memory/ 记忆（含知识库）
- agents/tools/llms/ 模型调用
- agents/tools/prompts/ 提示词
- agents/tools/runtime/ 运行时
- agents/planning/engine/ 编排引擎（规划/调度/路由/工作流/事件总线/拓扑）
- agents/action/execution/ 执行能力（执行器/工具）

## 依赖
- agents/planning/engine/ 编排调度
- agents/action/execution/ 工具执行
- protocol/ 契约

## 接口
register/invoke(agent) -> Result；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/agents/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/agents/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/agents.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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

## 下辖子模块（按感知-规划-行动-记忆-工具分类 + 公共 API）
- **agents/api/** 公共接口层：其他模块通过 `from agents.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **感知 agents/perception/**：`context/`（上下文管理）、`reasoning/`（推理）、`reflection/`（反思评估）
- **规划 agents/planning/**：`planner/`（规划角色 Agent）、`orchestrator/`（编排角色 Agent）、`engine/`（编排引擎：planner/scheduler/router/workflow/eventbus/topology）
- **行动 agents/action/**：`coder/`、`executor/`（执行角色）、`tester/`、`debugger/`、`critic/`、`reviewer/`、`researcher/`、`docwriter/`（角色 Agent）+ `execution/`（executor 沙箱 + tools 工具）
- **记忆 agents/memory/**：12 子模块（working/episodic/semantic/vector/archive/compression/retrieval/reflection/checkpoint/cache/snapshot/sync）
- **工具 agents/tools/**：`llms/`（模型调用）、`prompts/`（提示词，含 roles/）、`runtime/`（运行时托管）
