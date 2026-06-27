# 00_PROJECT_SPEC.md — AegisOS 项目规范（Single Source of Truth）

> **最高优先级文件**。本文件是整个 AegisOS 仓库**唯一的项目级真相源（SSOT）**。
> 一切架构、目录、协议、接口、Schema、事件、Agent、开发流程、接口边界、AI 编码规范，均以本文件为根，并以下游编号规范（`01`–`11`）为展开。
> 本目录 `developer/specs/` 下的编号规范 **取代** `developer/` 根下旧版散落文档（`API_SPEC.md` / `MESSAGE_PROTOCOL.md` / `EVENT_SPEC.md` / `ARCHITECTURE.md` / `CODING_RULES.md` / `DIRECTORY_GUIDE.md` 等）作为权威；旧文档保留作历史参考，冲突时以本目录为准。
>
> 适用对象：人类开发者与所有 AI Coding Agent（Cursor / Claude Code / Codex / GPT 等）。

---

## 1. 项目目标（Goal）

| # | 目标 | 验收含义 |
|---|------|----------|
| G1 | **动态异构群体智能**（Dynamic Heterogeneous Topology） | 拓扑随任务/能力/信任度自适应重构（`agents/planning/engine/topology/`） |
| G2 | **长期记忆**（Long-term Memory，含知识库） | 12 子模块记忆可读写、压缩、检索、跨会话沉淀（`agents/memory/`） |
| G3 | **低熵通信**（Low Entropy Communication） | 按需链式稀疏路由，禁止全广播（`agents/planning/engine/router/`） |
| G4 | **端边云协同**（Edge-Cloud Collaboration） | 离线优先，向量时钟按需同步（`infrastructure/nodes/`、`protocol/sync.py`） |
| G5 | **可运行系统**（Runnable System） | 开箱可 `make setup/test/build/deploy`，可部署 |
| G6 | **AI 可自主开发**（Developer Operating System） | 全仓库 `AGENT.md` + 本规范体系，Agent 按边界精准读写、自主开发 |

**赛事对齐**：挑战杯揭榜挂帅 + 荣耀群体智能赛题。AegisOS = **Agent Operating System (AOS) + AI Native IDE**，不仅包含 Agent，而是让整个项目可由 Agent 自主开发与运行。

---

## 2. 非目标（Non Goal）

| # | 非目标 | 理由 |
|---|--------|------|
| NG1 | 不做通用操作系统内核 | AegisOS 的「OS」指 Agent 协同操作系统，非 Linux 内核替代 |
| NG2 | 不做单体大模型训练 | 复用外部 LLM（`agents/tools/llms/`），不自训练基座模型 |
| NG3 | 不做无边界全广播通信 | 与 G3 低熵原则冲突 |
| NG4 | 不做无规范自由扫描式 AI 开发 | 与 G6 边界式开发冲突 |
| NG5 | 不承诺跨大版本（≥v2）零破坏兼容 | 仅保证同一 major 内向后兼容（见 §11） |
| NG6 | 不在 protocol/ 之外定义并行数据契约 | 破坏唯一契约原则 |

---

## 3. 系统边界（System Boundary）

```
┌─────────────────────── 外部 ───────────────────────┐
│  用户（前端交互） · 外部 LLM API · 外部数据源 · 边缘节点 │
└────────────────────────┬───────────────────────────┘
                         │ 唯一入口/出口
┌────────────────────────▼───────────────────────────┐
│  backend/gateway/  ← 所有外部请求唯一入口（鉴权+限流）  │
├────────────────────────────────────────────────────┤
│  系统内部（AegisOS）                                  │
│   frontend · backend · agents · infrastructure      │
│   observability · data · tooling                    │
├────────────────────────────────────────────────────┤
│  protocol/  ← 所有跨模块数据的唯一契约（系统边界内）     │
└────────────────────────────────────────────────────┘
```

