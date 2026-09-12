# Backend/Repositories 仓储层 — AGENT.md

> 本文件是 `backend/repositories/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
仓储层：数据访问。DB 引擎/会话工厂 + Session/Task 仓储 CRUD。封装所有数据库操作，向上层提供领域友好的接口。

## 读取目录（允许读）
- backend/models/
- protocol/
- tooling/configs/
- developer/specs/06_SCHEMA_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/services/（服务层）
- backend/core/（组合根/鉴权/中间件）
- protocol/
- developer/
- frontend/

## 输出
- repositories/database.py — DB 引擎初始化、AsyncSession 工厂、get_db 依赖
- repositories/repositories.py — SessionRepository / TaskRepository（CRUD 操作）
- repositories/__init__.py — barrel 导出

## 依赖
- backend/models/entities.py — ORM 实体定义
- backend/models/converters.py — Entity↔protocol 转换
- protocol/ — 数据契约类型
- tooling/configs/ — 数据库连接配置

## 接口
- SessionRepository: create / get_by_id / list / update_status / close
- TaskRepository: create / get_by_id / list_by_session / update_status
- get_db: FastAPI 依赖注入 AsyncSession

## 测试方式
`pytest tests/backend/`，使用内存 SQLite，覆盖 CRUD、分页、异常。

## 配置位置
`tooling/configs/backend.yaml` 中 `database.url`（开发用 sqlite+aiosqlite，生产可换 PostgreSQL）。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **数据 Schema**：developer/specs/06_SCHEMA_SPEC.md
- **模型层**：backend/models/（ORM 实体 + 转换器）
- **服务层**：backend/services/（调用方）
- **组合根**：backend/core/composition.py（DI 装配）
