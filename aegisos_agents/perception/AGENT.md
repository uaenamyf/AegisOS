# Agents/Perception 感知层 — AGENT.md

> 本文件是 `aegisos_agents/perception/` 分类的开发规范，隶属 `aegisos_agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·感知（Perception）：接收、理解输入与评估结果

## 职责
感知与认知：上下文管理、推理、反思。负责接收任务输入、理解语义、评估执行结果质量，为规划层提供决策依据。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/
- aegisos_agents/tools/llms/
- aegisos_agents/tools/prompts/
- tooling/configs/

## 禁止修改目录
- frontend/
- aegisos_agents/planning/
- protocol/ 类型定义

## 输出
- aegisos_agents/perception/context/ 上下文管理
- aegisos_agents/perception/reasoning/ 推理
- aegisos_agents/perception/reflection/ 反思

## 依赖
- protocol/ Task/Session
- aegisos_agents/memory/ 检索
- aegisos_agents/tools/llms/ 模型

## 接口
perceive(input) -> Understanding；产出可追溯推理与反思。

## 测试方式
`pytest tests/aegisos_agents/perception/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/perception/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/perception/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/perception.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块

| 子模块 | 状态 | 职责 |
|--------|:----:|------|
| `context/` | ✅ P2 | 上下文窗口管理：TokenBudget + ContextManager |
| `reasoning/` | ✅ | 推理策略：plan_mode / react_mode / goal_mode / neuro_symbolic |
| `reflection/` | ✅ P2 | 运行时反思：ExecutionCritic + OutputScorer + FeedbackLoop |

### context/ — 上下文窗口管理（✅ P2）
- `window.py` — TokenBudget：token 估算（字符/4）+ 智能裁剪（决策优先+头尾保留+digest）
- `manager.py` — ContextManager：会话上下文生命周期（open/close/pack/switch/isolate）
- 纯算法实现，不调 LLM。

### reflection/ — 运行时反思（✅ P2）
- `critic.py` — ExecutionCritic：四维批判检查（完整性/合理性/一致性/空结果）
- `scoring.py` — OutputScorer：四维量化评分（completeness/correctness/efficiency/safety）
- `feedback.py` — FeedbackLoop：整合批判+评分 → FeedbackRecord → 写回 memory/reflection
- 纯算法实现，不调 LLM。

---

### 🔧 SDK 集成状态

> 2026-07-06 全量排查。🔲 **neuro_symbolic.py 是 SDK 重构 P0 优先项**。

| 文件 | 当前实现 | SDK 重构方案 | 优先级 |
|------|---------|-------------|--------|
| `reasoning/neuro_symbolic.py` | 旧 `ModelProvider.complete()` + `json.loads` + `try/except` 手写解析 | 迁移到 `StructuredAgent[ExploitPlannerResult]`，用 SDK `output_type` 替代手写解析；`validate_chain` 符号侧保留 | **P0** |
| `context/` | 未实现 | 无 LLM 调用，不需要 SDK | — |
| `reflection/` | 未实现 | 无 LLM 调用，不需要 SDK | — |

> 这是 `aegisos_agents/` 中**唯一**仍用旧 `ModelProvider.complete()` + `json.loads` 的 LLM 调用点。
> 详见 `aegisos_agents/AGENT.md`「openai-agents SDK 集成状态」段 + `developer/plan.md`。
