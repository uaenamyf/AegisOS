# Obs/Visualization 可视化 — AGENT.md

> 本文件是 `observability/present/visualization/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
图表、图谱与可视化面板：动态图渲染、指标图表、拓扑布局。服务前端。

## 读取目录（允许读）
- protocol/
- aegisos_agents/planning/engine/topology/
- observability/inspect/monitor/
- tooling/configs/
- developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md

## 禁止修改目录
- backend/
- protocol/ 类型定义
- aegisos_agents/planning/engine/router/ 路由实现

## 输出
- observability/present/visualization/charts/
- observability/present/visualization/graphs/
- observability/present/visualization/dashboards/

## 依赖
- aegisos_agents/planning/engine/topology/ 图
- observability/inspect/monitor/ 指标
- protocol/ Graph

## 接口
render(data) -> View；服务前端可视化。

## 测试方式
`pytest tests/observability/present/visualization/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/observability/present/visualization/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/visualization/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/visualization.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 07_EVENT_SPEC.md
- **API 边界**：observability/api/ — from observability.api import ...
- **数据契约**：protocol/event.py（Event）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H5 评测/回放）
