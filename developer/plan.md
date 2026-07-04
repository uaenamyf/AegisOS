# plan.md — AegisOS 动态开发计划

> **本文件是项目的「活计划」**，动态维护当前未完成的内容和下一步计划。每次会话开始时阅读此文件了解「现在该做什么」，每次完成任务后更新勾选状态。
>
> 维护规则：
> 1. 每完成一个任务 → 勾选 `[x]` + 在 `developer/CHANGELOG.md` 记录
> 2. 每新增计划项 → 添加到对应 Phase 下，标注优先级（P0 最高）
> 3. 每次会话结束前 → 更新「最近变更」段
> 4. 本文件与 `roadmap/README.md`（阶段总览）互补：roadmap 看宏观阶段，plan.md 看具体待办
>
> 最后更新：2026-07-04 · 55 测试全通过 · 统一配置体系 ✅

---

## 📊 总览

| 维度 | 状态 |
|------|------|
| **当前阶段** | P5 收尾 + P6 部分 + 赛事 Phase F-H 待启动 |
| **测试** | 55 passed（protocol 6 + memory 7 + planning 10 + tools 5 + action 15 + perception 4 + 基础 8） |
| **已完成 Phase** | A ✅ · B(部分) ✅ · C ✅ · D ✅ · E ✅ · 前后端打通 ✅ |
| **待完成 Phase** | B3 · E13 · F · G · H |
| **赛事截止** | 2026-09-15（XH-202631 荣耀·超长程群体智能） |

---

## ✅ 已完成任务（不做不删，留痕）

### Phase A — Protocol 攻防类型 ✅
- [x] A1 `protocol/cyber.py` 8 个攻防 dataclass（Asset/VulnFinding/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel）
- [x] A1 `protocol/__init__.py` 导出 + `04_PROTOCOL_SPEC.md` / `06_SCHEMA_SPEC.md` 登记
- [x] A1 测试 6 个（`tests/protocol/test_cyber.py`）

### Phase B — 超长程记忆 ✅(部分)
- [x] B1 `protocol/memory.py` 扩展 `kind` / `recent` 字段
- [x] B1 `agents/memory/compression/compactor.py` 上下文压缩（4 测试）
- [x] B2 `agents/memory/recall/recaller.py` 记忆唤醒 Top-5（3 测试）

### Phase C — 动态异构拓扑 + 低熵路由 ✅
- [x] C1 `protocol/graph.py` 扩展 `GraphNode.status` 字段
- [x] C1 `agents/planning/engine/topology/topology.py` 活跃子图（2 测试）
- [x] C2 `agents/planning/engine/router/router.py` Top-K=3 稀疏路由（3 测试）
- [x] C3 `agents/planning/engine/router/election.py` 异构选举点积（2 测试）

### Phase D — 调度 + 端边云 ✅
- [x] D1 `agents/planning/engine/scheduler/scheduler.py` 端边云卸载（3 测试）
- [x] D2 `agents/tools/llms/model_router.py` 多模型路由（5 测试）
- [x] D2 `agents/tools/llms/openai_provider.py` / `anthropic_provider.py` / `local_provider.py` Provider 实现

### Phase E — 红蓝紫 Agent ✅
- [x] E1-E11 11 个攻防 Agent 全部实现（15 测试）：
  - 🔴 红队：recon · vuln_correlator · exploit_planner · lateral_move
  - 🔵 蓝队：detector · triage · threat_hunt · ir_planner · forensics
  - 🟣 紫队：critic · reviewer
- [x] E12 `agents/perception/reasoning/neuro_symbolic.py` 神经符号闭环（4 测试）

### 前后端打通 ✅
- [x] `backend/src/composition.py` DI 组合根：14 Agent 注册 + MockRuntime 真实调用分发
- [x] `backend/src/main.py` FastAPI app + CORS + TraceMiddleware + lifespan
- [x] 10 个 REST 端点（health/sessions/tasks/agents/graph/memory/tools/metrics/replay）
- [x] SSE `events.py` + WebSocket `stream.py`
- [x] `backend/src/mappers/` SQLAlchemy async + aiosqlite（SessionEntity/TaskEntity）
- [x] `frontend/src/` React + Vite + Zustand + 36 个 TS 类型
- [x] `frontend/views/chat/ChatView.tsx` 完整实现（Agent 选择 + 消息收发 + 任务轮询）

### 文档体系 ✅
- [x] 根 `MODULE.md` — 10 大模块总览
- [x] 9 个域 `MODULE.md`（protocol/agents/backend/frontend/infrastructure/observability/data/tooling/developer）
- [x] `docs/ARCHITECTURE.md` — 全 10 域实现状态仪表盘
- [x] `README.md` 模块文档索引表
- [x] `CLAUDE.md`（根 + `.claude/`）同步更新

### 统一配置体系 ✅
- [x] `tooling/configs/settings.py` — Python 统一配置加载器（环境变量 > .env > defaults.yaml > 代码默认值）
- [x] `tooling/configs/defaults.yaml` — 全项目默认值 SSOT（backend/frontend/cors/auth/db/log/rate_limit/trace/frontend_env）
- [x] `tooling/configs/.env.example` — 环境变量模板
- [x] `frontend/src/config/index.ts` — 前端统一配置入口（`config` 单例）
- [x] `frontend/.env` — Vite 环境变量
- [x] 后端 5 文件接入 settings（main.py/auth.py/middleware.py/database.py）
- [x] 前端 3 文件接入 config（client.ts/sse.ts/ws.ts）
- [x] 脚本/构建配置接入环境变量（start.sh/Makefile/vite.config.ts/playwright.config.ts）
- [x] 55 测试全通过 + TypeScript 类型检查通过