- **入站边界**：一切外部请求经 `backend/gateway/`；前端只调 `backend.api` 暴露的 REST/WS/SSE。
- **出站边界**：对外 LLM 调用集中在 `agents/tools/llms/`；对外部署集中在 `infrastructure/delivery/`。
- **数据边界**：跨模块数据结构 = `protocol/` 的 26 个契约类型；禁止裸 JSON 跨模块。
- **开发边界**：`developer/` 纵切所有层，是规范大脑，不参与运行时。

---

## 4. 核心设计原则（Design Principles）

1. **契约先行（Contract First）**：`protocol/` 是唯一数据契约；所有跨模块通信走 `protocol/message.py` 的 `Message` 信封。
2. **同域聚合 + 域内分类**：Agent 相关归 `agents/`（认知架构五层：感知-规划-行动-记忆-工具）；后端归 `backend/`（Controller-Service-Mapper + Gateway）；前端归 `frontend/`（Controller-Service-Mapper + Views）。
3. **API 解耦（Dependency Inversion）**：每个域通过 `api/` 子包暴露 `typing.Protocol` 接口；其他模块只 `from {domain}.api import XxxAPI`，禁止导入内部实现。实现由各域内部注入，便于 mock。
4. **模块边界（Boundary）**：每个模块的 `AGENT.md` 规定「读取目录 / 禁止修改目录」；Agent 不得越界。
5. **低熵稀疏通信（Low Entropy）**：路由按需链式（Agent→Planner→Memory→Coder→Reviewer→Executor），禁止全广播。
6. **长期记忆（Long-term Memory）**：多层记忆 + 压缩 + 反思，跨会话沉淀经验。
7. **动态异构拓扑（Dynamic Heterogeneous Topology）**：图随任务/能力/信任度自适应更新，发 `GraphUpdate` 事件。
8. **端边云协同（Edge-Cloud）**：离线优先，向量时钟按需同步（`protocol/sync.py`）。
9. **可观测可回放（Observable & Replayable）**：事件流驱动确定性回放（`observability/inspect/replay/`）。
10. **AI 可开发（AI-Developable）**：`developer/` + `AGENT.md` + 本规范体系让 Agent 按规范自主开发而不扫描全项目。
11. **幂等与可恢复（Idempotent & Recoverable）**：事件至少一次投递 + `event_id` 去重；任务可重试/回滚 + 检查点/快照。
12. **安全最小特权（Least Privilege）**：网关鉴权；工具沙箱执行；密钥走环境/`tooling/configs/`；日志脱敏。

---

## 5. 项目分层（Architecture Layers）

| 层 | 目录 | 角色 | 对外入口 |
|----|------|------|----------|
| 规范层 | `developer/`（含 `specs/`、`roadmap/`） | 项目大脑，纵切所有层，不参与运行时 | — |
| 契约层 | `protocol/` | 唯一数据契约（26 类型） | 本身即全局契约 |
| 表现层 | `frontend/` | Controller-Service-Mapper + Views | `frontend/api/`（3 接口） |
| 应用层 | `backend/` | Controller-Service-Mapper + Gateway | `backend/api/`（5 接口） |
| 智能体域 | `agents/` | 认知架构五层：感知-规划-行动-记忆-工具 | `agents/api/`（5 接口；规划/感知内聚不暴露） |
| 基础设施层 | `infrastructure/` | 传输-节点-交付 | `infrastructure/api/`（4 接口） |
| 可观测层 | `observability/` | 观测-度量-呈现 | `observability/api/`（6 接口） |
| 数据层 | `data/` | 数据集 + 模型 | `data/api/`（2 接口） |
| 工程支撑层 | `tooling/` | 配置 + 脚本 | `tooling/api/`（2 接口） |
| 文档资产层 | `docs/` | 文档与示例 | — |
| 测试层 | `tests/` | 单元/集成/E2E/基准 | — |

