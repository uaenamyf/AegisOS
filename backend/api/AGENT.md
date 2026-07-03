# Backend/API 公共接口 — AGENT.md

> 本文件是 `backend/api/` 的开发规范，隶属 `backend/` 域。这是**该域对外的唯一公共接口**，其他模块通过本接口调用本域能力，实现解耦。

## 职责
后端域公共 API：对其他模块暴露会话管理、任务管理、记忆网关、动态图、事件流等接口。其他模块只通过 `backend.api` 导入，不直接访问 backend/controllers|services|mappers|gateway 内部实现。

## 解耦原则
- **其他模块只导入 `from backend.api import ...`**，禁止直接访问 `backend/` 内部子包。
- 内部实现可自由重构，只要 `api/` 接口签名不变，依赖方不受影响。
- 接口参数与返回值一律使用 `protocol/` 定义的类型。

## 读取目录（允许读）
- protocol/
- tooling/configs/

## 禁止修改目录
- backend/ 内部实现（controllers/services/mappers/gateway）
- frontend/
- agents/
- protocol/ 类型定义

## 输出
- backend/api/__init__.py 公共 Protocol 接口
- SessionAPI / TaskAPI / MemoryGatewayAPI / GraphAPI / EventStreamAPI

## 依赖
- protocol/ 契约
- tooling/configs/ 配置

## 接口
其他模块 `from backend.api import TaskAPI` 等接口；实现由 backend/ 内部注入。

## 暴露的接口清单
SessionAPI(创建/查询/关闭会话) · TaskAPI(创建/查询/取消任务) · MemoryGatewayAPI(读写记忆) · GraphAPI(获取图/订阅更新) · EventStreamAPI(事件流/发消息)

## 测试方式
`pytest tests/backend/api/`，验证接口契约与 mock 兼容性，覆盖率目标 >= 80%。

## 日志位置
`logs/backend/api/`（结构化 JSON 日志，按 session/task 切分）。

## 配置位置
`tooling/configs/backend_api.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 接口参数/返回值必须复用 `protocol/` 类型，禁止自造并行结构。
- 接口签名变更属于**破坏性变更**，需在 `developer/CHANGELOG.md` 标注并通知所有依赖方。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md
- **下游·本模块调谁**：agents/api（RuntimeAPI 编排）+ DI 端口（plans/13 §3）
- **API 边界**：backend/api/ — from backend.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）
