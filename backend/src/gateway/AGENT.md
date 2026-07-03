# Backend/Gateway 网关 — AGENT.md

> 本文件是 `backend/src/gateway/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
网关：统一入口。鉴权、限流、路由分发、协议适配（HTTP/WS/gRPC）、请求追踪。所有外部请求经此进入后端。

## 读取目录（允许读）
- protocol/
- backend/src/controllers/
- tooling/configs/
- developer/specs/05_API_SPEC.md

## 禁止修改目录
- backend/src/controllers/ 业务路由
- backend/src/services/ 业务逻辑
- backend/src/mappers/ 持久化
- frontend/
- protocol/ 类型定义
- agents/

## 输出
- backend/src/gateway/routes.py 路由分发
- backend/src/gateway/auth.py 鉴权
- backend/src/gateway/middleware.py 限流/追踪中间件

## 依赖
- backend/src/controllers/ 后端路由
- protocol/ 契约
- tooling/configs/ 配置

## 接口
HTTP/WS/gRPC 入口；透传 X-Trace-Id/X-Session-Id/X-Task-Id；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`pytest tests/backend/gateway/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/gateway/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/gateway/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/gateway.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **API 边界**：backend/src/api/ — `from backend.src.api import ...`
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）
