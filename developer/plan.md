# plan.md — AegisOS 动态开发计划

> **本文件是项目的「活计划」**，整合了 `specs/plans/13`（前后端全流程）、`14`（赛事总体方案）、`15`（实施任务清单）的核心内容，动态维护当前未完成的内容和下一步计划。
>
> **结构**：待完成在前（§1-§7）→ 已完成在后（§8-§10）→ 附录（§11-§12）
>
> 维护规则：
> 1. 每完成一个任务 → 勾选 `[x]` + 在 `developer/CHANGELOG.md` 记录
> 2. 每新增计划项 → 添加到对应 Phase 下，标注优先级（P0 最高）
> 3. 每次会话结束前 → 更新「最近变更」段
> 4. 本文件已整合 `roadmap/`（阶段总览，详见附录 D）；`roadmap/` 仍作为 SSOT 保留
> 5. `specs/plans/13`、`14`、`15` 及 `roadmap/` 仍作为 SSOT 保留，本文件为执行态整合视图
>
> 最后更新：2026-07-06 · 90 测试全通过 · B3 记忆接入 runtime ✅ · E13 场景 1 端到端 ✅ · 文档对齐实际结构 ✅ · 整合 roadmap 到附录 D ✅

---

## 📊 总览

| 维度 | 状态 |
|------|------|
| **当前阶段** | P5 收尾 + P6 部分 + 框架规范化方案(R1-R5) + 赛事 Phase F-H 待启动 |
| **测试** | 90 passed（protocol 6 + memory 33 + planning 18 + tools 5 + action 19 + perception 4 + e2e 5） |
| **已完成 Phase** | A ✅ · B ✅ · C ✅ · D ✅ · E ✅ · 前后端打通 ✅ · 文档对齐 ✅ |
| **待完成 Phase** | 编排器 · F · G · H · R1-R5 |
| **赛事截止** | 2026-09-15（XH-202631 荣耀·超长程群体智能） |

### 赛事对齐（详见 §11 附录）

| 评分维度 | 占比 | 对应任务 | 状态 |
|---------|------|---------|------|
| 完整性 | 40 | 8 域全实现 + 3 场景可演示 + 回放 | A-E ✅ / F-H 🔲 |
| 应用创新 | 25 | 攻防对抗仿真 + 跨领域 3 场景 | Agent ✅ / 场景 🔲 |
| 技术创新 | 20 | 动态异构拓扑 + 低熵路由 + 神经符号闭环 + 记忆压缩唤醒 | C/D/B/E ✅ |
| 性能 | 15 | benchmark + 端边云三层调度优化 | 调度 ✅ / 评测 🔲 |

### 3 场景覆盖

| 场景 | 描述 | 依赖 | 状态 |
|------|------|------|------|
| 场景 1 | 网络防御（红→蓝→紫完整链路） | B3 + E13 + 编排器 | 🔲 待做 |
| 场景 2 | 超长程攻击链（多步横向移动） | 场景 1 + H1 靶场 | 🔲 待做 |
| 场景 3 | 端-边-云协同防御 | 场景 1 + H7 端边云 | 🔲 待做 |

### 🔥 P0 — 立即执行（本周）

> ✅ B3 + E13 已于 2026-07-06 完成，详见 §8「已完成任务」。下一步 P1：编排器实现。

### ⚡ P1 — 短期（1-2 周）

#### 编排器实现（P5 收尾）
> **优先级**：P1 · **预估**：2-3 天 · **阻塞**：E13、F
- [ ] `agents/planning/planner/` Planner 实现（任务分解 → 子任务 DAG）
- [ ] `agents/planning/orchestrator/` Orchestrator 实现（多 Agent 编排调度）
- [ ] `agents/planning/engine/workflow/` Workflow 引擎（DAG 执行）
- [ ] `agents/planning/engine/eventbus/` EventBus 实现（8 事件发布/订阅）
- [ ] 编排器集成 MockRuntime → 替换为真实 Runtime

#### F — 后端攻防 REST 端点
> **优先级**：P1 · **预估**：2 天 · **依赖**：编排器
- [ ] F1 `backend/routers/range.py` 靶场管理端点（`/api/v1/range/*`）
- [ ] F2 `backend/routers/topology.py` 拓扑端点（`/api/v1/topology`）
- [ ] F3 `backend/routers/attack.py` 攻击端点（`/api/v1/attack` · `/api/v1/attack/chain`）
- [ ] F4 `backend/routers/defense.py` 防御端点（`/api/v1/defense` · `/api/v1/alerts` · `/api/v1/response`）
- [ ] F5 `protocol/cyber.py` ThreatIntel 补充 ATT&CK 技战术映射字段
- [ ] F6 后端测试：攻防端点集成测试

#### G — 前端攻防视图
> **优先级**：P1 · **预估**：3-4 天 · **依赖**：F
- [ ] G1 `frontend/views/canvas/CanvasView.tsx` 攻击链 DAG 可视化（React Flow）
  - 节点：Asset / AttackStep / 节点状态颜色
  - 边：攻击路径
