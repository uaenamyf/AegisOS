# Agents/LLMs 模型调用 — AGENT.md

> 本文件是 `aegisos_agents/tools/llms/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
LLM 提供方适配与路由：统一调用接口、成本/延迟路由、限流与回退。为智能体提供模型调用能力。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- aegisos_agents/tools/prompts/
- developer/

## 禁止修改目录
- frontend/
- aegisos_agents/planning/engine/ 路由实现
- protocol/ 类型定义

## 输出
- aegisos_agents/tools/llms/providers/
- aegisos_agents/tools/llms/adapters/
- aegisos_agents/tools/llms/router/

## 依赖
- protocol/ Task/Payload
- tooling/configs/ 模型配置

## 接口
complete(prompt) -> Response；统一适配多 provider。

## 测试方式
`pytest tests/aegisos_agents/tools/llms/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/tools/llms/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/llms/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/llms.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

---

### 🔧 SDK 集成状态

> 2026-07-06 全量排查。✅ **SDK Provider + MockSDKModel 已就位**。

| 文件 | 用途 | 状态 |
|------|------|------|
| `sdk_provider.py` | `SDKProvider` 仅提供 `get_sdk_model()` 返回 SDK `OpenAIChatCompletionsModel`；`create_provider()` 工厂支持 Mock/真实 API 切换。R6 删除旧 `complete()` 死代码 | ✅ |
| `mock_sdk_model.py` | `MockSDKModel(Model)` 适配 `MockProvider` -> SDK `ModelResponse`，测试无需真实 API | ✅ |
| `base.py` | `LLMRequest`/`LLMResponse`（Mock 内部数据契约，保留） | ✅ |
| `mock_provider.py` | 测试用预设响应 | ✅ 保留 |

> R5 已删除 `model_router.py`（无业务引用）与 `ModelProvider` Protocol（SDK 有自己的 `ModelProvider`）。R6 删除 `sdk_provider.complete()` 死代码 + 未使用 import。

> 详见 `aegisos_agents/AGENT.md`「openai-agents SDK 集成状态」段 + `developer/plan.md`。
