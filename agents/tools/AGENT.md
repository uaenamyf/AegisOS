# Agents/Tools 工具层 — AGENT.md

> 本文件是 `agents/tools/` 分类的开发规范，隶属 `agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·工具（Tools）：能力支撑

## 职责
能力支撑：模型调用、提示词模板、运行时托管。为感知/规划/行动层提供底层能力。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- agents/planning/ 编排逻辑
- protocol/ 类型定义

## 输出
- agents/tools/llms/ 模型调用
- agents/tools/prompts/ 提示词
- agents/tools/runtime/ 运行时

## 依赖
- protocol/ Task/Payload
- tooling/configs/ 模型/Prompt 配置

## 接口
complete(prompt) -> Response；render(template,vars) -> prompt；run(agent,task) -> Result。

## 测试方式
`pytest tests/agents/tools/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/tools/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/tools/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/tools.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：agents/api/ — from agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块
- agents/tools/llms/ — LLM 提供方适配与路由（统一调用接口、成本/延迟路由）
- agents/tools/prompts/ — Prompt 模板库与版本管理（含 roles/ 各角色模板）
- agents/tools/runtime/ — Agent 运行时与生命周期管理（上下文注入、心跳、挂起/恢复）
