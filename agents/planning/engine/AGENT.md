# Engine 编排引擎层（域根） — AGENT.md

> 本文件是 `agents/planning/engine/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
编排引擎层：系统级规划、调度、动态图路由、工作流、事件总线、拓扑。编排 agents 域中的多个智能体协同。

## 读取目录（允许读）
- protocol/
- agents/
- tooling/configs/
- developer/specs/01_ARCHITECTURE_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子模块内部实现

## 输出
- agents/planning/engine/planner/ 规划
- agents/planning/engine/scheduler/ 调度
- agents/planning/engine/router/ 路由
- agents/planning/engine/workflow/ 工作流
- agents/planning/engine/eventbus/ 事件总线
- agents/planning/engine/topology/ 拓扑

## 依赖
- agents/ 智能体
- protocol/ 契约
- tooling/configs/

## 接口
编排 agents 完成任务；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/agents/planning/engine/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/engine/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/agents/planning/engine/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/engine.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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

## 下辖子模块
- `agents/planning/engine/planner/` 任务分解为 DAG 计划
- `agents/planning/engine/scheduler/` 调度执行单元
- `agents/planning/engine/router/` 动态图低熵路由（赛题亮点）
- `agents/planning/engine/workflow/` DAG 工作流引擎
- `agents/planning/engine/eventbus/` 发布订阅事件总线
- `agents/planning/engine/topology/` 动态异构拓扑
