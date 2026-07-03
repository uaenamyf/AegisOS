# Frontend/Services 服务层 — AGENT.md

> 本文件是 `frontend/services/` 的开发规范，隶属 `frontend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
服务层：前端业务逻辑核心。API 调用（经 backend/gateway）、WebSocket/SSE 连接管理与消息处理、状态编排。控制器与映射器之间的业务中枢。

## 读取目录（允许读）
- protocol/
- frontend/controllers/
- frontend/mappers/
- backend/
- tooling/configs/
- developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md

## 禁止修改目录
- frontend/controllers/ 交互处理
- frontend/mappers/ 数据转换
- frontend/views/ UI 组件
- backend/
- protocol/ 类型定义
- agents/

## 输出
- frontend/services/api/ API 调用服务（REST 请求封装，经 backend/gateway）
- frontend/services/realtime/ 实时服务（WebSocket/SSE 连接管理与消息分发）
- frontend/services/session/ 会话服务（会话状态、任务状态）
- frontend/services/graph/ 动态图服务（图数据获取与更新订阅）

## 依赖
- frontend/mappers/ 数据转换与全局状态
- backend/ API
- protocol/ 契约

## 接口
供 frontend/controllers/ 调用；管理 API 调用与实时连接；编排状态。

## 测试方式
`pytest tests/frontend/services/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/frontend/services/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/services/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/services.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md`。
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- 服务层专注业务逻辑；数据转换走 mappers/，交互分发走 controllers/。
- API 调用统一经 backend/gateway。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。
