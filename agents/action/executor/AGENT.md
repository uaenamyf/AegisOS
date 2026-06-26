# Agent: Executor — AGENT.md

> 本文件是 `agents/action/executor/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
执行 Agent：在沙箱中实际执行任务/工具，采集结果与副作用。

## 读取目录（允许读）
- protocol/
- agents/action/execution/tools/
- agents/action/execution/executor/
- agents/tools/runtime/
- agents/tools/prompts/roles/executor/
- tooling/configs/agents/executor.yaml

## 禁止修改目录
- frontend/
- agents/planning/engine/
- protocol/ 类型定义

## 输出
- ExecutionResult
- ToolFinish 事件

## 依赖
- agents/action/execution/tools/ 工具
- agents/tools/runtime/ 环境
- protocol/ ToolCall

## 接口
receive(task) -> tool() -> ExecutionResult

## 测试方式
`pytest tests/agents/action/executor/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/action/executor/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/roles/executor/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/agents/executor.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。

## Agent 统一生命周期
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result -> Log -> Heartbeat -> Finish

## Agent 统一接口
- `receive(task)` 接收任务并校验
- `think()` 推理与计划
- `tool()` 调用工具执行
- `reflect()` 反思与自评
- `respond()` 返回结构化结果