> 共 **11 个顶层域**，**27 个公共 API 接口**（见 `05_API_SPEC.md`）。

---

## 6. 模块职责（Domain Responsibility）

| 域 | 核心职责 | 关键产物 |
|----|----------|----------|
| `agents/perception/` | 感知：上下文管理、推理、反思评估 | context / reasoning / reflection |
| `agents/planning/` | 规划：planner、orchestrator、engine（planner·scheduler·router·workflow·eventbus·topology） | Plan(DAG)、Route、Schedule |
| `agents/action/` | 行动：8 角色（coder·executor·tester·debugger·critic·reviewer·researcher·docwriter）+ execution（沙箱+工具） | 执行结果、ToolResult |
| `agents/memory/` | 记忆：12 子模块（含 semantic 知识库） | MemoryPacket |
| `agents/tools/` | 工具：llms、prompts、runtime | LLM 调用、Prompt 模板、生命周期托管 |
| `backend/` | gateway→controllers→services→mappers | REST/WS/SSE 端点、会话/任务/记忆/图桥接 |
| `frontend/` | controllers→services→mappers→views | canvas/graph/monitor/replay 可视化 |
| `infrastructure/` | transport·nodes(edge·cloud)·delivery | 低熵通信、端边云同步、部署 |
| `observability/` | inspect(monitor·replay)·measure(benchmark·evaluation)·present(visualization) | 监控、回放、评估、可视化 |
| `data/` | datasets、models | 数据集、Schema 注册 |
| `tooling/` | configs、scripts | 配置、自动化脚本 |
| `protocol/` | 26 契约类型 | Message/Event/Task/Plan/Schedule/MemoryPacket/ToolCall/Graph/Agent/Heartbeat/Sync… |

---

## 7. 开发顺序（Development Order）

严格遵循自底向上、契约先行：

```
P0 Specification  （规范：本目录 12 份编号规范） ← 当前阶段产出
   ↓
P1 Contract       （契约：protocol/ 26 类型可序列化往返）
   ↓
P2 Protocol       （协议：Message 信封 + Event + 动态路由协议）
   ↓
P3 API            （接口：27 个 api/ Protocol 接口签名冻结）
   ↓
P4 Skeleton       （骨架：各域空实现 + DI 注入 + 配置 + Makefile）
   ↓
P5 Implementation （实现：Memory→Router→Scheduler→Planner+Agents）
   ↓
P6 Testing        （测试：协议往返、API 契约、端到端、基准、覆盖率≥80%）
   ↓
P7 Deployment     （部署：Docker/K8s/CI、端边云、开箱可部署）
```

> 与 `developer/roadmap/` 的 P0–P7 一致。**P0 规范未完成前，任何人/AI 不得编写业务代码。**

---

## 8. 模块依赖关系（Dependency Rules）

依赖方向**严格自上而下**，禁止逆向与跨层穿透：

```
frontend  →  backend  →  agents  →  protocol
                       ↘          ↗
   observability  →  infrastructure  →  protocol
   data / tooling  →  protocol
   所有域  →  protocol   （唯一被全局依赖的层）
```

铁律：
- `protocol/` **不依赖任何业务域**（零反向依赖），仅依赖标准库。
- 任何域只通过 `from {domain}.api import XxxAPI` 调用他域，**禁止**直接导入他域内部子包。
- `frontend` 不直接调用 `agents`/`infrastructure`，须经 `backend`。
- `developer/` 不被任何运行时代码依赖。
- 禁止循环依赖（详见 `03_IMPORT_SPEC.md`）。

---

## 9. 可扩展性原则（Extensibility）

