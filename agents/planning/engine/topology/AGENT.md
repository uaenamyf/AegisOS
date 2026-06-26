# Engine/Topology 动态拓扑 — AGENT.md

> 本文件是 `agents/planning/engine/topology/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
动态异构拓扑图构建与布局：节点/边/权重/熵/延迟/信任度维护，图变更事件。供 router 消费。

## 读取目录（允许读）
- protocol/
- agents/planning/engine/router/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- agents/planning/engine/planner/
- protocol/ 类型定义

## 输出
- agents/planning/engine/topology/graph/
- agents/planning/engine/topology/layout/
- agents/planning/engine/topology/metrics/

## 依赖
- agents/planning/engine/router/ 路由消费
- protocol/ Graph/GraphUpdate

## 接口
build/update_graph() -> Graph；产出动态异构拓扑。

## 测试方式
`pytest tests/agents/planning/engine/topology/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/engine/topology/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/topology/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/topology.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
