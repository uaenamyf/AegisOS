# Agents/LLMs 模型调用 — AGENT.md

> 本文件是 `agents/tools/llms/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
LLM 提供方适配与路由：统一调用接口、成本/延迟路由、限流与回退。为智能体提供模型调用能力。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- agents/tools/prompts/
- developer/

## 禁止修改目录
- frontend/
- agents/planning/engine/ 路由实现
- protocol/ 类型定义

## 输出
- agents/tools/llms/providers/
- agents/tools/llms/adapters/
- agents/tools/llms/router/

## 依赖
- protocol/ Task/Payload
- tooling/configs/ 模型配置

## 接口
complete(prompt) -> Response；统一适配多 provider。

## 测试方式
`pytest tests/agents/tools/llms/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/tools/llms/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/llms/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/llms.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。
