# plan.md — AegisOS 动态开发计划

> **本文件是项目的「活计划」**，整合了 `specs/plans/13`（前后端全流程）、`14`（赛事总体方案）、`15`（实施任务清单）、`roadmap/`（阶段总览）的核心内容。
>
> **结构**：待完成在前（§1-§6）→ 已完成在后（§7）→ 附录（§8-§11）
>
> 维护规则：
> 1. 每完成一个任务 → 勾选 `[x]` + 在 `developer/CHANGELOG.md` 记录
> 2. 每新增计划项 → 添加到对应段下，标注优先级（P0 最高）
> 3. 每次会话结束前 → 更新「最近变更」段
> 4. 待完成区只保留未完成任务；完成后立即移到 §7 完成区
> 5. SSOT 保留：`specs/plans/13`、`14`、`15`、`roadmap/`
>
> 最后更新：2026-08-04 · **P2 记忆/感知/工具全部补全** · 346 测试全通过

---

## 📊 总览

| 维度 | 状态 |
|------|------|
| **当前阶段** | P5 ✅ · P6 ✅ · SDK 集成 S1-S4 ✅ · R2-R5 ✅ · F ✅ · G ✅ · H5 ✅ · AP1 ✅ · AP3 ✅ |
| **测试** | **346 passed**（全模块覆盖） |
| **已完成** | P0-P6 全部 ✅ · F 端点 ✅ · G 视图 ✅ · R2-R6 SDK ✅ · H5 可观测 ✅ · AP1 Plan ✅ · AP3 Goal ✅ · B3+E13 ✅ · P2 记忆/感知/工具补全 ✅ |
| **待完成** | P2 数据层(H2) · AP4 Ask · P3 容器化部署 · AP2 ReAct |
| **赛事截止** | 2026-09-15（XH-202631 荣耀·超长程群体智能） |

### 3 场景覆盖

| 场景 | 描述 | 状态 |
|------|------|------|
| 场景 1 | 网络防御（红→蓝→紫完整链路） | ✅ 可演示 |
| 场景 2 | 超长程攻击链（多步横向移动） | 🔲 待做（功能优先） |
| 场景 3 | 端-边-云协同防御 | 🔲 待做（容器化后） |

---

## 🔥 §1 — P0 立即执行（本周）

> **当前无 P0 阻塞项**。所有紧急任务已在 2026-07-09 前完成。
>
> 下一步优先级：
> 1. **H2** 数据层（Neo4j + Qdrant）接入 — 记忆系统所需
> 2. **AP4 Ask** 行动范式 — 人机协同
> 3. **H1 Docker 沙箱靶场** — 赛事演示必需

---

## ⚡ §2 — P1 短期（1-2 周）

> **所有 P1 任务已完成**（截至 2026-07-09）。以下仅留痕说明范围。

已完成的 P1 任务 → 见 §7 完成区：
- 编排器实现（planner + orchestrator + workflow + eventbus + runtime）
- F 后端攻防 REST 端点（6 个子任务）
- G 前端攻防视图（6 个子任务）
- R4 SDK 编排器深化（8 个子任务）
- R5 旧接口清理 + 流式 + 事件总线（5 个子任务）
- AP1 Plan 范式（5 个子任务）- AP3 Goal 范式（4 个子任务）
---

## 📅 §3 — P2 中期（赛事前）

### H2 — 数据层接入
> **优先级**：P2 · **预估**：2-3 天 · **状态**：🔲 待做
- [ ] H2.1 `data/models/` Neo4j 拓扑图 + ATT&CK 图接入
- [ ] H2.2 `data/models/` Qdrant 向量库接入
- [ ] H2.3 `aegisos_agents/memory/vector/` 对接 Qdrant
- [ ] H2.4 `aegisos_agents/memory/semantic/` 对接 Neo4j ATT&CK 图

