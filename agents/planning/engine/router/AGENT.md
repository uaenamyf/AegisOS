# Engine/Router 动态图路由 — AGENT.md

> 本文件是 `agents/planning/engine/router/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
动态异构拓扑路由：维护 Agent/Task/Memory/Tool 节点与边，计算低熵通信路径，自适应更新图。赛题核心亮点。

## 读取目录（允许读）
- protocol/
- agents/planning/engine/topology/
- agents/memory/
- agents/
- tooling/configs/
- developer/specs/04_PROTOCOL_SPEC.md

## 禁止修改目录
- frontend/
- agents/planning/engine/planner/ 规划逻辑
- protocol/ 类型定义

## 输出
- agents/planning/engine/router/graph/ 动态图
- agents/planning/engine/router/policies/ 路由策略
- agents/planning/engine/router/scoring/ 评分

## 依赖
- agents/planning/engine/topology/ 拓扑
- agents/ 能力注册
- protocol/ Graph/Route

## 接口
route(task) -> Route；动态计算 Agent->Planner->Memory->Coder->Reviewer->Executor 链；详见 developer/specs/04_PROTOCOL_SPEC.md。

## 测试方式
`pytest tests/agents/planning/engine/router/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/engine/router/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/router/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/router.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。
