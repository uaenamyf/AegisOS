# Agent: Researcher — AGENT.md

> 本文件是 `agents/action/researcher/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
调研检索 Agent：检索知识/文档/记忆，聚合证据供其他 Agent 决策。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/action/execution/tools/
- agents/tools/prompts/roles/researcher/
- tooling/configs/agents/researcher.yaml

## 禁止修改目录
- frontend/
- agents/planning/engine/
- protocol/ 类型定义

## 输出
- Evidence 证据集
- MemoryUpdate 写入语义记忆

## 依赖
- agents/memory/ retrieval
- agents/action/execution/tools/ 检索工具
- protocol/ Task

## 接口
receive(query) -> think() -> tool() -> Evidence

## 测试方式
`pytest tests/agents/action/researcher/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/action/researcher/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/roles/researcher/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/agents/researcher.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## Agent 统一生命周期
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result -> Log -> Heartbeat -> Finish

## Agent 统一接口
- `receive(task)` 接收任务并校验
- `think()` 推理与计划
- `tool()` 调用工具执行
- `reflect()` 反思与自评
- `respond()` 返回结构化结果