### 记忆子系统补全（7 个空模块）✅
> **优先级**：P2 · **预估**：2 天 · **状态**：✅ 完成（2026-08-01）
- [x] `aegisos_agents/memory/archive/` 归档记忆
- [x] `aegisos_agents/memory/cache/` 缓存记忆
- [x] `aegisos_agents/memory/checkpoint/` 检查点
- [x] `aegisos_agents/memory/reflection/` 反思记忆
- [x] `aegisos_agents/memory/retrieval/` 检索
- [x] `aegisos_agents/memory/snapshot/` 快照
- [x] `aegisos_agents/memory/sync/` 同步

### 感知层补全 ✅
> **优先级**：P2 · **预估**：1-2 天 · **状态**：✅ 完成（2026-08-01）
- [x] `aegisos_agents/perception/context/` 上下文管理（TokenBudget + ContextManager）
- [x] `aegisos_agents/perception/reflection/` 反思（ExecutionCritic + OutputScorer + FeedbackLoop）

### 工具层补全 ✅
> **优先级**：P2 · **预估**：1 天 · **状态**：✅ 完成（2026-08-03）
- [x] `aegisos_agents/tools/prompts/` Prompt 管理（PromptRegistry + PromptRenderer）
- [x] `aegisos_agents/tools/runtime/` 运行时（AgentLifecycle + RuntimeSupervisor）

### AP3 — Goal 范式（递归目标分解）
> **优先级**：P2 · **预估**：2 天 · **依赖**：R4（已完成）· **状态**：✅ 完成（2026-07-08）
- [x] AP3.1 `perception/reasoning/strategies/goal_mode.py` - Goal 模式（递归分解 + 失败重试 + 备选路径）
- [x] AP3.2 `CyberOrchestrator` 接入 Goal - 替代固定模板，目标递归分解为子任务 DAG
- [x] AP3.3 `exploit_planner` 支持 Goal 递归 - 复杂目标分解为多阶段子目标
- [x] AP3.4 测试：Goal 范式递归分解 + 失败重试验证（21 测试）

### AP4 — Ask 范式（人机协同）
> **优先级**：P2 · **预估**：1-2 天 · **依赖**：F/G 端点（已完成）· **状态**：🔲 待做
- [ ] AP4.1 `perception/reasoning/strategies/ask_mode.py` — Ask 模式（暂停提问 + 超时降级）
- [ ] AP4.2 `ir_planner` 接入 Ask — 破坏性操作前确认
- [ ] AP4.3 `critic` 接入 Ask — 严重度阈值请求
- [ ] AP4.4 `threat_hunt` 接入 Ask — 不确定时澄清
- [ ] AP4.5 `protocol/event.py` 补充 `HumanInputRequired` / `HumanResponse` 事件
- [ ] AP4.6 前端 `ChatView` 人机交互消息渲染
- [ ] AP4.7 测试：Ask 范式 HITL 流程

---

## 📋 §4 — P3 长期 / 容器化与部署

> **容器化后移策略（2026-07-06）**：所有容器化/部署任务后移至 P3，等功能实现完成后进行。

### H1 — Docker 沙箱靶场
> **优先级**：P3 · **预估**：3-5 天 · **状态**：🔲 后移
- [ ] H1.1 `infrastructure/delivery/deployment/` Docker Compose 靶场编排
- [ ] H1.2 攻防工具容器化（nmap/metasploit/zeek/splunk）
- [ ] H1.3 `infrastructure/transport/communication/` 容器间通信
- [ ] H1.4 靶场安全隔离（永不触真实网络）

### H7 — 部署交付
> **优先级**：P3 · **预估**：3-5 天 · **状态**：🔲 后移
- [ ] H7.1 `Dockerfile.backend` — 后端镜像
- [ ] H7.2 `Dockerfile.frontend` — 前端镜像（多阶段构建）
- [ ] H7.3 `docker-compose.yml` — 一键编排
- [ ] H7.4 `nginx.conf` — Nginx 反向代理
- [ ] H7.5 `conf.d/aegisos.conf` — 站点配置
- [ ] H7.6 `infrastructure/nodes/edge/` 端侧节点
- [ ] H7.7 `infrastructure/nodes/cloud/` 云侧节点
- [ ] H7.8 端边云协同联调
- [ ] H7.9 `tooling/scripts/` 靶场编排脚本