---

## 🔲 待完成任务（按优先级排序）

### 🔥 P0 — 立即执行（本周）

#### B3 — 记忆接入 runtime 认知循环
> **优先级**：P0 · **预估**：1-2 天 · **阻塞**：E13 端到端测试
- [ ] B3.1 `agents/memory/working/` 工作记忆实现（当前会话上下文存储）
- [ ] B3.2 `agents/memory/episodic/` 情景记忆实现（历史任务经验存储）
- [ ] B3.3 `agents/memory/semantic/` 语义记忆实现（ATT&CK/CVE 知识库）
- [ ] B3.4 `agents/memory/vector/` 向量记忆实现（Qdrant 接入预留）
- [ ] B3.5 编排器调用 compactor + recaller 形成闭环
- [ ] B3.6 测试：记忆读写检索 + 压缩唤醒集成测试

#### E13 — 场景 1 端到端测试
> **优先级**：P0 · **预估**：1 天 · **依赖**：B3 完成
- [ ] E13.1 `tests/e2e/test_scenario1.py` — 红→蓝→紫完整链路
- [ ] E13.2 测试流程：recon → vuln_correlator → exploit_planner → detector → triage → ir_planner → critic → reviewer
- [ ] E13.3 验证 AttackChain → Alert → ResponsePlan → Critique 全链路数据流

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
- [ ] F1 `backend/src/controllers/api/range.py` 靶场管理端点（`/api/v1/range/*`）
- [ ] F2 `backend/src/controllers/api/topology.py` 拓扑端点（`/api/v1/topology`）
- [ ] F3 `backend/src/controllers/api/attack.py` 攻击端点（`/api/v1/attack` · `/api/v1/attack/chain`）
- [ ] F4 `backend/src/controllers/api/defense.py` 防御端点（`/api/v1/defense` · `/api/v1/alerts` · `/api/v1/response`）
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

#### 协议迁移
- [ ] `protocol/*.py` 从 `@dataclass` 迁移到 Pydantic v2（`06 §12` 待办）
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

## 🎯 赛事场景覆盖计划

> 3 个场景需在赛事截止（2026-09-15）前完成演示。详见 `plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`。

| 场景 | 描述 | 依赖 | 状态 |
|------|------|------|------|
| 场景 1 | 网络防御（红→蓝→紫完整链路） | B3 + E13 + 编排器 | 🔲 待做 |
| 场景 2 | 超长程攻击链（多步横向移动） | 场景 1 + H1 靶场 | 🔲 待做 |
| 场景 3 | 端边云协同防御 | 场景 1 + H7 端边云 | 🔲 待做 |

**优先级**：场景 1 > 场景 2 > 场景 3

---

## 📐 评分维度对齐

> 赛事评分 5 维度，对应实现任务。详见 `plans/14` §评分对齐。

| 维度 | 评分点 | 对应任务 | 状态 |
|------|--------|---------|------|
| 准确率 | 攻击链/告警/响应的准确性 | E1-E11 Agent + E13 e2e | ✅ Agent 完成 / 🔲 e2e 待做 |
| 召回率 | 检测覆盖率（漏报率） | detector + threat_hunt | ✅ Agent 完成 / 🔲 评测待做 |
| 延迟 | 端到端响应时间 | H5.3 Benchmark | 🔲 待做 |
| 资源 | CPU/内存/容器开销 | H5.3 Benchmark | 🔲 待做 |
| 鲁棒性 | 对抗样本/异常输入处理 | critic + reviewer + H5.4 | ✅ Agent 完成 / 🔲 评测待做 |

---

## 🔄 最近变更

| 日期 | 变更 | 提交 |
|------|------|------|
| 2026-07-04 | 前后端打通：14 Agent 注册 + Chat 联调 + 文档同步 | （见 CHANGELOG） |
| 2026-07-04 | 创建模块文档体系：MODULE.md + ARCHITECTURE.md | `fadf83c` `e58caa9` `e4851bc` |
| 2026-07-04 | Phase A-E 核心引擎 TDD 实现（55 测试） | （见 CHANGELOG） |
| 2026-07-04 | 统一配置体系：settings.py + defaults.yaml + 前端 config + 20 文件接入 | `240f8c0` |

---

## 📌 维护提醒

1. **每次会话开始**：读本文件了解当前待办 → 读 `roadmap/README.md` 了解宏观阶段
2. **每次完成任务**：勾选 `[x]` → 更新 `CHANGELOG.md` → 更新本文件「最近变更」段
3. **新增计划项**：添加到对应 Phase 下 → 标注优先级（P0/P1/P2/P3）→ 标注预估时间和依赖
4. **阶段完成**：更新 `roadmap/README.md` 进度勾选 + `MODULE.md` 实现状态 + `docs/ARCHITECTURE.md` 仪表盘
5. **本文件路径**：`developer/plan.md`（非 `specs/plans/` 下的赛事计划，后者是 SSOT 不改动）
