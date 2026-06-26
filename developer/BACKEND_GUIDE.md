# BACKEND_GUIDE.md — 后端规范

> 后端服务位于 `backend/`，采用经典 **Controller-Service-Mapper** 三层架构 + Gateway 网关入口。

## 架构
```
请求 -> backend/gateway/（鉴权/限流/路由分发/协议适配）
  -> backend/controllers/（参数校验/响应封装，不含业务逻辑）
  -> backend/services/（业务逻辑/用例编排/事务）
  -> backend/mappers/（数据转换/持久化访问）
  -> agents/（智能体域）/ protocol/（契约）
```

## 结构
### backend/gateway/ 网关
- `routes/` 路由分发 · `auth/` 鉴权 · `middleware/` 限流/追踪 · `adapters/` 协议适配（HTTP/WS/gRPC）
- 统一入口，透传 X-Trace-Id/X-Session-Id/X-Task-Id。

### backend/controllers/ 控制器
- `api/` REST 控制器 · `ws/` WebSocket 控制器 · `sse/` SSE 控制器 · `schemas/` 请求响应 Schema · `middleware/` 中间件
- 只做参数校验 + 调 service + 封装响应，**不含业务逻辑**。

### backend/services/ 服务
- `session/` 会话服务 · `task/` 任务服务（创建/查询/取消）· `agent/` Agent 编排服务 · `memory/` 记忆桥接 · `graph/` 动态图桥接
- 业务逻辑核心：用例编排、事务管理、调用 agents/ 与 mappers/。

### backend/mappers/ 映射器
- `entities/` DB 实体模型（ORM 映射）· `dto/` 数据传输对象 · `repositories/` 仓储实现（CRUD/查询）· `converters/` 类型转换器（protocol <-> entity <-> dto）
- 数据转换与持久化访问，service 不直接操作 DB。

## 约定
- 入口经 gateway，不直接暴露；透传 trace/session/task id。
- 请求/响应使用 `protocol/` 类型或其生成的 Schema。
- 业务逻辑放 services/，controllers/ 仅校验与编排，mappers/ 仅数据转换与持久化。
- 与 agents/ 通信走 gRPC（内部）或 eventbus（异步）。
- 热数据 DB；冷数据走 agents/memory/archive。迁移脚本版本化。
- 错误统一 `{code, message, trace_id}`；5xx 记录完整堆栈到 logs/。

## 端点
详见 `developer/API_SPEC.md`。REST + WebSocket + SSE，统一 `/api/v1/...`。