### Protocol → Pydantic 迁移
> **优先级**：P3 · **预估**：3-5 天 · **状态**：🔲 待做
- [ ] R1.1-R1.5 `protocol/*.py` → Pydantic（删除手写 `to_dict()` / `from_dict()`）
- [ ] R1.6 更新所有引用 `asdict()` → `model_dump()`
- [ ] R1.7 测试全通过

### AP2 — ReAct 范式（工具调用循环）
> **优先级**：P3 · **预估**：3-4 天 · **依赖**：H1 沙箱 · **状态**：✅ 完成（2026-08-12）
- [x] AP2.1 `perception/reasoning/strategies/react_mode.py` — ReAct 模式（think→act→observe 循环）
- [x] AP2.2-AP2.6 5 个 Agent 接入 ReAct（recon/vuln_correlator/detector/threat_hunt/forensics）
- [x] AP2.7 测试：ReAct 工具调用循环验证

### 工程支撑（P3）
- [ ] `tooling/scripts/check_no_broadcast.py` 低熵广播检测
- [ ] CI/CD 流水线（GitHub Actions）
- [ ] `tooling/configs/environments/` 多环境覆盖
- [ ] `tooling/configs/agents/` Agent 配置
- [ ] `tooling/configs/models/` 模型配置
- [ ] `tooling/configs/prompts/` Prompt 配置
- [ ] `tooling/configs/deployment.yaml` 部署配置
- [ ] HTTPS / TLS 证书
- [ ] LLM API Key 安全注入
- [ ] 生产级 ASGI 服务器（gunicorn + uvicorn workers）
- [ ] `frontend/dist/` 构建产物校验

---

## 🏆 §5 — 里程碑验收

| 里程碑 | 验收标准 | 状态 |
|--------|----------|------|
| M1（P1-P2） | `cyber.py` 类型可序列化往返；记忆压缩单元测试通过 | ✅ |
| M2（P3-P4） | router 稀疏路由可计算且非全广播；调度可卸载 | ✅ |
| M3（P5） | 红蓝紫 Agent 端到端跑通场景 1 | ✅ E13 |
| M4（P6） | 5 视图可交互，攻击链 DAG 可视化 + 回放 | ✅ F+G |
| M5（P7+演示） | 3 场景可演示，benchmark + 5 维度评测报告 | 🔲 H 待做 |

---

## ✅ §7 — 已完成任务（按完成时间倒序）
### 2026-08-03 P2 全部补全 ✅（346 测试通过）

- [x] **记忆 7 子模块**：retrieval（混合检索 RRF）+ cache（L1/L2 缓存）+ checkpoint（检查点）+ reflection（反思引擎）+ archive（归档）+ snapshot（快照）+ sync（同步）
- [x] **感知 2 子模块**：context（TokenBudget + ContextManager）+ reflection（ExecutionCritic + OutputScorer + FeedbackLoop）
- [x] **工具 2 子模块**：prompts（PromptRegistry + PromptRenderer）+ runtime（AgentLifecycle + RuntimeSupervisor）
- [x] **MemoryStore v2**：recall/retrieve/write 升级 + 编排器 3 钩子 + 7 新属性
- [x] 39（记忆）+ 26（感知）+ 27（工具）= 92 新测试，346 全通过

### 2026-07-08 AP3 Goal 范式（递归目标分解）✅（250 passed）

