# CLAUDE.md — AegisOS 工程总览（渐进式披露）

> 本文件给 Claude Code 提供全工程导航。**渐进式披露**：从上往下读，按需点进链接的 SSOT 文档（`AGENT.md` / `developer/specs/` / `roadmap/` / `plans/` / `.claude/skills/`），不要一次性把全部细节塞进上下文。
>
> 位置：`.claude/CLAUDE.md`。⚠️ `.claude/` 已被 `.gitignore` 忽略——此文件不会被提交/共享。若需**每会话自动加载 + 团队共享**，应放在仓库根 `CLAUDE.md`（Claude Code 默认自动加载根 `CLAUDE.md` 与 `~/.claude/CLAUDE.md`）。如需我可同步复制到根。

---

## L0 · 30 秒上手（必读最小集）

**项目**：AegisOS = Agent Operating System + AI Native IDE；赛事作品为「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」（荣耀 XH-202631，截止 2026-09-15）。

**第一步**：读 `AGENT.md`（根，仓库最高规范）→ `developer/plan.md`（动态待办计划）→ `developer/specs/00_PROJECT_SPEC.md`（SSOT）→ `developer/roadmap/README.md`（当前阶段 P0..P7）→ 目标模块 `AGENT.md`。

**最易违反的铁律**：
- 跨域调用仅经 `api/`：`from {domain}.api import ...`，禁直接 import 内部子包。
- 数据契约只用 `protocol/` 类型，禁自造并行结构；跨模块通信走 `protocol/message.py` Message 信封，禁裸 dict/JSON。
- AI 改动 ≤1 域 / ≤8 文件 / 行为保持 / 含测试；首次创建文件写文件说明 + date + dev（§10.1），增改函数/方法/接口写 date + dev + changelog + 代码注释（§10.2）。
- router 禁低熵全广播（仅 Top-K 稀疏路由）；攻防工具仅 Docker 沙箱靶场内运行，永不触真实网络。

**在哪找**：规范 → `developer/specs/` · 契约 → `protocol/` · 接口 → 各域 `api/` · **动态计划 → `developer/plan.md`（当前待办）** · 阶段 → `developer/roadmap/` · skills → `.claude/skills/` · **模块实现文档 → 各域 `AGENT.md` 末尾「📋 模块实现详解」 + 根 `AGENT.md` 末尾「📋 模块实现总览」· 架构仪表盘 → `docs/ARCHITECTURE.md`**。

---

## L1 · 项目与分层

### 定位
面向「挑战杯揭榜挂帅 + 荣耀群体智能赛题」的 AOS + AI Native IDE。核心特性：动态异构群体智能、长期记忆、低熵通信、端边云协同、可运行系统。整个项目可由 Agent 自主开发（Spec First：P0 规范未完成前不得写业务代码）。

### 8 域分层（同域聚合 + 域内分类）
| 域 | 职责 | AGENT.md | api/ |
|----|------|----------|------|
| `developer/` | 规范层（项目大脑）：specs SSOT + roadmap | `developer/AGENT.md` | — |
| `protocol/` | 契约层，唯一数据契约 | `protocol/AGENT.md` | — |
| `aegisos_agents/` | 智能体域：感知-规划-行动-记忆-工具五层 | `aegisos_agents/AGENT.md` | `aegisos_agents/api/` |
| `backend/` | 应用层：Router-Service-Repository-Model + Core | `backend/AGENT.md` | `backend/api.py` |
| `frontend/` | 表现层：Controller-Service-Lib + Views | `frontend/AGENT.md` | — |
| `infrastructure/` | 基建：transport / nodes(端·云) / delivery | `infrastructure/AGENT.md` | `infrastructure/api/` |
| `observability/` | 可观测：inspect / measure / present | `observability/AGENT.md` | `observability/api/` |
| `data/` | 数据：datasets / models（Neo4j · Qdrant 接入） | `data/AGENT.md` | `data/api/` |
| `tooling/` | 工程支撑：configs / scripts | `tooling/AGENT.md` | `tooling/api/` |
| `docs/` · `tests/` | 文档资产 · 测试 | `docs·tests/AGENT.md` | — |

> 每个目录/子模块都有独立 `AGENT.md`（共 78 个）规定职责/读取目录/禁止修改目录/接口/测试/配置。**改某模块前先读其 `AGENT.md` 的「禁止修改目录」+「交叉引用（去哪里找）」段，不得越界。**

### AI 开发工作流
读 `AGENT.md` → `specs`(00/03/11) → `roadmap` 定位阶段 → 目标模块 `AGENT.md` → `protocol` 契约 + `04` → 目标域 `api` + `05` → 配置 → 生成代码 → 质量门禁（`ruff format && ruff check --fix && mypy && pytest`，本机无 Python 见下）→ 更新 Doc + `CHANGELOG` → Commit。**永不全仓扫描。**