- **新增 Agent**：在 `agents/action/{role}/` 新建模块 + `AGENT.md` + 在 `agents/api` 注册；不影响他域。
- **新增工具**：在 `agents/action/execution/tools/` 注册 `ToolSpec`；沙箱执行；无需改协议。
- **新增事件**：在 `protocol/event.py` 的 `EventType` 登记 + `07_EVENT_SPEC.md` 登记 + CHANGELOG。
- **新增 API**：在域 `api/` 增加 `Protocol` 方法（可选方法用默认实现/拆新接口，避免破坏既有实现）。
- **新增节点**：在 `infrastructure/nodes/{edge,cloud}/` 注册，发 `Heartbeat`。
- **插件化**：工具/LLM/记忆后端通过 DI 注入，接口稳定、实现可替换。

---

## 10. 稳定性原则（Stability）

- **稳定层**：`protocol/`、各域 `api/`（签名冻结，变更属破坏性）。
- **不稳定层**：各域 `api/` 之外的内部实现（可自由重构，只要 api 签名不变）。
- **关键路径**（scheduler/router/memory/eventbus/planner）测试覆盖率 ≥ 90%；整体 ≥ 80%。
- **容错**：Task `retry` + `rollback` + `agents/memory/checkpoint` + `snapshot` + 事件回放。
- **降级**：LLM 调用回退（`agents/tools/llms/`）；节点失联后离线优先 + 同步。
- **质量门禁**：`ruff format && ruff check --fix && mypy && pytest` 全绿方可提交。

---

## 11. 向后兼容原则（Backward Compatibility）

- 仅保证**同一 major 版本**内兼容。
- **字段新增**必须可选（带默认值）。
- **字段废弃**先标记 `deprecated` 一个 minor 版本，再移除。
- **`api/` 签名变更**属破坏性变更，须 bump major + CHANGELOG + 通知所有依赖方。
- **Message/Event 字段**向后兼容；接收方忽略未知字段（前向容忍）。
- **URL 版本** `/api/v1/`；新增版本并存 `/v2/`，旧版至少维护一个 minor 周期。

---

## 12. 生命周期（Lifecycles）

### 12.1 API 生命周期
`Draft → Proposed（写 API_SPEC）→ Frozen（签名冻结）→ Stable → Deprecated → Removed`
- Frozen 后签名变更 = 破坏性，须 bump major。

### 12.2 Protocol 生命周期
`Draft → Proposed（写 PROTOCOL_SPEC）→ Implemented（protocol/*.py）→ Stable → Deprecated → Removed`
- 现状：`protocol/` 26 类型为 v1，dataclass 实现；目标升级为 Pydantic（见 `06_SCHEMA_SPEC.md`）。

### 12.3 Event 生命周期
`Draft → Proposed（写 EVENT_SPEC 登记 EventType）→ Emitted（生产者实现）→ Consumed（消费者实现）→ Stable → Deprecated → Removed`
- 新增事件须在 `protocol/event.py` + `07_EVENT_SPEC.md` 双登记。

### 12.4 Memory 生命周期
`Write → Compress → Split(working/semantic/episodic/archive) → VectorIndex → Reflection → Cache → Sync → Evict`
- 幂等写入（packet id 去重）；checkpoint/snapshot 恢复（见 `08_AGENT_SPEC.md`）。

### 12.5 Agent 生命周期
```
Initialize → Load Config → Load Prompt → Load Skills → Receive Task
→ Reasoning → Memory Read → Tool Call → Reflection → Return Result
→ Log → Heartbeat → Finish
```
统一接口：`receive(task)` → `think()` → `tool()` → `reflect()` → `respond()`（见 `08_AGENT_SPEC.md`）。

### 12.6 Workflow 生命周期
`Created(goal) → Planned(DAG) → Routed → Scheduled → Running → Checkpointed → (Retry|Rollback) → Succeeded|Failed|Cancelled`
- DAG 工作流引擎：`agents/planning/engine/workflow/`。

### 12.7 Task 生命周期
`Pending → Running → (Retry→Running)* → Succeeded | Failed → (RolledBack) | Cancelled`
- 状态机由 `protocol/scheduler.py` 的 `TaskStatus` 定义。

---

## 13. Commit 规范