- [x] **AP3.1** `perception/reasoning/strategies/goal_mode.py` - `GoalMode` 混入类（`decompose()` 递归分解 + `execute_tree()` 依赖序执行 + 失败重试 + 备选路径注入）。`GoalNode`/`GoalResult`/`GoalStatus` 数据类型。3 场景模板（cyber_red/cyber_blue/generic）+ 自定义模板。`create_goal_mode_orchestrator` 工厂。
- [x] **AP3.2** `CyberOrchestrator` 继承 `GoalMode[dict]`，新增 `run_red_chain_with_goal()` / `run_blue_chain_with_goal()`（替代固定模板，递归分解 + 重试 + fallback）。`_create_red_agent_executor()` / `_create_blue_agent_executor()` 执行回调。
- [x] **AP3.3** `exploit_planner/agent.py` 新增 `plan_with_goal()` - 按资产递归分解为初始访问 + 横向移动子目标，失败重试 + 备选路径，汇聚为完整 AttackChain。
- [x] **AP3.4** 21 个测试：数据类型 + decompose（4 场景）+ execute_tree（成功/重试/备选路径/依赖跳过）+ 工厂 + CyberOrchestrator 端到端 + exploit_planner Goal 递归。250 测试全通过。
### 2026-07-09 R4.4-R4.8 SDK 编排深化 + 测试 ✅（208 passed）

- [x] **R4.4** SDK tracing + AgentHooks — `CyberTraceProcessor` + `CyberAgentHooks`（7 个生命周期回调） + `trace()` 包裹编排流程。22 测试通过。
- [x] **R4.5** SDK FunctionTool — `cyber_tools.py`：6 个攻防工具（nmap_scan/metasploit_exploit/lateral_move_exec/query_attck_kb/query_cve_db/correlate_alerts）。工厂函数 + 高危工具 needs_approval 标记。30 测试通过。
- [x] **R4.6** MockRuntime 替换为 CyberOrchestrator — 删除 85 行 dispatch map，链式调用委托编排器。
- [x] **R4.7** `composition.py` DI 注入共享 CyberOrchestrator（Mock/真实模式自动切换）。
- [x] **R4.8** 208 测试全通过。

### 2026-07-09 R5 旧接口清理 + 流式 + 事件总线 ✅

- [x] **R5.1** `base.py` 清理：删除 `ModelProvider` Protocol，保留 `LLMRequest`/`LLMResponse`
- [x] **R5.2** `model_router.py` 删除（无业务引用）
- [x] **R5.3** `_run_streamed` SSE 流式：新增 `backend/routers/stream.py` + `StructuredAgent._run_streamed()` + 前端 `stream.ts` + ChatView Stream 模式
- [x] **R5.4** AgentHooks→EventBus 发布：`CyberAgentHooks` 发布 `AgentStart`/`AgentFinish`/`ToolCall`/`ToolFinish` 事件。6 测试通过。
- [x] **R5.5** 179 测试全通过。

### 2026-07-08 R4.1-R4.3 SDK 编排深化 ✅

- [x] **R4.1** `neuro_symbolic.py` → SDK：`NeuroSymbolicAgent(StructuredAgent[ExploitPlannerResult])` 替代旧 `ModelProvider.complete()` + `json.loads`。4 测试通过。
- [x] **R4.2** SDK handoffs：`ChainContext` 跨 handoff 共享上下文 + `on_handoff` 回调 + `run_red_chain_via_handoffs()`。9 测试通过。
- [x] **R4.3** SDK output_guardrails：`create_attack_chain_guardrail()` + `run_red_chain_with_guardrail()` 手动捕获重试。5 测试通过。

### 2026-07-07 H5 可观测与评测 ✅（41 测试）

- [x] H5.1 `MetricsCollector` 实时监控（订阅 EventBus + 告警规则 + 面板数据）
- [x] H5.2 `Timeline` + `ReplayPlayer` 时序回放（步进/跳跃/定时）
- [x] H5.3 `BenchmarkCase`/`Suite`/`Runner` 性能基准（min/avg/max/p99）
- [x] H5.4 `Evaluator` 5 维度评测（accuracy/recall/latency/resource/robustness）
- [x] H5.5 `ChartGenerator` + `GraphRenderer` + `DashboardAssembler` + `VisualizationService`

