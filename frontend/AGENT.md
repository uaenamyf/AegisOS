# Frontend 前端表现层（域根） — AGENT.md

> 本文件是 `frontend/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。
>
> **目录结构**：所有源码位于 `frontend/src/` 下（与后端 `backend/src/` 结构对齐）。`frontend/` 根仅含配置文件 + `src/`。

## 职责
AI Native IDE 与群体智能可视化交互层。采用与后端对称的 **Controller-Service-Mapper** 三层架构 + Views 视图层。

## 内部分层（Controller-Service-Mapper + Views）
| 分类 | 角色 | 说明 |
|------|------|------|
| frontend/src/controllers/ | 控制器 | 接收用户交互与后端事件，参数校验，调用 service，分发到 views |
| frontend/src/services/ | 服务 | 前端业务逻辑：API 调用、WebSocket/SSE 管理、状态编排 |
| frontend/src/mappers/ | 映射器 | 数据转换：protocol/ <-> 视图模型 <-> API 请求/响应，共享工具与状态 |
| frontend/src/views/ | 视图 | 按功能特性的 UI 组件：chat/canvas/graph/monitor/replay |

## 读取目录（允许读）
- backend/
- protocol/
- tooling/configs/
- developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md

## 禁止修改目录
- backend/
- protocol/ 类型定义
- agents/

## 输出
- frontend/src/controllers/ 控制器（交互/事件处理）
- frontend/src/services/ 服务（API 调用、WS/SSE 管理、状态编排）
- frontend/src/mappers/ 映射器（数据转换、共享工具、全局状态）
- frontend/src/views/ 视图（chat/canvas/graph/monitor/replay）

## 依赖
- backend/ API
- protocol/ 消息类型

## 接口
REST + WebSocket + SSE；详见 developer/specs/05_API_SPEC.md。

## 测试方式
`npm test`（Vitest 单元测试）+ `npm run test:e2e`（Playwright 端到端测试），覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/frontend/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/frontend/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/frontend.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md`。
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- API 调用统一经 backend/gateway，类型由 `developer/specs/05_API_SPEC.md` 生成。
- 控制器不写业务逻辑，只做交互/事件处理 + 调 service + 分发到 views。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 调用链路
```
用户交互/后端事件 -> frontend/src/controllers/（交互处理/事件分发）
  -> frontend/src/services/（API 调用/WS·SSE 管理/状态编排）
  -> frontend/src/mappers/（数据转换/视图模型构建/全局状态）
  -> frontend/src/views/（UI 渲染：chat/canvas/graph/monitor/replay）
```


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 12_TECH_STACK_SPEC.md
- **数据契约**：protocol/ 类型（经 gen_ts_types 生成 frontend/src/protocol/types.ts）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（G 攻防视图）

## 下辖子模块
- **frontend/src/controllers/** — 控制器：接收用户交互与后端推送事件，参数校验，调用 service，分发到 views。不含业务逻辑。
- **frontend/src/services/** — 服务：前端业务逻辑核心。API 调用（经 backend/gateway）、WebSocket/SSE 连接管理、状态编排。
- **frontend/src/mappers/** — 映射器：数据转换（protocol <-> 视图模型 <-> API 请求/响应）、共享工具函数、全局状态管理、主题样式与静态资产。
- **frontend/src/views/** — 视图：按功能特性的 UI 组件。`chat/`(Agent 对话)、`canvas/`(任务画布)、`graph/`(动态图可视化)、`monitor/`(Agent 监控)、`replay/`(回放时间线)。
- **frontend/src/protocol/** — 类型定义：`types.ts`(自动生成) + `frontend-types.ts`(手维护前端本地类型)。