- [ ] G2 `frontend/views/monitor/MonitorView.tsx` 防御看板
  - 告警列表 + 严重度排序
  - 响应计划 + 执行状态
- [ ] G3 `frontend/views/replay/ReplayView.tsx` 时序回放
  - 时间轴拖拽
  - 攻击链逐步回放
- [ ] G4 `frontend/views/graph/GraphView.tsx` 异构图可视化
- [ ] G5 `frontend/src/protocol/types.ts` 补充 cyber 类型映射
- [ ] G6 前端测试：视图交互测试

### 📅 P2 — 中期（赛事前）

#### H1 — Docker 沙箱靶场
> **优先级**：P2 · **预估**：3-5 天
- [ ] H1.1 `infrastructure/delivery/deployment/` Docker Compose 靶场编排
- [ ] H1.2 攻防工具容器化（nmap/metasploit/zeek/splunk 等）
- [ ] H1.3 `infrastructure/transport/communication/` 容器间通信
- [ ] H1.4 靶场安全隔离（永不触真实网络）

#### H2 — 数据层接入
> **优先级**：P2 · **预估**：2-3 天
- [ ] H2.1 `data/models/` Neo4j 拓扑图 + ATT&CK 图接入
- [ ] H2.2 `data/models/` Qdrant 向量库接入
- [ ] H2.3 `agents/memory/vector/` 对接 Qdrant
- [ ] H2.4 `agents/memory/semantic/` 对接 Neo4j ATT&CK 图

#### H5 — 可观测与评测
> **优先级**：P2 · **预估**：2-3 天
- [ ] H5.1 `observability/inspect/monitor/` 实时监控实现
- [ ] H5.2 `observability/inspect/replay/` 攻击链回放实现
- [ ] H5.3 `observability/measure/benchmark/` 性能基准测试
- [ ] H5.4 `observability/measure/evaluation/` 5 维度评测（准确率/召回率/延迟/资源/鲁棒性）
- [ ] H5.5 `observability/present/visualization/` 数据可视化

#### H7 — 部署交付
> **优先级**：P2 · **预估**：3-5 天
- [ ] H7.1 `infrastructure/delivery/deployment/docker/Dockerfile.backend` — 后端镜像
- [ ] H7.2 `infrastructure/delivery/deployment/docker/Dockerfile.frontend` — 前端镜像（多阶段构建：node build → nginx serve）
- [ ] H7.3 `infrastructure/delivery/deployment/docker/docker-compose.yml` — 一键编排（backend + frontend + nginx + db）
- [ ] H7.4 `infrastructure/delivery/deployment/nginx/nginx.conf` — Nginx 反向代理配置
  - 前端静态文件服务（`dist/`）
  - `/api/` → backend:8000 REST 代理
  - `/ws/` → backend:8000 WebSocket 升级代理
  - gzip 压缩 + 连接超时
- [ ] H7.5 `infrastructure/delivery/deployment/nginx/conf.d/aegisos.conf` — 站点配置
- [ ] H7.6 `infrastructure/nodes/edge/` 端侧节点实现
- [ ] H7.7 `infrastructure/nodes/cloud/` 云侧节点实现
- [ ] H7.8 端边云协同联调
- [ ] H7.9 `tooling/scripts/` 靶场编排脚本

### 📋 P3 — 长期 / 技术债

#### Agent 框架规范化与替换（详见 `docs/RESEARCH_AGENT_FRAMEWORK_REFACTOR.md`）
> **优先级**：P3 · **预估**：5-7 天 · **收益**：代码量 -70%，新增 checkpoint/流式/100+模型兼容

**阶段 1: Protocol → Pydantic**（1 域 / ≤8 文件）
- [ ] R1.1 `protocol/cyber.py` → Pydantic BaseModel（删除手写 `to_dict()` / `from_dict()`）
- [ ] R1.2 `protocol/message.py` → Pydantic
- [ ] R1.3 `protocol/graph.py` → Pydantic
- [ ] R1.4 `protocol/agent.py` / `event.py` / `scheduler.py` / `memory.py` → Pydantic
- [ ] R1.5 `protocol/tool.py` / `heartbeat.py` / `sync.py` → Pydantic
- [ ] R1.6 更新所有引用：`asdict()` → `model_dump()` / `from_dict()` → `model_validate()`
- [ ] R1.7 59 测试全通过

**阶段 2: LLM Provider → litellm + instructor**（≤4 文件）
- [ ] R2.1 安装 `litellm` + `instructor` 依赖
- [ ] R2.2 新建 `agents/tools/llms/unified_provider.py`（~30 行，替代 4 个手写 Provider ~220 行）
- [ ] R2.3 `ModelRouter` 改为委托 `UnifiedProvider`
- [ ] R2.4 MockProvider 保留（测试用），实现 litellm mock adapter
- [ ] R2.5 删除 `openai_provider.py` / `anthropic_provider.py` / `local_provider.py`
- [ ] R2.6 59 测试全通过

