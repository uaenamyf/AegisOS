# Agents/API 公共接口 — AGENT.md

> 本文件是 `aegisos_agents/api/` 的开发规范，隶属 `aegisos_agents/` 域。这是**该域对外的唯一公共接口**，其他模块通过本接口调用本域能力，实现解耦。

## 职责
智能体域公共 API：对其他模块暴露 Agent 注册/调用、记忆读写、规划/路由/调度、工具执行、推理/反思、事件总线、运行时心跳等接口。其他模块只通过 `aegisos_agents.api` 导入，不直接访问 aegisos_agents/perception|planning|action|memory|tools 内部实现。

## 解耦原则
- **其他模块只导入 `from aegisos_agents.api import ...`**，禁止直接访问 `aegisos_agents/` 内部子包。
- 内部实现可自由重构，只要 `api/` 接口签名不变，依赖方不受影响。
- 接口参数与返回值一律使用 `protocol/` 定义的类型。

## 读取目录（允许读）
- protocol/
- tooling/configs/

## 禁止修改目录
- aegisos_agents/ 内部实现（perception/planning/action/memory/tools）
- frontend/
- backend/
- protocol/ 类型定义

## 输出
- aegisos_agents/api/__init__.py 公共 Protocol 接口
- AgentRegistryAPI / MemoryAPI / PlanningAPI / ExecutionAPI / PerceptionAPI / EventBusAPI / RuntimeAPI

## 依赖
- protocol/ 契约（所有接口参数/返回值类型）
- tooling/configs/ 配置

## 接口
其他模块 `from aegisos_agents.api import MemoryAPI` 等接口；实现由 aegisos_agents/ 内部注入。

## 暴露的接口清单
AgentRegistryAPI(注册/调用/列出) · MemoryAPI(read/write/retrieve) · PlanningAPI(plan/route/schedule) · ExecutionAPI(execute/register_tool) · PerceptionAPI(reason/reflect/open_context) · EventBusAPI(publish/subscribe) · RuntimeAPI(run/heartbeat)

## 测试方式
`pytest tests/aegisos_agents/api/`，验证接口契约与 mock 兼容性，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/api/`（结构化 JSON 日志，按 session/task 切分）。

## 配置位置
`tooling/configs/agents_api.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 接口参数/返回值必须复用 `protocol/` 类型，禁止自造并行结构。
- 接口签名变更属于**破坏性变更**，需在 `developer/CHANGELOG.md` 标注并通知所有依赖方。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）
