# Execution/Tools 工具 — AGENT.md

> 本文件是 `agents/action/execution/tools/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
工具注册、包装与规格：统一工具协议、权限、沙箱、规格校验。

## 读取目录（允许读）
- protocol/
- agents/action/execution/executor/
- tooling/configs/
- developer/TOOL_SPEC.md

## 禁止修改目录
- frontend/
- agents/planning/engine/
- protocol/ 类型定义

## 输出
- agents/action/execution/tools/builtin/
- agents/action/execution/tools/registry/
- agents/action/execution/tools/wrappers/
- agents/action/execution/tools/specs/

## 依赖
- agents/action/execution/executor/ 执行
- protocol/ ToolCall/ToolResult

## 接口
register/call(tool) -> ToolResult；详见 developer/TOOL_SPEC.md。

## 测试方式
`pytest tests/agents/action/execution/tools/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/action/execution/tools/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/tools/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/tools.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