**阶段 3: Agent 结构化输出 → instructor**（≤8 文件/批，分 2 批）
- [ ] R3.1 批 1（红队 4 Agent）：recon / vuln_correlator / exploit_planner / lateral_move
- [ ] R3.2 批 2（蓝队 5 + 紫队 2 Agent）：detector / triage / threat_hunt / ir_planner / forensics / critic / reviewer
- [ ] R3.3 每个 Agent 的 `json.loads` + `try/except` 替换为 `instructor` 结构化调用
- [ ] R3.4 删除 SYSTEM_PROMPT 中的 JSON 格式说明（instructor 自动注入）
- [ ] R3.5 59 测试全通过

**阶段 4: LangGraph 编排**（≤4 文件）
- [ ] R4.1 安装 `langgraph` + `langgraph-checkpoint-sqlite`
- [ ] R4.2 新建 `agents/planning/orchestrator/attack_graph.py`（红队攻击链图）
- [ ] R4.3 新建 `agents/planning/orchestrator/defense_graph.py`（蓝队防御链图）
- [ ] R4.4 `MockRuntime` 替换为 `GraphRuntime`（实现 `RuntimeAPI`）
- [ ] R4.5 `backend/core/composition.py` 注入 `GraphRuntime`（删除 ~200 行手写 dispatch map）
- [ ] R4.6 59 测试全通过

**阶段 5: 事件总线 + 流式**（≤2 文件）
- [ ] R5.1 新建 `agents/planning/engine/eventbus/impl.py`（基于 `blinker` 或 LangGraph callback）
- [ ] R5.2 LangGraph `app.stream()` → SSE → 前端 `EventSource`
- [ ] R5.3 59 测试全通过

#### 协议迁移（已并入 R1 阶段）
- [ ] `protocol/scheduler.py` Task 补充 `payload` 字段（当前 MockRuntime 用 getattr fallback）

#### 记忆子系统补全（10 个空模块）
- [ ] `agents/memory/archive/` 归档记忆
- [ ] `agents/memory/cache/` 缓存记忆
- [ ] `agents/memory/checkpoint/` 检查点
- [ ] `agents/memory/reflection/` 反思记忆
- [ ] `agents/memory/retrieval/` 检索
- [ ] `agents/memory/snapshot/` 快照
- [ ] `agents/memory/sync/` 同步

#### 感知层补全
- [ ] `agents/perception/context/` 上下文管理
- [ ] `agents/perception/reflection/` 反思

#### 工具层补全
- [ ] `agents/tools/prompts/` Prompt 管理
- [ ] `agents/tools/runtime/` 工具运行时

#### 工程支撑
- [ ] `tooling/scripts/check_no_broadcast.py` 低熵全广播检测（C4）
- [ ] CI/CD 流水线（GitHub Actions）
- [ ] `tooling/configs/environments/` 多环境覆盖（dev/staging/prod）
- [ ] `tooling/configs/agents/` Agent 配置（角色/能力/资源限制）
- [ ] `tooling/configs/models/` 模型配置（多模型路由策略/Token 限额）
- [ ] `tooling/configs/prompts/` Prompt 配置（版本化管理）
- [ ] `tooling/configs/deployment.yaml` 部署环境差异配置
- [ ] HTTPS / TLS 证书配置（赛事演示域名）
- [ ] `agents/tools/llms/` 真实 LLM API Key 安全注入（环境变量，不硬编码）
- [ ] 后端生产级 ASGI 服务器（gunicorn + uvicorn workers）
- [ ] `frontend/dist/` 构建产物校验 + CDN 预留

---

## ✅ 已完成任务（留痕，按完成时间倒序）

### 2026-07-06 B3 记忆接入 runtime 认知循环 + E13 场景 1 端到端 ✅（90 测试）

**B3 — 记忆接入 runtime 认知循环**（agents/memory/ 域，11 文件 + 5 测试文件，+31 测试）
- [x] B3.1 `agents/memory/working/store.py` — WorkingMemory 工作记忆（按 session 隔离的上下文栈，add/get/clear/sessions）
- [x] B3.2 `agents/memory/episodic/store.py` — EpisodicMemory 情景记忆（跨会话历史经验累积，add/all/by_task）
- [x] B3.3 `agents/memory/semantic/store.py` — SemanticMemory 语义记忆（ATT&CK/CVE 知识库，预置 8 个种子技战术，add/get/search/seed_attack_knowledge）
- [x] B3.4 `agents/memory/vector/store.py` — VectorMemory 向量记忆（余弦相似度 Top-K 检索，Qdrant 接入预留位，add/search）
- [x] B3.5 `agents/memory/memory_store.py` — MemoryStore 集成层：聚合四层存储 + compactor + recaller，实现 MemoryAPI（read/write/retrieve），提供 recall/search_knowledge/compress/end_session 形成认知循环闭环
- [x] B3.6 测试：`tests/agents/memory/test_working.py`(4) + `test_episodic.py`(3) + `test_semantic.py`(4) + `test_vector.py`(5) + `test_memory_store.py`(10) = 26 测试

