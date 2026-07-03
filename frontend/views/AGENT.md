# Frontend/Views 视图层 — AGENT.md

> 本文件是 `frontend/views/` 的开发规范，隶属 `frontend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
视图层：按功能特性的 UI 组件渲染。消费 mappers/ 产出的视图模型，接收 controllers/ 分发的交互/事件，不含业务逻辑与数据转换。

## 读取目录（允许读）
- protocol/
- frontend/mappers/
- frontend/controllers/
- tooling/configs/
- developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md

## 禁止修改目录
- frontend/controllers/ 交互处理
- frontend/services/ 业务逻辑
- frontend/mappers/ 数据转换
- backend/
- protocol/ 类型定义
- agents/

## 输出
- frontend/views/canvas/ 任务编排画布（DAG 编辑、节点拖拽、运行状态可视化）
- frontend/views/graph/ 动态图可视化（WebGL/Canvas 大规模增量渲染，节点/边/权重/熵）
- frontend/views/monitor/ Agent 状态监控面板（实时指标卡片、图表、告警）
- frontend/views/replay/ 回放时间线（事件流回放、播放控制、状态快照）

## 依赖
- frontend/mappers/ 视图模型与全局状态
- frontend/controllers/ 交互分发
- protocol/ 类型（生成 TS 类型）

## 接口
渲染视图模型；上报交互到 controllers/；不含业务逻辑。

## 测试方式
`pytest tests/frontend/views/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/frontend/views/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/views/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/views.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md`。
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- 视图只做渲染与交互上报，业务逻辑走 services/，数据转换走 mappers/。
- 大图渲染：增量渲染 + 视口剔除 + LOD，避免高频重渲染（节流/批量更新）。
- 支持暗色主题；关键操作有键盘可达路径。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 下辖功能特性
- `frontend/views/canvas/` 任务编排画布（DAG 编辑/运行）
- `frontend/views/graph/` 动态图可视化（大规模图渲染）
- `frontend/views/monitor/` Agent 状态监控（实时面板）
- `frontend/views/replay/` 回放时间线（确定性回放）
