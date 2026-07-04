# Backend 后端应用层（域根） — AGENT.md

> 本文件是 `backend/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。
>
> **目录结构**：采用经典 Python 四层扁平架构 `backend/{routers,services,repositories,models}` + 辅助层 `core/schemas/mocks`。`backend/` 根含 `AGENT.md` + `__init__.py` + `main.py` + `api.py` + 各子目录。

## 职责
后端应用层：提供会话管理、任务持久化、Agent 编排 API，与各子系统桥接。采用经典 **Router-Service-Repository-Model** 四层架构 + Core 网关入口。

## 内部分层（Router-Service-Repository-Model）
| 分类 | 角色 | 说明 |
|------|------|------|
| backend/routers/ | 路由层 | 接收请求、参数校验、调用 service、返回响应（不含业务逻辑） |
| backend/services/ | 服务层 | 业务逻辑核心：用例编排、事务、调用 agents/ 与 repositories/ |
| backend/repositories/ | 仓储层 | 数据访问：DB 引擎/会话工厂 + Session/Task 仓储 CRUD |
| backend/models/ | 模型层 | ORM 实体定义与 protocol↔Entity 转换器 |
| backend/core/ | 核心层 | 组合根(DI)、鉴权、中间件、路由聚合 |
| backend/schemas/ | 契约层 | Pydantic v2 请求/响应 Schema |
| backend/mocks/ | 模拟层 | agents.api 端口的 mock 实现（AgentRegistry/Runtime/Memory/Execution/EventBus） |

## 读取目录（允许读）
- protocol/
- agents/
- agents/planning/engine/
- tooling/configs/
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- developer/

## 输出
- backend/routers/ 路由层（路由、参数校验、响应封装）
- backend/services/ 服务层（业务逻辑、用例编排、事务）
- backend/repositories/ 仓储层（DB 引擎、会话工厂、CRUD 仓储）
- backend/models/ 模型层（ORM 实体、转换器）
- backend/core/ 核心层（组合根 DI、鉴权、中间件、路由聚合）
- backend/schemas/ 契约层（Pydantic v2 请求/响应 Schema）
- backend/mocks/ 模拟层（agents.api 端口 mock 实现）

## 依赖
- core/ 入口（组合根 DI、鉴权、中间件）
- agents/ 智能体域
- agents/planning/engine/ 编排
- protocol/ 契约

## 接口
REST/WebSocket/SSE；统一经 backend/core/ 入口；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`pytest tests/backend/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/backend/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/backend.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 调用链路
```
请求 -> backend/core/（鉴权/中间件/路由聚合）
  -> backend/routers/（参数校验/响应封装）
  -> backend/services/（业务逻辑/用例编排/事务）
  -> backend/repositories/（数据访问/持久化）
  -> backend/models/（ORM 实体/转换器）
  -> agents/（智能体域）/ protocol/（契约）
```


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **API 边界**：backend/api.py — `from backend.api import ...`
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）

## 下辖子模块
- **backend/api.py** 公共接口层：其他模块通过 `from backend.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **backend/routers/** — 路由层：接收 HTTP/WS/SSE 请求，参数校验，调用 service，封装响应。不含业务逻辑。
- **backend/services/** — 服务层：业务逻辑核心。用例编排（会话管理、任务下发、Agent 编排），事务管理，调用 agents/ 与 repositories/。含 DI 端口实现。
- **backend/repositories/** — 仓储层：数据访问。DB 引擎/会话工厂 + Session/Task 仓储 CRUD。
- **backend/models/** — 模型层：ORM 实体定义与 protocol↔Entity 转换器。
- **backend/core/** — 核心层：组合根(DI 装配)、鉴权、中间件、路由聚合。
- **backend/schemas/** — 契约层：Pydantic v2 请求/响应 Schema。
- **backend/mocks/** — 模拟层：agents.api 端口的 mock 实现（AgentRegistry/Runtime/Memory/Execution/EventBus）。