**E13 — 场景 1 端到端测试**（tests/e2e/ 域，1 测试文件，+5 测试）
- [x] E13.1 `tests/e2e/test_scenario1.py` — 红→蓝→紫完整链路
- [x] E13.2 测试流程：recon → vuln_correlator → exploit_planner → detector → triage → threat_hunt → ir_planner → critic → reviewer
- [x] E13.3 验证 AttackChain → Alert → ResponsePlan → Critique 全链路数据流 + B3 记忆闭环（write → recall → compress → 压缩后仍可唤醒）

**质量门禁**：ruff format ✅ · ruff check ✅（我的文件全通过）· mypy ✅（实现文件 0 错误，protocol/ 既有 39 错误未触碰）· pytest 90 passed（59→90）

### 2026-07-05 文档对齐实际结构 ✅
- [x] 全工程 14 个治理文档路径对齐：backend 扁平化（src/→扁平 + gateway/→core/ + controllers/→routers/ + mappers/→repositories/+models/）+ frontend mappers/→lib/（store/+api-client/）
- [x] 模式名修正：Controller-Service-Mapper → Controller-Service-Lib（前端）/ Router-Service-Repository-Model（后端）
- [x] CHANGELOG.md 历史引用保持不动（记录过去重构事件的史实）

### 2026-07-04 前后端打通 ✅
- [x] `backend/core/composition.py` DI 组合根：14 Agent 注册 + MockRuntime 真实调用分发
- [x] `backend/main.py` FastAPI app + CORS + TraceMiddleware + lifespan
- [x] 10 个 REST 端点（health/sessions/tasks/agents/graph/memory/tools/metrics/replay）
- [x] SSE `events.py` + WebSocket `stream.py`
- [x] `backend/repositories/` SQLAlchemy async + aiosqlite（SessionEntity/TaskEntity）
- [x] `frontend/src/` React + Vite + Zustand + 36 个 TS 类型
- [x] `frontend/views/chat/ChatView.tsx` 完整实现（Agent 选择 + 消息收发 + 任务轮询）
- [x] 59 测试全通过

### 2026-07-04 统一配置体系 ✅
- [x] `tooling/configs/settings.py` — Python 统一配置加载器（环境变量 > .env > defaults.yaml > 代码默认值）
- [x] `tooling/configs/defaults.yaml` — 全项目默认值 SSOT
- [x] `tooling/configs/.env.example` — 环境变量模板
- [x] `frontend/src/config/index.ts` — 前端统一配置入口
- [x] 后端 5 文件 + 前端 3 文件 + 脚本/构建配置全部接入

### 2026-07-04 Phase A-E 核心引擎 TDD 实现 ✅（59 测试）
- [x] **Phase A** — `protocol/cyber.py` 8 个攻防 dataclass（Asset/VulnFinding/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel）+ 6 测试
- [x] **Phase B（部分）** — `protocol/memory.py` 扩 kind/recent + `agents/memory/compression/compactor.py` 上下文压缩（4 测试）+ `agents/memory/recall/recaller.py` 记忆唤醒 Top-5（3 测试）
- [x] **Phase C** — `protocol/graph.py` 扩 GraphNode.status + `agents/planning/engine/topology/topology.py` 活跃子图（3 测试）+ `agents/planning/engine/router/router.py` Top-K=3 稀疏路由（4 测试）+ `agents/planning/engine/router/election.py` 异构选举点积（3 测试）
- [x] **Phase D** — `agents/planning/engine/scheduler/scheduler.py` 端-边-云三层卸载（device/edge/cloud，8 测试）+ `agents/tools/llms/model_router.py` 多模型路由（TIER_PROVIDER_MAP 三层映射，5 测试）+ openai/anthropic/local Provider 实现
- [x] **Phase E（部分）** — E1-E11 11 个攻防 Agent 全部实现（红队 4 + 蓝队 5 + 紫队 2 = 19 测试）+ E12 `agents/perception/reasoning/neuro_symbolic.py` 神经符号闭环（4 测试），共 23 测试

### 2026-07-04 文档体系 ✅
- [x] 根 `AGENT.md` 末尾「📋 模块实现总览」段 — 10 大模块总览（原根 `MODULE.md` 已合并）
- [x] 9 个域 `AGENT.md` 末尾「📋 模块实现详解」段（protocol/agents/backend/frontend/infrastructure/observability/data/tooling/developer，原各域 `MODULE.md` 已合并）
- [x] `docs/ARCHITECTURE.md` — 全 10 域实现状态仪表盘
- [x] `README.md` 模块文档索引表
- [x] `CLAUDE.md`（根 + `.claude/`）同步更新

### 2026-07-04 Agent 框架规范化调研 ✅
- [x] `docs/RESEARCH_AGENT_FRAMEWORK_REFACTOR.md` — 7 类重复造轮子诊断 + litellm/instructor/LangGraph 替换方案（→ R1-R5 待执行）

