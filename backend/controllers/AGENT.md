# Backend/Controllers 控制器层 — AGENT.md

> 本文件是 `backend/controllers/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
控制器层：接收 HTTP/WebSocket/SSE 请求，参数校验，调用 service，封装响应。**不含业务逻辑**，只做入参出参与流转。

## 读取目录（允许读）
- protocol/
- backend/services/
- backend/gateway/
- tooling/configs/
- developer/specs/05_API_SPEC.md

## 禁止修改目录
- backend/services/ 业务逻辑
- backend/mappers/ 持久化实现
- frontend/
- protocol/ 类型定义
- agents/

## 输出
- backend/controllers/api/ API 控制器（REST 路由）
- backend/controllers/ws/ WebSocket 控制器（实时双向）
- backend/controllers/sse/ SSE 控制器（事件流推送）
- backend/controllers/schemas/ 请求/响应 Schema（由 protocol/ 类型生成）
- backend/controllers/middleware/ 中间件（trace/session/task id 透传、错误处理）

## 依赖
- backend/services/ 服务
- protocol/ 契约
- backend/gateway/ 入口

## 接口
REST + WebSocket + SSE；经 backend/gateway/ 入口；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`pytest tests/backend/controllers/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/controllers/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/controllers/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/controllers.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 控制器不写业务逻辑，只做参数校验 + 调 service + 封装响应。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **API 边界**：backend/api/ — from backend.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）