### 全局铁律（精简）
模块解耦(`api/`) · `protocol` 唯一契约 · Message 信封 · 不得越界 · API 签名变更=破坏性 · 质量门禁 · 低熵稀疏通信 · 技术栈登记制 · AI 范围/代码注释强制。详见根 `AGENT.md`「全局铁律」+ `developer/specs/03_IMPORT_SPEC.md` / `04` / `11`。

---

## L2 · 模块地图（去哪改什么）

> 改某模块前：读对应 `AGENT.md` → 看其「交叉引用（去哪里找）」段定位相关规范/上下游/API/契约/计划。

| 域 | 主要职责 | 主要规范 | 关键计划 | 接口边界 |
|----|---------|---------|---------|---------|
| `aegisos_agents/perception` | context / reasoning / reflection | 08 | 14/15 | `aegisos_agents/api` |
| `aegisos_agents/planning` | planner / orchestrator / engine(planner·scheduler·router·workflow·eventbus·topology) | 03·08·04(§16 低熵) | 14/15 | `aegisos_agents/api` |
| `aegisos_agents/action` | coder·executor·tester·debugger·critic·reviewer·researcher·docwriter + execution(沙箱) | 08·11 | 14/15(红蓝紫 E1-E11) | `aegisos_agents/api` |
| `aegisos_agents/memory` | 12 子模块（working/episodic/semantic/vector/compression/recall/...） | 08·06 | 14/15(B1-B3 压缩/唤醒) | `aegisos_agents/api` |
| `aegisos_agents/tools` | llms(多模型兼容) · prompts · runtime | 12·08 | 14/15(D2 多模型) | `aegisos_agents/api` |
| `aegisos_agents/api` | 公共接口层：RuntimeAPI / AgentRegistry / Memory / Planning / Execution / Perception / EventBus | 05·10 | 13(双向调用/DI 端口) | — |
| `protocol` | message/event/scheduler/tool/memory/agent/graph/heartbeat/sync + `cyber.py`（8 攻防类型 ✅） | 04·06 | 14/15(A1 cyber 类型) | — |
| `backend` | routers/services/repositories/models + core/schemas/mocks | 05·10·12 | 13·14/15(F 攻防端点) | `backend/api.py` |
| `frontend` | src/(controllers / services / mappers / views(chat·canvas·graph·monitor·replay)) | 13·05·12 | 13·14/15(G 攻防视图) | — |
| `infrastructure` | transport / nodes(edge·cloud) / delivery(deployment) | 01·12 | 14/15(H1 沙箱靶场·端边云) | `infrastructure/api` |
| `observability` | inspect(monitor·replay) / measure(benchmark·evaluation) / present(visualization) | 01·07 | 14/15(H5 评测·回放) | `observability/api` |
| `data` | datasets / models（Neo4j 拓扑+ATT&CK 图 · Qdrant 向量） | 06 | 14/15(H2) | `data/api` |
| `tooling` | configs / scripts（gen_readme · gen_ts_types · 靶场编排） | 09 | 14/15 | `tooling/api` |

---

## L3 · 深指针

### 规范体系（`developer/specs/`，唯一真相源）
| 编号 | 文件 | 内容 |
|------|------|------|
| 00 | `00_PROJECT_SPEC.md` | 项目 SSOT：目标/边界/原则/分层/生命周期/commit/review |
| 01 | `01_ARCHITECTURE_SPEC.md` | 系统架构：分层/微内核/DDD/事件驱动/各 Runtime |
| 02 | `02_DIRECTORY_SPEC.md` | 目录规范：每目录职责/边界/可改性 |
| 03 | `03_IMPORT_SPEC.md` | Import 规范：依赖矩阵/禁循环（AI 最重要） |
| 04 | `04_PROTOCOL_SPEC.md` | 通信协议：Message/Event/Task/Graph/低熵稀疏§16 |
| 05 | `05_API_SPEC.md` | API 契约：27 接口 × Request/Response/Error/Timeout/Retry/Version |
| 06 | `06_SCHEMA_SPEC.md` | 数据 Schema（现 dataclass，§12 向 Pydantic 迁移） |
| 07 | `07_EVENT_SPEC.md` | 事件总线：8 事件/生命周期/可靠性/追踪 |
| 08 | `08_AGENT_SPEC.md` | Agent Runtime：生命周期/API/Prompt/Memory/Tool |
| 09 | `09_DEVELOPMENT_SPEC.md` | 开发流程：Spec→Contract→API→Impl→Test→Doc |
| 10 | `10_INTERFACE_BOUNDARY_SPEC.md` | 接口边界：并行开发核心（谁调谁/异步/网关/EventBus） |
| 11 | `11_AI_CODING_SPEC.md` | AI 编码规范：必读/范围/禁改协议 API/测试/代码注释 §10 |
| 12 | `12_TECH_STACK_SPEC.md` | 技术栈：语言/运行时/框架/库/工具链/版本约束 |
| 13 | `plans/13_FRONTEND_BACKEND_PLAN.md` | 前后端全流程计划（双向调用/DI 端口/FastAPI） |
| 14 | `plans/14_CYBERDEFENSE_SOLUTION_PLAN.md` | 赛事总体方案（架构/角色/算法/3 场景/评分对齐） |
| 15 | `plans/15_CYBERDEFENSE_TASKS.md` | 实施任务清单（Phase A-H，核心算法 TDD） |