### 2026-06-26 P0 初始化 ✅
- [x] AegisOS 仓库骨架（37 顶层模块 → 同域聚合分层 → 8 域 + tooling/docs/tests）
- [x] 全仓库 AGENT.md 体系（78 个）
- [x] developer/ 规范层（specs 00-12 + plans 13-15 + roadmap P0-P7）
- [x] protocol/ 通信契约（10 模块 + cyber.py 攻防扩展）

---

## 📌 维护提醒

1. **每次会话开始**：读本文件了解当前待办 + 宏观阶段（附录 D 整合自 `roadmap/`）
2. **每次完成任务**：勾选 `[x]` → 更新 `CHANGELOG.md` → 更新本文件「最近变更」段 → 从待完成移到已完成
3. **新增计划项**：添加到对应 Phase 下 → 标注优先级（P0/P1/P2/P3）→ 标注预估时间和依赖
4. **阶段完成**：更新 `roadmap/README.md` 进度勾选 + 本文件附录 D 进度勾选 + `AGENT.md` 末尾「📋 模块实现详解」实现状态 + `docs/ARCHITECTURE.md` 仪表盘
5. **本文件路径**：`developer/plan.md` — 整合 `specs/plans/13`、`14`、`15` 的执行态视图；SSOT 仍为原文件

---

## 📎 附录 A — 赛事总体方案摘要（整合自 `plans/14`）

### 产品定位

**AegisOS = Agent Operating System**。赛事作品以 AegisOS 为底座，构建「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」：

- **超长程**：攻击链/防御响应跨数十~数百步、跨小时~天级时序 → 记忆压缩 + 唤醒 + 分段推理
- **动态异构**：Agent 群体由不同模型/不同 Prompt/不同能力域的异构单元组成，拓扑随任务动态重组
- **群体智能**：多 Agent 协同（红蓝紫对抗 + 元认知 critique/review）
- **深度协同推理**：神经（LLM）+ 符号（ATT&CK/CVE 知识图）闭环，可解释、可回放、可验证

### 赛事映射

| 项 | 值 |
|----|-----|
| 赛事 | 挑战杯揭榜挂帅 XH-202631（荣耀终端股份有限公司） |
| 命题 | 面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术 |
| 评分构成 | 完整性 40 + 应用创新 25 + 技术创新 20 + 性能 15 |
| 截止 | 2026-09-15 |

### 命题分解

| 命题关键词 | 本方案对应能力 | 落地位置 |
|-----------|---------------|---------|
| 超长程 | 记忆压缩/唤醒、分段 Planner、时序回放 | `agents/memory/`、`agents/planning/engine/planner/`、`observability/inspect/replay/` |
| 动态异构 | 异构 Agent 池 + 动态拓扑选举 + 多模型兼容层 | `agents/`、`agents/planning/engine/topology/`、`agents/tools/llms/` |
| 群体协同 | 红蓝紫对抗 + router 稀疏路由 + critic/reviewer | `agents/planning/engine/router/`、`agents/action/critic/` |
| 深度协同推理 | 神经-符号闭环（LLM ↔ ATT&CK/CVE 图） | `agents/perception/reasoning/`、`data/` |

### 红蓝紫 Agent 角色一览

| 阵营 | 角色 | 目录 | 输入→输出 |
|------|------|------|----------|
| 🔴 红队 | recon | `agents/action/recon/` | 目标范围 → Asset[] |
| 🔴 红队 | vuln_correlator | `agents/action/vuln_correlator/` | Asset[] → VulnFinding[] |
| 🔴 红队 | exploit_planner | `agents/action/exploit_planner/` | VulnFinding[] → AttackChain |
| 🔴 红队 | lateral_move | `agents/action/lateral_move/` | ExploitPlan+Topology → LateralStep[] |
| 🔵 蓝队 | detector | `agents/action/detector/` | 事件流 → Alert[] |
| 🔵 蓝队 | triage | `agents/action/triage/` | Alert[] → PrioritizedAlert[] |
| 🔵 蓝队 | threat_hunt | `agents/action/threat_hunt/` | PrioritizedAlert+ATT&CK → HuntHypothesis[] |
| 🔵 蓝队 | ir_planner | `agents/action/ir_planner/` | HuntHypothesis → ResponsePlan |
| 🔵 蓝队 | forensics | `agents/action/forensics/` | ResponsePlan → ForensicReport |
| 🟣 紫队 | critic | `agents/action/critic/` | 红蓝产出 → 反驳/校验 |
| 🟣 紫队 | reviewer | `agents/action/reviewer/` | 产出 → 一致性结论 |

### 端边云调度策略（四规则 + 降级）

| 层 | 物理形态 | 算力 | 延迟 | 攻防场景 |
|----|---------|------|------|---------|
| 端 (device) | PC/手机/IoT/防火墙 | 极弱（规则/1-3B 小模型） | <100ms | 本地告警分诊、轻量 IDS |
| 边 (edge) | 边缘网关/机架服务器 | 中等（7-14B, Ollama/vLLM） | <1s | 区域威胁聚合、ATT&CK 初筛 |
| 云 (cloud) | GPU 集群/模型 API | 强（70B+/GPT-4o） | 1-5s | 全局攻击链推理、跨域关联 |

