# Backend/Gateway 网关 — AGENT.md

> 本文件是 `backend/gateway/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
网关：统一入口。鉴权、限流、路由分发、协议适配（HTTP/WS/gRPC）、请求追踪。所有外部请求经此进入后端。

## 读取目录（允许读）
- protocol/
- backend/controllers/
- tooling/configs/
- developer/API_SPEC.md

## 禁止修改目录
- backend/controllers/ 业务路由
- backend/services/ 业务逻辑
- backend/mappers/ 持久化
- frontend/
- protocol/ 类型定义
- agents/

## 输出
- backend/gateway/routes/ 路由分发
- backend/gateway/auth/ 鉴权
- backend/gateway/middleware/ 限流/追踪中间件
- backend/gateway/adapters/ 协议适配（HTTP/WS/gRPC）

## 依赖
- backend/controllers/ 后端路由
- protocol/ 契约
- tooling/configs/ 配置

## 接口
HTTP/WS/gRPC 入口；透传 X-Trace-Id/X-Session-Id/X-Task-Id；详见 developer/API_SPEC.md。

## 测试方式
`pytest tests/backend/gateway/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/gateway/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/gateway/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/gateway.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