格式：`<type>(<scope>): <subject>`

| type | 含义 |
|------|------|
| feat | 新功能 |
| fix | 缺陷修复 |
| refactor | 重构（不改变行为） |
| docs | 文档/规范 |
| test | 测试 |
| perf | 性能 |
| chore | 构建/工具/配置 |
| spec | 规范变更（本目录） |
| break! | 破坏性变更（须 bump major + CHANGELOG + 通知依赖方） |

- `scope` = 受影响域（agents/backend/frontend/protocol/infra/observ/…）。
- subject 祈使句、小写、≤72 字符。
- **提交前**：运行质量门禁（`ruff format && ruff check --fix && mypy && pytest`）+ 更新 `developer/CHANGELOG.md`。
- **新增/变更 API** 同步更新 `05_API_SPEC.md`；**新增/变更事件**同步更新 `07_EVENT_SPEC.md`；**变更协议**同步更新 `04_PROTOCOL_SPEC.md`。
- 不提交密钥/凭据；不在 commit message 写敏感信息。

---

## 14. Review 规范

- **契约符合性**：是否复用 `protocol/` 类型？是否走 `Message` 信封？是否只经 `api/` 跨域？
- **边界符合性**：是否越界修改他域「禁止修改目录」？是否读过目标 `AGENT.md`？
- **低熵通信**：是否引入全广播？路由是否按需链式？
- **测试**：公共接口是否有测试？bug 修复是否附回归测试？覆盖率达标？
- **文档同步**：API/Event/Protocol 变更是否同步规范 + CHANGELOG？
- **安全**：是否泄露密钥？日志是否脱敏？工具是否沙箱执行 + 权限校验？
- **破坏性**：是否 bump major + 通知依赖方？
- **AI 合规**：是否符合 `11_AI_CODING_SPEC.md`（修改前读规范、单次改动范围、不擅自改协议/API、**生成/修改代码加 `@aegis-gen` 注释头**、测试/文档/冲突处理）。

---

## 15. 规范索引（下游展开）

| 编号 | 文件 | 内容 |
|------|------|------|
| 00 | `00_PROJECT_SPEC.md` | 本文件：项目级 SSOT |
| 01 | `01_ARCHITECTURE_SPEC.md` | 系统架构规范 |
| 02 | `02_DIRECTORY_SPEC.md` | 目录规范（每个目录职责/边界/可改性） |
| 03 | `03_IMPORT_SPEC.md` | Import 规范（依赖矩阵、禁循环） |
| 04 | `04_PROTOCOL_SPEC.md` | 通信协议规范（Message/Event/Task/...） |
| 05 | `05_API_SPEC.md` | API 接口契约规范 |
| 06 | `06_SCHEMA_SPEC.md` | 数据 Schema 规范（Pydantic） |
| 07 | `07_EVENT_SPEC.md` | 事件总线规范 |
| 08 | `08_AGENT_SPEC.md` | Agent Runtime 规范 |
| 09 | `09_DEVELOPMENT_SPEC.md` | 开发流程规范 |
| 10 | `10_INTERFACE_BOUNDARY_SPEC.md` | 接口边界规范（并行开发核心） |
| 11 | `11_AI_CODING_SPEC.md` | AI 编码规范（给 AI Agent；含 `@aegis-gen` 代码注释头） |
| 12 | `12_TECH_STACK_SPEC.md` | 技术栈规范（语言/运行时/框架/库/工具链/版本约束） |
| 13 | `plans/13_FRONTEND_BACKEND_PLAN.md` | 前后端开发全流程计划（含后端↔智能体双向调用架构） |

> 规范冲突时的优先级：`00_PROJECT_SPEC` > `04_PROTOCOL_SPEC` ≈ `05_API_SPEC` ≈ `06_SCHEMA_SPEC` > 其余编号规范 > `developer/` 根旧文档 > 各模块 `AGENT.md`。