调度规则：① privacy=local → 端 ② latency<1s → 端 ③ latency<5s → 边 ④ 默认 → 云。降级：端→边→云。

### 后端攻防端点（Phase F 细节）

| 端点 | → service | 说明 |
|------|-----------|------|
| POST /api/v1/range/start | range.start | 启动靶场会话 |
| GET /api/v1/range/{id}/topology | range.topology | 靶场网络拓扑 |
| POST /api/v1/range/{id}/red/attack | range.red_attack | 提交红队目标→群体推理攻击链 |
| GET /api/v1/range/{id}/chain | range.chain | 攻击链 DAG |
| GET /api/v1/range/{id}/defense | range.defense | 蓝队响应 + 防御动作 |
| GET /api/v1/threat/attack-techniques | threat.techniques | ATT&CK 图查询 |

> 编排仍走 `RuntimeAPI.submit(task)`（见 `plans/13` §3.1）；端点仅领域入口。

### 里程碑验收

| 里程碑 | 验收标准 | 状态 |
|--------|----------|------|
| M1（P1-P2） | `cyber.py` 类型可序列化往返；记忆压缩单元测试通过 | ✅ |
| M2（P3-P4） | router 稀疏路由可计算且非全广播；调度可卸载 | ✅ |
| M3（P5） | 红蓝紫 Agent 端到端跑通场景 1（攻击链→响应→回放） | ✅ E13 完成 |
| M4（P6） | 5 视图可交互，攻击链 DAG 可视化 + 回放 | 🔲 F/G 待做 |
| M5（P7+演示） | 3 场景可演示，benchmark + 5 维度评测报告就绪 | 🔲 H 待做 |

---

## 📎 附录 B — 前后端开发计划摘要（整合自 `plans/13`）

### 后端↔智能体双向调用设计

- **正向**：后端经 `agents.api.RuntimeAPI.submit(task)` 编排智能体（后端→agents 正向依赖）
- **反向**：智能体经 DI 端口回调后端（`agents/api/ports.py` 定义端口 Protocol，backend 实现并注入，经典 DIP 零逆向 import）
  - `PersistencePort`：save_task_result / save_artifact
  - `SessionPort`：get_session / get_user_context
  - `TaskUpdatePort`：update_status
  - 凡能走 EventBus 的不设端口

### 后端 REST 端点（现有 + 攻防扩展）