> 冲突优先级：`00` > `04` ≈ `05` ≈ `06` > 其余编号 > 各模块 `AGENT.md`。必读顺序见根 `AGENT.md`。

### roadmap（`developer/roadmap/`，P0..P7）
`P0 初始化(✅) → P1 Protocol → P2 Memory → P3 Router → P4 Scheduler → P5 Planner+Agents → P6 Frontend → P7 Deployment`。当前 **P0-P5 ✅ 完成**（94 测试通过），**P6 部分完成**（ChatView ✅，攻防视图 🔲），P7 未开始；**openai-agents SDK 集成 S1-S4 ✅ 完成**（11 个攻防 Agent + SDKProvider + CyberOrchestrator），R4-R5 SDK 深化进行中。各阶段→攻防扩展映射见 `roadmap/README.md`「赛事作品对齐」。

### skills（`.claude/skills/`，按需启用）
- **superpowers（14）**：`writing-plans` · `executing-plans` · `subagent-driven-development` · `dispatching-parallel-agents` · `brainstorming` · `test-driven-development` · `systematic-debugging` · `verification-before-completion` · `requesting-code-review` · `receiving-code-review` · `using-git-worktrees` · `finishing-a-development-branch` · `using-superpowers` · `writing-skills`。
- **codex（3）**：`codex-cli-runtime` · `codex-result-handling` · `gpt-5-4-prompting`。
- **独立（5）**：`frontend-design` · `mcp-builder` · `skill-creator` · `web-artifacts-builder` · `webapp-testing`。
- 赛事执行推荐：`subagent-driven-development`（按 Phase 派发）+ `writing-plans`（已用于 `plans/15`）。

### 计划（`developer/specs/plans/`）
`13` 前后端全流程 · `14` 赛事总体方案 · `15` 实施任务清单。Phase A-E + B3 + E13 + SDK S1-S4 已完成（94 测试通过）；下一步：R4 SDK 编排深化（handoffs/guardrails/tracing）+ R5 旧接口清理 + F/G 攻防端点视图。
> **动态开发计划**：`developer/plan.md` — 当前未完成任务清单 + 下一步计划，每次会话必读、每次完成任务后更新勾选。

---

## 本机环境约束
- **Python 环境**：macOS 上有 `.venv/`（Python 3.12.13 + greenlet 3.5.3），可运行 `pytest`/`ruff`/`mypy`/`uvicorn` 全链路。Windows 环境仅有 node + perl（Python 域代码须在 macOS/容器内开发）。详见 memory `aegisos-windows-no-python`。
- **赛事**：XH-202631，截止 2026-09-15；详见 memory `aegisos-cyberdefense-competition` 与 `plans/14` · `15`。
- **protocol 现状**：`protocol/*.py` 为 `@dataclass`（非 Pydantic，`06 §12` 列迁移待办）；id 字段约定 `*_id`；`Graph.nodes` 为 dict；`NodeKind.Agent` 驼峰。
- **openai-agents SDK 集成**：S1-S4 ✅ 完成（`StructuredAgent[T]` 基类 + 11 个攻防 Agent + `SDKProvider`/`MockSDKModel` + `CyberOrchestrator`）；R4-R5 🔲 待深化（handoffs/guardrails/tracing + 旧接口清理）；`neuro_symbolic.py` 是唯一未迁移的 LLM 调用点（P0）。详见 `aegisos_agents/AGENT.md`「🔧 openai-agents SDK 集成状态」段 + `developer/plan.md`。

---

## 维护
- 本文件**指针式**，不复制 SSOT 全文；SSOT 变动后核对此处链接。
- 模块结构 / api 变动后：更新对应 `AGENT.md`「交叉引用」段 + 根 `README.md`（`python3 tooling/scripts/gen_readme.py` 刷新自动段，本机无 Python 时手动同步）。
- 代码实现变动后：更新对应 `AGENT.md` 末尾「📋 模块实现详解」段（根 `AGENT.md` 末尾「📋 模块实现总览」段）+ `docs/ARCHITECTURE.md` 仪表盘。
