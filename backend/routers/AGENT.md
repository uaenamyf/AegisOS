# Backend/Routers 路由层 — AGENT.md

> 本文件是 `backend/routers/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
路由层：接收 HTTP/WS/SSE 请求，参数校验，调用 service，封装响应。**不含业务逻辑**。

## 读取目录（允许读）
- backend/services/
- backend/schemas/
- backend/core/
- protocol/
- developer/specs/05_API_SPEC.md
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/services/（业务逻辑）
- backend/repositories/（数据访问）
- backend/models/（ORM 实体）
- backend/core/（组合根/鉴权/中间件）
- protocol/
- developer/
- frontend/

## 输出
- routers/{health,sessions,tasks,agents,memory,graph,tools,metrics,replay}.py — REST 路由
- routers/sse.py — SSE 事件流
- routers/ws.py — WebSocket 双向流
- routers/__init__.py — 路由聚合 barrel 导出

## 依赖
- backend/services/ — 业务逻辑调用
- backend/schemas/ — 请求/响应 Schema
- backend/core/composition.py — 依赖注入获取 service 实例
- protocol/ — 数据契约类型

## 接口
- FastAPI APIRouter 实例（每个文件一个 router）
- 经 `backend/routers/__init__.py` 聚合为统一 router

## 测试方式
`pytest tests/backend/`，覆盖路由参数校验、响应码、异常处理。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **API 契约**：developer/specs/05_API_SPEC.md
- **接口边界**：developer/specs/10_INTERFACE_BOUNDARY_SPEC.md
- **组合根**：backend/core/composition.py（DI 装配）
- **服务层**：backend/services/（业务逻辑）
- **契约层**：backend/schemas/（Pydantic v2 Schema）