| 方法 | 路径 | → service | 状态 |
|------|------|-----------|------|
| GET | /api/v1/health | — | ✅ |
| POST | /api/v1/sessions | session.create | ✅ |
| GET/DELETE | /api/v1/sessions/{id} | session.get/close | ✅ |
| POST | /api/v1/tasks | task.create → RuntimeAPI.submit | ✅ |
| GET | /api/v1/tasks · /api/v1/tasks/{id} | task.list/get | ✅ |
| POST | /api/v1/tasks/{id}/cancel | task.cancel | ✅ |
| GET | /api/v1/agents | agent.list → AgentRegistryAPI | ✅ |
| GET | /api/v1/agents/{id} | agent.get | ✅ |
| POST | /api/v1/agents/{id}/invoke | agent.invoke → RuntimeAPI.run | ✅ |
| GET/POST | /api/v1/memory/{session} | memory.read/write → MemoryAPI | ✅ |
| GET | /api/v1/graph | graph.get → EventBus 订阅缓存 | ✅ |
| POST | /api/v1/tools/{name}/invoke | tool.invoke → ExecutionAPI | ✅ |
| GET | /api/v1/metrics | metrics → MonitorAPI | ✅ |
| GET | /api/v1/replay/{session} | replay → ReplayAPI | ✅ |
| WS | /ws/v1/stream?session= | EventStream → EventBus.subscribe | ✅ |
| SSE | /api/v1/events?stream= | EventStream → EventBus.subscribe | ✅ |
| POST | /api/v1/range/* | range.* | 🔲 Phase F |
| GET | /api/v1/threat/attack-techniques | threat.techniques | 🔲 Phase F |

### 前端分层职责

| 层 | 目录 | 职责 |
|----|------|------|
| Controllers | `frontend/src/controllers/` | 交互/事件处理 + 调 service + 分发 views |
| Services | `frontend/src/services/` | API 调用（经 api-client）、WS/SSE 管理、状态编排 |
| Lib | `frontend/src/lib/` | HTTP 客户端（api-client/）、全局 store（Zustand） |
| Views | `frontend/src/views/` | chat ✅ / canvas 🔲 / graph 🔲 / monitor 🔲 / replay 🔲 |

### 并行与依赖编排

```
protocol(P1) ──┬─→ backend 骨架 ──→ routers→services→repositories ──→ 智能体集成(需 P5) ──→ 测试
               └─→ frontend 骨架 ──→ lib→services→controllers→views ──→ E2E(需后端)
gen_ts_types.py 是前后端契约同步桥梁，protocol 变更后 CI 重跑
```

---

## 📎 附录 C — 实施任务清单摘要（整合自 `plans/15`）

> 核心算法任务（A/B/C）已含完整 TDD 代码并实现；其余任务含确切路径 + 接口契约 + 验收命令。

### Global Constraints

- `protocol/` 是唯一数据契约；现有 `@dataclass`（非 Pydantic），新增类型沿用 dataclass 风格
- id 字段统一 `*_id`；枚举用驼峰（`NodeKind.Agent`）；`Graph.nodes` 为 dict
- 跨域调用仅经 `api/`；跨模块禁裸 dict，用 Message 信封
- 禁低熵全广播：router 仅 Top-K 稀疏路由
- AI 改动 ≤1 域、≤8 文件、行为保持、含测试
- 攻防工具仅 Docker 沙箱靶场内运行，永不触真实网络
- API 签名变更 = 破坏性（major bump + CHANGELOG）

### 技术栈（生产级）

| 层 | 技术 | 版本约束 |
|----|------|---------|
| 后端 | FastAPI / Uvicorn / SQLAlchemy+aiosqlite | >=0.110 / >=0.29 / >=2.0 |
| 消息 | Redis Streams | >=7 |
| 图 | Neo4j | >=5 |
| 向量 | Qdrant | >=1.8 |
| 沙箱 | Docker | — |
| 通信 | gRPC / MQTT | — |
| LLM | OpenAI 兼容多模型层 | — |
| 前端 | React 18 / TS 5 / Vite 5 / Zustand / React Flow / Tailwind / shadcn | — |

---

## 📎 附录 D — Roadmap 阶段总览（整合自 `developer/roadmap/`）

> 本附录整合 `developer/roadmap/README.md` 及 `P0/`–`P7/` 各阶段详情。**注意**：此处 P0–P7 指 **roadmap 开发阶段**，与上方「待完成」§5–§8 中的 **P0–P3 优先级标签**（立即执行/短期/中期/长期）含义不同，勿混淆。
>
> SSOT 仍为 `developer/roadmap/`，本附录为执行态整合视图。

### 阶段推进链

```
P0 项目初始化 → P1 Protocol → P2 Memory → P3 Router → P4 Scheduler → P5 Planner+Agents → P6 Frontend → P7 Deployment
```

### 阶段总览

| 阶段 | 名称 | 目标 | 完成标准 | 状态 |
|------|------|------|----------|------|
| P0 | 项目初始化 | 搭建骨架与开发规范 | 可运行空壳 + 文档就位 | ✅ 完成 |
| P1 | Protocol | 定义通信协议 | 协议可序列化往返 | ✅ 完成 |
| P2 | Memory | 记忆子系统 | 可读写检索 + 压缩 | ✅ 完成（10 子模块待补） |
| P3 | Router | 动态图路由 | 动态路由可计算 | ✅ 完成 |
| P4 | Scheduler | 调度器 | 任务可调度执行 | ✅ 完成 |
| P5 | Planner+Agents | 规划器与 Agent | 群体完成端到端任务 | ✅ 完成（编排器/runtime 集成/E13 待补） |
| P6 | Frontend | AI Native IDE | 可视化可交互 | ✅ 部分完成（攻防视图待补） |
| P7 | Deployment | 部署交付 | 开箱可部署 | 🔲 未开始 |

### 各阶段详情

> 每阶段统一字段：目标 / 输入 / 输出 / 接口 / 测试 / 风险 / 完成标准 / 依赖阶段（目标与完成标准见上表）。

| 阶段 | 输入 | 输出 | 接口 | 测试 | 风险 | 依赖 |
|------|------|------|------|------|------|------|
| P0 | 需求文档（补充.md/开发.md） | 分层目录 / developer 规范 / CI 空壳 | 无 | 结构校验脚本 | 规范不一致导致返工 | 无（起点） |
| P1 | 协议设计（`specs/04`） | `protocol/*.py` 数据类 + 序列化 | Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync | 协议序列化往返测试 | 格式频繁变更导致全局返工 | 需 P0 |
| P2 | `protocol/` 契约 | `agents/memory/` 12 子模块 + 统一接口 | read/write/retrieve(MemoryPacket) | 存取/检索/压缩/同步测试 | 向量索引性能与一致性 | 需 P1 |
| P3 | `protocol/` + `topology/` | `router/` 动态图与低熵路由 | route(task) -> Route | 路由决策与图更新测试 | 动态图一致性 | 需 P2 |
| P4 | `router/` + 任务 | `scheduler/` 队列与策略 | schedule(task) -> execution | 调度/抢占/重试测试 | 死锁/饥饿 | 需 P3 |
| P5 | `scheduler/` + `memory/` | `planner/` + `agents/*` + `tools/runtime/` | plan(goal) / receive()->...->respond() | 规划与 Agent 端到端测试 | 计划质量与 Agent 协作稳定性 | 需 P4 |
| P6 | `backend/` API | `frontend/` 画布/图谱/监控/回放 | REST + WebSocket + SSE | E2E 前端测试 | 实时性与大规模图渲染 | 需 P5 |
| P7 | 全系统 | `infrastructure/delivery/deployment/` docker/k8s/ci + `tooling/scripts/` | make build/deploy | 部署冒烟测试 | 环境差异与密钥管理 | 需 P6 |

### 阶段输出路径

| 阶段 | 输出路径 |
|------|---------|
| P0 | 分层目录骨架 + `developer/` + 全部 AGENT.md |
| P1 | `protocol/*.py` |
| P2 | `agents/memory/`（12 子模块） |
| P3 | `agents/planning/engine/topology/` + `agents/planning/engine/router/` |
| P4 | `agents/planning/engine/scheduler/` |
| P5 | `agents/planning/engine/planner/` + `agents/`（角色 + runtime） |
| P6 | `frontend/` + `backend/` |
| P7 | `infrastructure/delivery/deployment/` + `tooling/scripts/` |

### 当前进度（勾选）

- [x] P0 目录结构（同域聚合分层）与 AGENT.md 体系
- [x] P1 Protocol 实现（cyber.py 8 类型 + memory/graph/scheduler 字段扩展，6 测试）
- [x] P2 Memory 实现（compression/compactor.py + recall/recaller.py，7 测试；其余 10 子模块待补）
- [x] P3 Router 实现（topology 活跃子图 + router Top-K 稀疏路由 + election 异构选举，10 测试）
- [x] P4 Scheduler 实现（端边云三层调度 device/edge/cloud + 多模型兼容层 model_router，13 测试）
- [~] P5 Planner + Agents 实现（11 红蓝紫 Agent + 神经符号闭环已完成 23 测试；planner/orchestrator/workflow/eventbus 编排器待补；B3 runtime 集成待补；E13 e2e 测试待补）
- [~] P6 Frontend 实现（5 视图占位 + Chat 联调已完成；攻防视图 G1-G3 + 后端攻防端点 F 待补）
- [ ] P7 Deployment 实现

### 赛事作品对齐（XH-202631 荣耀·超长程群体智能）

> 赛事作品以 AegisOS 为底座，落地「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」。总体方案见 `plans/14`，可执行任务清单见 `plans/15`。

| roadmap 阶段 | 赛事作品扩展 |
|---------|------------|
| P1 Protocol | 新增 `protocol/cyber.py` 攻防类型（Asset/AttackChain/Alert/DefenseAction/...） |
| P2 Memory | 12 子模块 + 超长程压缩/唤醒（ATT&CK/CVE/向量/情景） |
| P3 Router | 低熵稀疏路由（Top-K，非全广播）+ 动态异构选举 |
| P4 Scheduler | 调度 + 端边云卸载（云大模型/端小模型） |
| P5 Planner+Agents | 红蓝紫 Agent 角色 + 神经-符号协同推理闭环 |
| P6 Frontend | 5 视图（攻击链 DAG/防御看板/时序回放）+ 后端攻防端点 |
| P7 Deployment | Docker 沙箱靶场 + Neo4j/Qdrant + 3 场景演示 + 5 维度评测 |

- 截止：2026-09-15 提交；增量交付，每阶段可演示；优先跑通场景 1（网络防御）。

---

## 🔄 最近变更

| 日期 | 变更 | 提交 |
|------|------|------|
| 2026-07-06 | B3 记忆接入 runtime（4 存储 + MemoryStore 闭环，+26 测试）+ E13 场景 1 端到端（+5 测试），90 passed | （本次提交） |
| 2026-07-05 | 整合 `developer/roadmap/`（P0-P7 阶段详情 + 进度 + 赛事对齐）到 plan.md 附录 D | （本次提交） |
| 2026-07-05 | 全工程文档对齐实际结构（14 文件，backend 扁平化 + frontend mappers/→lib/） | `0997b6d` |
| 2026-07-05 | 整合 plans/13、14、15 到 plan.md，待完成在前+已完成在后 | （本次提交） |
| 2026-07-04 | 前后端打通：14 Agent 注册 + Chat 联调 + 文档同步 | （见 CHANGELOG） |
| 2026-07-04 | Phase A-E 核心引擎 TDD 实现（55→59 测试） | （见 CHANGELOG） |
| 2026-07-04 | 统一配置体系：settings.py + defaults.yaml + 前端 config + 20 文件接入 | `240f8c0` |
| 2026-07-04 | Agent 框架规范化调研：7 类重复造轮子诊断 + litellm/instructor/LangGraph 替换方案 | （文档 `docs/RESEARCH_AGENT_FRAMEWORK_REFACTOR.md`） |
| 2026-07-04 | 端-边-云三层调度升级：scheduler 2 层→3 层 + 4 规则+降级 + model_router 映射 | （见 CHANGELOG） |