### 2026-07-07 AP1 Plan 范式 ✅（9 测试）

- [x] AP1.1 `plan_mode.py` — `PlanMode[T]` 两阶段推理混入 + `PlanResult`/`PlanStep` Pydantic
- [x] AP1.2-AP1.4 `exploit_planner` / `ir_planner` / `lateral_move` 接入 Plan 范式
- [x] AP1.5 9 测试通过（降级路径 + 完整两阶段 + 工厂函数）

### 2026-07-06 编排器实现 ✅ + F 后端 ✅ + G 前端 ✅

**编排器**（P5 收尾）：
- [x] `planning/planner/planner.py` — 4 场景模板（cyber_red/blue/purple/generic），纯算法
- [x] `planning/orchestrator/orchestrator.py` — 整合 Planner + WorkflowEngine + EventBus
- [x] `planning/engine/workflow/engine.py` — Kahn 拓扑排序 + ThreadPoolExecutor + 条件分支
- [x] `planning/engine/eventbus/impl.py` — topic 路由 + FIFO + 死信队列 + 历史回放
- [x] `runtime.py` — CyberRuntime 委托 CyberOrchestrator，实现 RuntimeAPI

**F — 后端攻防端点**（11 测试）：
- [x] F1-F2 靶场端点（`/api/v1/range/start` · `/api/v1/range/{id}/topology`）
- [x] F3 攻击端点（`/api/v1/attack` · `/api/v1/attack/chain/{id}`）
- [x] F4 防御端点（`/api/v1/defense` · `/api/v1/defense/{id}` · `/api/v1/defense/purple-review`）
- [x] F5 `protocol/cyber.py` ThreatIntel ATT&CK 字段扩展 + 威胁情报端点
- [x] F6 攻防端点集成测试全通过

**G — 前端攻防视图**（21 测试）：
- [x] G1 `RedTeamPanel.tsx` — 攻击链 DAG 可视化（SVG + 贝塞尔曲线 + CVSS 评分徽章）
- [x] G2 `BlueTeamPanel.tsx` — 防御看板（告警排序 + 响应计划 + 回滚信息）
- [x] G3 `PurpleTeamPanel.tsx` — 时序回放（Play/Pause/Step forward/backward）
- [x] G4 `ThreatIntelPanel.tsx` — ATT&CK 威胁情报表（9 战术过滤 + 可展开行）
- [x] G5 `protocol/types.ts` 补充 cyber 类型映射
- [x] G6 21 测试全通过（12 API + 9 组件渲染）

### 2026-07-06 B3 记忆接入 runtime 认知循环 + E13 场景 1 端到端 ✅

- [x] B3.1-B3.5 四层记忆（Working/Episodic/Semantic/Vector）+ MemoryStore 集成（read/write/retrieve/recall/compress/end_session）
- [x] E13 场景 1 端到端：recon→vuln_correlator→exploit_planner→detector→triage→threat_hunt→ir_planner→critic→reviewer 全链路
- [x] 90 passed（59→90）

### 2026-07-04 前后端打通 ✅

- [x] `backend/core/composition.py` DI 组合根：14 Agent 注册 + MockRuntime 分发
- [x] `backend/main.py` FastAPI + CORS + TraceMiddleware + lifespan
- [x] 10 REST 端点 + SSE + WebSocket
- [x] `backend/repositories/` SQLAlchemy async + aiosqlite
- [x] `frontend/src/` React 18 + Vite 5 + Zustand + 36 TS 类型
- [x] `ChatView.tsx` 完整实现（Agent 选择 + 消息收发 + 任务轮询）
- [x] 59 测试全通过

### 2026-07-04 统一配置体系 ✅

- [x] `tooling/configs/settings.py` + `defaults.yaml` + `.env.example` + `frontend/src/config/index.ts`
- [x] 20 文件接入统一配置

### 2026-07-04 Phase A-E 核心引擎 TDD ✅

