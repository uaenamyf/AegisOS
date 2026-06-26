# Frontend/Controllers 控制器层 — AGENT.md

> 本文件是 `frontend/controllers/` 的开发规范，隶属 `frontend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
控制器层：接收用户交互（点击/拖拽/输入）与后端推送事件（WS/SSE），参数校验，调用 service，分发到 views。**不含业务逻辑**。

## 读取目录（允许读）
- protocol/
- frontend/services/
- frontend/views/
- tooling/configs/
- developer/FRONTEND_GUIDE.md

## 禁止修改目录
- frontend/services/ 业务逻辑
- frontend/mappers/ 数据转换
- backend/
- protocol/ 类型定义
- agents/

## 输出
- frontend/controllers/interaction/ 用户交互控制器（画布操作/图谱交互/监控筛选/回放控制）
- frontend/controllers/events/ 后端事件控制器（WS/SSE 事件分发）
- frontend/controllers/routes/ 前端路由（页面/视图切换）

## 依赖
- frontend/services/ 服务
- frontend/views/ 视图
- protocol/ 契约（事件类型）

## 接口
接收交互/事件 -> 调 service -> 分发到 views；不含业务逻辑。

## 测试方式
`pytest tests/frontend/controllers/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/frontend/controllers/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/controllers/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/controllers.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/FRONTEND_GUIDE.md`。
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- 控制器不写业务逻辑，只做交互/事件处理 + 调 service + 分发到 views。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
