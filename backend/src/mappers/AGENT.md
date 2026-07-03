# Backend/Mappers 映射器层 — AGENT.md

> 本文件是 `backend/src/mappers/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
映射器层：数据转换与持久化访问。负责 protocol/ 类型 <-> DB 模型 <-> DTO 之间的转换，以及仓储/DAO 实现。是数据进出后端的关口。

## 读取目录（允许读）
- protocol/
- backend/src/services/
- tooling/configs/
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/src/controllers/ 路由
- backend/src/services/ 业务逻辑
- frontend/
- protocol/ 类型定义
- agents/

## 输出
- backend/src/mappers/entities.py DB 实体模型（ORM 映射）
- backend/src/mappers/converters.py 类型转换器（protocol <-> entity <-> dto）
- backend/src/mappers/repositories.py 仓储实现（CRUD、查询）
- backend/src/mappers/database.py 数据库引擎与会话工厂

## 依赖
- protocol/ 契约（数据类型来源）
- tooling/configs/ 数据库配置

## 接口
供 backend/src/services/ 调用；封装所有数据访问，service 不直接操作 DB。

## 测试方式
`pytest tests/backend/mappers/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/mappers/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/mappers/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/mappers.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 映射器只做数据转换与持久化，不含业务逻辑。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **API 边界**：backend/src/api/ — `from backend.src.api import ...`
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）
