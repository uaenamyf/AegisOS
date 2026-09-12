# Backend/Models 模型层 — AGENT.md

> 本文件是 `backend/models/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
模型层：ORM 实体定义与 protocol↔Entity 转换器。定义数据库表结构映射，提供与 protocol 契约类型的双向转换。

## 读取目录（允许读）
- protocol/
- developer/specs/06_SCHEMA_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/services/（服务层）
- backend/repositories/（仓储层）
- backend/core/（组合根/鉴权/中间件）
- protocol/（类型定义，只读引用）
- developer/
- frontend/

## 输出
- models/entities.py — SQLAlchemy 2.0 ORM 实体（SessionEntity / TaskEntity 等）
- models/converters.py — protocol 契约 ↔ ORM Entity 双向转换函数
- models/__init__.py — barrel 导出

## 依赖
- protocol/ — 数据契约类型（Session / Task 等）
- SQLAlchemy 2.0（ORM 基类/列类型）

## 接口
- SessionEntity / TaskEntity: ORM 实体（表结构定义）
- to_entity(protocol_obj) / from_entity(orm_obj): 双向转换

## 测试方式
`pytest tests/backend/`，覆盖转换正确性、字段映射完整性。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **数据 Schema**：developer/specs/06_SCHEMA_SPEC.md
- **仓储层**：backend/repositories/（使用 Entity）
- **服务层**：backend/services/（使用 converters）
- **协议契约**：protocol/message.py / protocol/scheduler.py