- [x] **Phase A** `protocol/cyber.py` 8 攻防类型（Asset/VulnFinding/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel）
- [x] **Phase B** 记忆压缩/唤醒（compactor 4 测试 + recaller 3 测试）
- [x] **Phase C** 拓扑活跃子图 + Top-K 稀疏路由 + 异构选举（10 测试）
- [x] **Phase D** 端边云三层调度 + 多模型路由（13 测试）
- [x] **Phase E** 11 红蓝紫 Agent + 神经符号闭环（23 测试）
- [x] 59 测试全通过

### 2026-07-04 文档体系 ✅

- [x] `AGENT.md` 末尾「📋 模块实现总览」 + 9 域「📋 模块实现详解」
- [x] `docs/ARCHITECTURE.md` 全 10 域仪表盘
- [x] `CLAUDE.md` 同步更新

### 2026-07-04 Agent 框架调研 ✅

- [x] `docs/RESEARCH_AGENT_FRAMEWORK_REFACTOR.md` — 7 类重复造轮子诊断 + 替换方案

### 2026-07-04 openai-agents SDK 集成 S1-S4 ✅

- [x] S1-S2 `StructuredAgent` 基类 + 11 个 Agent output_type 定义
- [x] S3 批 1/2：红队 4 + 蓝队 5 + 紫队 2 → 全部迁移到 StructuredAgent
- [x] S4 SDKProvider + MockSDKModel 双模式 + CyberOrchestrator 编排器
- [x] 所有 `json.loads` + `try/except` 已删除

### 2026-06-26 P0 初始化 ✅

- [x] 仓库骨架（8 域 + tooling/docs/tests）
- [x] 78 个 AGENT.md
- [x] developer/ 规范层（specs 00-12 + plans 13-15 + roadmap P0-P7）
- [x] protocol/ 通信契约（10 模块 + cyber.py 攻防扩展）

---

## 📌 §8 — 维护提醒

1. **每次会话开始**：读本文件了解当前待办
2. **每次完成任务**：勾选 `[x]` → 更新 `CHANGELOG.md` → 移到 §7 完成区 → 更新「最后更新」行
3. **新增计划项**：添加到对应对应段下 → 标注优先级 + 预估 + 依赖
4. **阶段完成**：更新 `roadmap/README.md` + `AGENT.md` + `docs/ARCHITECTURE.md`

---

## 📎 附录 A — 赛事总体方案（整合自 `plans/14`）

### 产品定位

**AegisOS = Agent Operating System**。赛事作品为「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」：
- **超长程**：攻击链跨数十~数百步、跨小时~天级 → 记忆压缩 + 唤醒 + 分段推理
- **动态异构**：不同模型/Prompt/能力域的异构 Agent 池，拓扑随任务重组
- **群体智能**：红蓝紫对抗 + 元认知 critique/review
- **深度协同推理**：神经（LLM）+ 符号（ATT&CK/CVE 知识图）闭环

### 赛事映射

| 项 | 值 |
|----|-----|
| 赛事 | 挑战杯揭榜挂帅 XH-202631（荣耀终端） |
| 命题 | 面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术 |
| 评分 | 完整性 40 + 应用创新 25 + 技术创新 20 + 性能 15 |
| 截止 | 2026-09-15 |

### 红蓝紫 Agent 角色一览

| 阵营 | 角色 | 输入→输出 |
|------|------|----------|
| 🔴 红队 | recon | 目标范围 → Asset[] |
| 🔴 红队 | vuln_correlator | Asset[] → VulnFinding[] |
| 🔴 红队 | exploit_planner | VulnFinding[] → AttackChain |
| 🔴 红队 | lateral_move | ExploitPlan+Topology → LateralStep[] |
| 🔵 蓝队 | detector | 事件流 → Alert[] |
| 🔵 蓝队 | triage | Alert[] → PrioritizedAlert[] |
| 🔵 蓝队 | threat_hunt | PrioritizedAlert+ATT&CK → HuntHypothesis[] |
| 🔵 蓝队 | ir_planner | HuntHypothesis → ResponsePlan |
| 🔵 蓝队 | forensics | ResponsePlan → ForensicReport |
| 🟣 紫队 | critic | 红蓝产出 → 反驳/校验 |
| 🟣 紫队 | reviewer | 产出 → 一致性结论 |

