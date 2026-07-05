# Backend/Core 核心层 — AGENT.md

> 本文件是 `backend/core/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
核心层：组合根(DI 装配)、鉴权、中间件、路由聚合。应用的入口配置与依赖注入中心。

## 读取目录（允许读）
- backend/routers/
- backend/services/
- backend/repositories/
- backend/models/
- backend/mocks/
- backend/schemas/
- aegisos_agents/api/
- protocol/
- tooling/configs/
- developer/specs/05_API_SPEC.md
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/services/（服务层，只通过 DI 端口引用）
- backend/repositories/（仓储层）
- backend/models/（ORM 实体）
- protocol/
- developer/
- frontend/

## 输出
- core/composition.py — 组合根：Composition 类（DI 容器）、get_composition() / reset_composition()、FastAPI 依赖提供者、Annotated 别名
- core/auth.py — API Key 鉴权（verify_api_key 依赖）
- core/middleware.py — TraceMiddleware（请求追踪）+ get_trace_id 依赖
- core/routes.py — 路由聚合（gateway_router：鉴权 + 挂载 routers/ + sse + ws）
- core/__init__.py — barrel 导出

## 依赖
- backend/services/di_ports.py — DI 端口 Protocol 定义
- backend/services/*_service.py — Service 实现
- backend/repositories/database.py — DB 引擎/会话工厂
- backend/repositories/repositories.py — 仓储实现
- backend/routers/ — 路由实现
- backend/mocks/ — aegisos_agents.api 端口 mock 实现（开发/测试模式）
- backend/schemas/ — 请求/响应 Schema
- aegisos_agents/api/ — 智能体域公共接口（端口定义）
- protocol/ — 数据契约
- tooling/configs/ — 配置

## 接口
- Composition: 组合根容器（持有所有 service/repository 实例）
- get_composition() -> Composition: 获取单例（含 reset 支持）
- FastAPI 依赖提供者: get_session_service / get_task_service / ...
- Annotated 别名: SessionServiceDep / TaskServiceDep / ...

## 测试方式
`pytest tests/backend/`，覆盖 DI 装配、reset 行为、鉴权流程。

## 配置位置
`tooling/configs/backend.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **API 契约**：developer/specs/05_API_SPEC.md
- **接口边界**：developer/specs/10_INTERFACE_BOUNDARY_SPEC.md
- **DI 端口**：backend/services/di_ports.py（Protocol 接口定义）
- **Mock 实现**：backend/mocks/（aegisos_agents.api 端口 mock）
- **路由层**：backend/routers/（路由实现）
