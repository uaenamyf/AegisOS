# Backend/Services 服务层 — AGENT.md

> 本文件是 `backend/services/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
服务层：业务逻辑核心。用例编排（会话管理、任务下发、Agent 编排），事务管理，调用 agents/ 子系统与 backend/mappers/。控制器与持久化之间的业务中枢。

## 读取目录（允许读）
- protocol/
- backend/mappers/
- backend/controllers/
- agents/
- agents/planning/engine/
- tooling/configs/
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/controllers/ 路由
- backend/mappers/ 数据转换实现
- frontend/
- protocol/ 类型定义
- agents/ 业务实现（仅调用）

## 输出
- backend/services/session/ 会话服务
- backend/services/task/ 任务服务（创建/查询/取消）
- backend/services/agent/ Agent 编排服务（桥接 agents/）
- backend/services/memory/ 记忆服务（桥接 agents/memory/）
- backend/services/graph/ 动态图服务（桥接 agents/planning/engine/topology/）

## 依赖
- backend/mappers/ 数据转换与持久化
- agents/ 智能体域
- protocol/ 契约

## 接口
供 backend/controllers/ 调用；编排 agents/ 与 mappers/；管理事务。

## 测试方式
`pytest tests/backend/services/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/services/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/services/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/services.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 服务层专注业务逻辑；数据访问走 mappers/，路由走 controllers/。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **下游·本模块调谁**：agents/api（RuntimeAPI 编排）+ DI 端口（plans/13 §3）
- **API 边界**：backend/api/ — from backend.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）
