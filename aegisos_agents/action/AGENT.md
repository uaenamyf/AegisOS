# Agents/Action 行动层 — AGENT.md

> 本文件是 `aegisos_agents/action/` 分类的开发规范，隶属 `aegisos_agents/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
认知架构·行动（Action）：执行与产出

## 职责
执行与产出：代码生成、测试、调试、评审、调研、文档、沙箱执行。各角色 Agent 在此层实际执行任务并产出结果。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/
- aegisos_agents/tools/
- aegisos_agents/planning/
- tooling/configs/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- aegisos_agents/planning/ 编排逻辑

## 输出
- aegisos_agents/action/{recon,vuln_correlator,exploit_planner,lateral_move}/ 红队 Agent
- aegisos_agents/action/{detector,triage,threat_hunt,ir_planner,forensics}/ 蓝队 Agent
- aegisos_agents/action/{critic,reviewer}/ 紫队 Agent
- aegisos_agents/action/execution/ 执行能力

## 依赖
- aegisos_agents/tools/ 工具与模型
- aegisos_agents/memory/ 上下文
- protocol/ ToolCall

## 接口
receive(task) -> think() -> tool() -> respond() -> Result。

## 测试方式
`pytest tests/aegisos_agents/action/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/action/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/action/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/action.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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
- aegisos_agents/action/structured_agent.py — `StructuredAgent[T]` 泛型基类，包装 SDK `Agent` + `Runner.run_sync` + `output_type`
- aegisos_agents/action/output_types.py — 11 个 Pydantic BaseModel 作为 SDK `output_type`
- aegisos_agents/action/react_support.py — AP2.2-AP2.6 ReAct 共享适配器，组装默认工具调用并支持自定义 thinker
- aegisos_agents/action/recon/ — 红队侦察 Agent（StructuredAgent[ReconResult]）
- aegisos_agents/action/vuln_correlator/ — 红队漏洞关联 Agent（StructuredAgent[VulnCorrelatorResult]）
- aegisos_agents/action/exploit_planner/ — 红队利用规划 Agent（StructuredAgent[ExploitPlannerResult]）
- aegisos_agents/action/lateral_move/ — 红队横向移动 Agent（StructuredAgent[LateralMoveResult]）
- aegisos_agents/action/detector/ — 蓝队检测 Agent（StructuredAgent[DetectorResult]）
- aegisos_agents/action/triage/ — 蓝队分诊 Agent（StructuredAgent[TriageResult]）
- aegisos_agents/action/threat_hunt/ — 蓝队威胁狩猎 Agent（StructuredAgent[ThreatHuntResult]）
- aegisos_agents/action/ir_planner/ — 蓝队应急响应规划 Agent（StructuredAgent[IRPlannerResult]）
- aegisos_agents/action/forensics/ — 蓝队取证 Agent（StructuredAgent[ForensicsResult]）
- aegisos_agents/action/critic/ — 紫队批判 Agent（StructuredAgent[CritiqueResult]，双 Agent 红/蓝）
- aegisos_agents/action/reviewer/ — 紫队审查 Agent（StructuredAgent[ReviewResult]）
- aegisos_agents/action/execution/ — 执行能力：executor(沙箱执行器) + tools(工具注册)

> ⚠️ 原始 `coder/` `executor/` `tester/` `debugger/` `researcher/` `docwriter/` 仅有 AGENT.md 骨架，赛事版攻防 Agent 已替代上述通用角色。

---

### 🔧 SDK 集成状态

> 2026-07-06 全量排查。✅ **11 个攻防 Agent 已全部迁移到 openai-agents SDK**。

- **基类**：`StructuredAgent[T]`（Generic）封装 SDK `Agent` + `Runner.run_sync` + `output_type`
- **输出类型**：`output_types.py` 定义 11 个 Pydantic BaseModel
- **模型适配**：`tools/llms/sdk_provider.py` → `OpenAIChatCompletionsModel`（真实 API）/ `tools/llms/mock_sdk_model.py` → `MockSDKModel`（测试）
- **无 `json.loads`**：所有 Agent 通过 SDK `output_type` 获得结构化输出，无需手写 JSON 解析

详见 `aegisos_agents/AGENT.md`「openai-agents SDK 集成状态」段 + `developer/plan.md`。

---

### 🔁 ReAct 接入状态（AP2.2-AP2.6）

| Agent | ReAct 方法 | 默认工具 | 领域输出 |
|-------|------------|----------|----------|
| `recon` | `scan_react()` | `nmap_scan` | `list[Asset]` |
| `vuln_correlator` | `correlate_react()` | `query_cve_db` | `list[VulnFinding]` |
| `detector` | `detect_react()` | `correlate_alerts` | `list[Alert]` |
| `threat_hunt` | `hunt_react()` | `query_attck_kb` | `list[dict]` |
| `forensics` | `investigate_react()` | `collect_forensic_evidence` | `dict` |

五个方法均保留原同步接口，新增路径统一返回 `ReactResult`。工具必须经调用方注入的
`ExecutionAPI` 执行；默认工具失败立即停止，观察数据会标记为不可信 JSON 后再交给
结构化模型归纳。调用方可注入自定义 thinker 并关闭快速失败，以实现多工具重试或
备选路径。生产环境的危险工具执行仍须由 H1 Docker 沙箱提供隔离。

**测试**：11 个 ReAct Agent 用例；`tests/aegisos_agents/action/` 共 30 个测试通过，
其中 `react_support.py` 覆盖率为 100%。
