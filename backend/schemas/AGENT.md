# Backend/Schemas 契约层 — AGENT.md

> 本文件是 `backend/schemas/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
契约层：Pydantic v2 请求/响应 Schema 定义。为 routers/ 提供参数校验与序列化模型。

## 读取目录（允许读）
- protocol/
- developer/specs/05_API_SPEC.md
- developer/specs/06_SCHEMA_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/services/（服务层）
- backend/repositories/（仓储层）
- backend/models/（ORM 实体）
- backend/core/（组合根）
- protocol/（类型定义，只读引用）
- developer/
- frontend/

## 输出
- schemas/__init__.py — barrel 导出所有 Pydantic v2 模型

## 依赖
- Pydantic v2（BaseModel）
- protocol/ — 数据契约类型（复用，不自造并行结构）

## 接口
- 请求模型：CreateSessionRequest / CreateTaskRequest / ...
- 响应模型：SessionResponse / TaskResponse / ...
- 分页模型：PaginatedResponse[T]

## 测试方式
`pytest tests/backend/`，覆盖序列化/反序列化、校验规则。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **API 契约**：developer/specs/05_API_SPEC.md
- **数据 Schema**：developer/specs/06_SCHEMA_SPEC.md
- **路由层**：backend/routers/（使用方）
- **协议契约**：protocol/（复用类型）
