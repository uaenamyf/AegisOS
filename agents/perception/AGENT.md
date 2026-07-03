# Agents/Perception 感知层 — AGENT.md

> 本文件是 `agents/perception/` 分类的开发规范，隶属 `agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·感知（Perception）：接收、理解输入与评估结果

## 职责
感知与认知：上下文管理、推理、反思。负责接收任务输入、理解语义、评估执行结果质量，为规划层提供决策依据。

## 读取目录（允许读）
- protocol/
- agents/memory/
- agents/tools/llms/
- agents/tools/prompts/
- tooling/configs/

## 禁止修改目录
- frontend/
- agents/planning/
- protocol/ 类型定义

## 输出
- agents/perception/context/ 上下文管理
- agents/perception/reasoning/ 推理
- agents/perception/reflection/ 反思

## 依赖
- protocol/ Task/Session
- agents/memory/ 检索
- agents/tools/llms/ 模型

## 接口
perceive(input) -> Understanding；产出可追溯推理与反思。

## 测试方式
`pytest tests/agents/perception/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/perception/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/perception/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/perception.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 下辖子模块
- agents/perception/context/ — 上下文窗口与会话管理（Token 预算、裁剪、隔离）
- agents/perception/reasoning/ — 推理链/树与策略（CoT/ToT/ReAct）
- agents/perception/reflection/ — 反思、批判与反馈评分（区别于 agents/memory/reflection/ 反思记忆存储）
