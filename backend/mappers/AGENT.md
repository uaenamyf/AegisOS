# Backend/Mappers 映射器层 — AGENT.md

> 本文件是 `backend/mappers/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
映射器层：数据转换与持久化访问。负责 protocol/ 类型 <-> DB 模型 <-> DTO 之间的转换，以及仓储/DAO 实现。是数据进出后端的关口。

## 读取目录（允许读）
- protocol/
- backend/services/
- tooling/configs/
- developer/BACKEND_GUIDE.md

## 禁止修改目录
- backend/controllers/ 路由
- backend/services/ 业务逻辑
- frontend/
- protocol/ 类型定义
- agents/

## 输出
- backend/mappers/entities/ DB 实体模型（ORM 映射）
- backend/mappers/dto/ 数据传输对象（请求/响应转换）
- backend/mappers/repositories/ 仓储实现（CRUD、查询）
- backend/mappers/converters/ 类型转换器（protocol <-> entity <-> dto）

## 依赖
- protocol/ 契约（数据类型来源）
- tooling/configs/ 数据库配置

## 接口
供 backend/services/ 调用；封装所有数据访问，service 不直接操作 DB。

## 测试方式
`pytest tests/backend/mappers/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/mappers/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/mappers/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/mappers.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 映射器只做数据转换与持久化，不含业务逻辑。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
