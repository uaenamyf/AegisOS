# Protocol 契约层 — AGENT.md

> 本文件是 `protocol/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
全系统通信协议的定义与序列化：Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync。系统唯一数据契约。

## 读取目录（允许读）
- developer/specs/04_PROTOCOL_SPEC.md
- developer/specs/07_EVENT_SPEC.md
- tooling/configs/

## 禁止修改目录
- frontend/
- backend/
- agents/
- agents/planning/engine/ 业务逻辑

## 输出
- protocol/*.py 数据类
- 序列化/反序列化
- schema 校验

## 依赖
- tooling/configs/

## 接口
Message 信封 + 强类型 Payload；详见 developer/specs/04_PROTOCOL_SPEC.md。

## 测试方式
`pytest tests/protocol/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/protocol/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/protocol/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/protocol.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/04_PROTOCOL_SPEC.md + 06_SCHEMA_SPEC.md
- **数据契约**：本层即契约（无 api/，被各域复用）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（A1 cyber 类型）