---

## 📎 附录 B — 前后端开发计划（整合自 `plans/13`）

### 后端 REST 端点

| 方法 | 路径 | 状态 |
|------|------|------|
| GET | /api/v1/health | ✅ |
| POST | /api/v1/sessions | ✅ |
| GET/DELETE | /api/v1/sessions/{id} | ✅ |
| POST | /api/v1/tasks | ✅ |
| GET | /api/v1/tasks · /api/v1/tasks/{id} | ✅ |
| POST | /api/v1/tasks/{id}/cancel | ✅ |
| GET | /api/v1/agents | ✅ |
| GET | /api/v1/agents/{id} | ✅ |
| POST | /api/v1/agents/{id}/invoke | ✅ |
| GET/POST | /api/v1/memory/{session} | ✅ |
| GET | /api/v1/graph | ✅ |
| POST | /api/v1/tools/{name}/invoke | ✅ |
| GET | /api/v1/metrics | ✅ |
| GET | /api/v1/replay/{session} | ✅ |
| WS | /ws/v1/stream | ✅ |
| SSE | /api/v1/events | ✅ |
| POST | /api/v1/range/* | ✅ F |
| GET | /api/v1/threat/attack-techniques | ✅ F |
| POST | /api/v1/stream/* | ✅ R5.3 |

---

## 📎 附录 C — 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI / Uvicorn / SQLAlchemy+aiosqlite |
| 图 | Neo4j ≥ 5 |
| 向量 | Qdrant ≥ 1.8 |
| LLM | openai-agents SDK / StructuredAgent / MockSDKModel |
| 前端 | React 18 / TS 5 / Vite 5 / Zustand |
| 测试 | pytest 9.1.1 / Playwright / Vitest |

---

## 📎 附录 D — Roadmap 阶段总览

| 阶段 | 名称 | 状态 |
|------|------|------|
| P0 | 项目初始化 | ✅ |
| P1 | Protocol | ✅ |
| P2 | Memory | ✅（7 空模块待补） |
| P3 | Router | ✅ |
| P4 | Scheduler | ✅ |
| P5 | Planner+Agents | ✅ |
| P6 | Frontend | ✅ |
| P7 | Deployment | 🔲 |

---

## 🔄 最近变更

| 日期 | 变更 | 提交 |
|------|------|------|
| 2026-08-01 | **P2 记忆子系统补全**：retrieval/cache/checkpoint/reflection/archive/snapshot/sync 7 模块 + MemoryStore v2 集成 + 39 新测试 | — |
| 2026-07-08 | **R6 SDK 对齐清理**：删除 `sdk_provider.complete()` 死代码 + 未使用 import；修复 `__init__.py` 注释规范 | - |
| 2026-07-08 | **AP3 Goal 范式完成**：递归分解 + 失败重试 + 备选路径（21 测试） | - || 2026-07-08 | **plan.md 重组**：待完成区与完成区分离，已完成任务集中到 §7 | — |
| 2026-07-09 | R4.4-R4.8 SDK 编排深化完成 + R5 旧接口清理/流式/事件总线完成 | `af88bdf` |
| 2026-07-08 | R4.1-R4.3 SDK handoffs/guardrails/neuro_symbolic 完成 | （见 CHANGELOG） |
| 2026-07-07 | H5 可观测评测完成（41 测试）+ AP1 Plan 范式完成（9 测试） | （见 CHANGELOG） |
| 2026-07-06 | 编排器 + F 端点 + G 视图完成 + B3 记忆闭环 + E13 e2e + 容器化后移 P3 | （见 CHANGELOG） |
