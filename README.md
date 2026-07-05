<div align="center">

# 🛡️ AegisOS

### Agent Operating System + AI Native IDE

**面向超长程网络攻击防御的动态异构群体智能协同推理引擎**

*荣耀 XH-202631 · 挑战杯揭榜挂帅 · 截止 2026-09-15*

</div>

---

## 📌 这是什么？

AegisOS 是一个**可由 AI Agent 自主开发与运行**的群体智能系统，核心能力：

| 能力 | 说明 |
|------|------|
| 🔀 **动态异构群体智能** | 多角色 Agent 自组织协同，按能力动态选举最优执行节点 |
| 🧠 **超长程记忆** | 上下文压缩 + 记忆唤醒，支持超长任务链不丢上下文 |
| 📡 **低熵稀疏通信** | Top-K 路由（非全广播），最小化 Agent 间通信开销 |
| ☁️ **端边云协同** | 按隐私/延迟约束自动卸载到端侧或云侧模型 |
| 🔴🔵🟣 **红蓝紫攻防** | 11 个攻防 Agent 覆盖侦察→漏洞→利用→检测→响应全链路 |
| 🤖 **AI 自主开发** | 全仓库 78 个 AGENT.md 规范，Agent 按模块边界精准读写 |

---

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────┐
│  frontend/   表现层  React + Vite + Zustand + React Flow  │
├─────────────────────────────────────────────────────────┤
│  backend/    应用层  FastAPI + SQLAlchemy + WebSocket      │
├─────────────────────────────────────────────────────────┤
│  agents/     智能体域  感知 → 规划 → 行动 → 记忆 → 工具     │
├─────────────────────────────────────────────────────────┤
│  protocol/   契约层  Message 信封 + 强类型 Payload（唯一）  │
├─────────────────────────────────────────────────────────┤
│  infrastructure/  基建  Docker 沙箱 · 端边云 · 传输         │
└─────────────────────────────────────────────────────────┘
   observability/  可观测   data/  数据   tooling/  工具链
```

### 智能体域 — 认知架构五层

```
agents/
├── perception/   感知 — context · reasoning · reflection
├── planning/      规划 — topology · router · scheduler · planner · orchestrator
├── action/        行动 — 11 个红蓝紫攻防 Agent（见下表）
├── memory/        记忆 — compression · recall + 10 子模块
└── tools/         工具 — llms（多模型兼容） · prompts · runtime
```

### 攻防 Agent 角色

| 队伍 | Agent | 职责 |
|------|-------|------|
| 🔴 **红队** | `recon` | 网络侦察，发现资产 |
| 🔴 | `vuln_correlator` | 漏洞关联，CVE 匹配 |
| 🔴 | `exploit_planner` | 攻击链规划，输出 DAG |
| 🔴 | `lateral_move` | 横向移动路径规划 |
| 🔵 **蓝队** | `detector` | 入侵检测，事件→告警 |
| 🔵 | `triage` | 告警分诊，去噪 + 优先级 |
| 🔵 | `threat_hunt` | 威胁狩猎，ATT&CK 假设生成 |
| 🔵 | `ir_planner` | 响应计划（含 rollback） |
| 🔵 | `forensics` | 取证分析 |
| 🟣 **紫队** | `critic` | 对抗性校验，红蓝产出反驳 |
| 🟣 | `reviewer` | 一致性审查，最终结论 |

---

## 🚀 快速开始

### 前置条件

- Python 3.12+（项目自带 `.venv/`）
- Node.js 18+（前端开发）
- macOS / Linux

### 启动

```bash
# 1. 安装依赖
.venv/bin/pip install -e ".[dev]"
cd frontend && npm install && cd ..

# 2. 启动后端（http://localhost:8000）
.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端（http://localhost:5173）
cd frontend && npm run dev
```

### 验证

```bash
# 运行测试
.venv/bin/python -m pytest tests/ -v          # 59 passed

# 质量门禁
.venv/bin/ruff format && .venv/bin/ruff check --fix

# API 文档
open http://localhost:8000/docs                # Swagger UI
```

> API 鉴权：所有 `/api/v1/*` 端点需 `X-API-Key: aegis-dev-key` header。

---

## 📊 当前进度

| Phase | 内容 | 状态 | 测试 |
|-------|------|------|------|
| **A** | protocol 攻防类型（cyber.py） | ✅ 完成 | 6 |
| **B** | 超长程记忆压缩 + 唤醒 | ✅ 完成 | 7 |
| **C** | 拓扑 + 低熵路由 + 异构选举 | ✅ 完成 | 10 |
| **D** | 端边云三层调度 + 多模型兼容 | ✅ 完成 | 13 |
| **E** | 11 红蓝紫 Agent + 神经符号闭环 | ✅ 完成 | 23 |
| — | 前后端打通（14 Agent + Chat） | ✅ 完成 | — |
| **B3** | 记忆接入 runtime 认知循环 | 🔲 待做 | — |
| **E13** | 场景 1 端到端测试 | 🔲 待做 | — |
| **F** | 后端攻防 REST 端点 | 🔲 待做 | — |
| **G** | 前端攻防视图（DAG/看板/回放） | 🔲 待做 | — |
| **H** | Docker 沙箱 + Neo4j/Qdrant + 评测 | 🔲 待做 | — |

> 完整 gap 分析见 `/memories/repo/gap-analysis.md`。

---

## 📡 通信协议

所有跨模块通信走 **Message 信封**（非裸 JSON），`protocol/` 是唯一数据契约：

```
Message
├── header:  message_id / parent_id / task_id / sender / receiver
├── payload:  protocol 强类型（Asset / Alert / AttackChain / ...）
└── meta:    priority / ttl / timestamp
```

**8 种事件**：`AgentStart` · `AgentFinish` · `ToolCall` · `ToolFinish` · `Retry` · `Rollback` · `MemoryUpdate` · `GraphUpdate`

**动态路由**：`Task → 活跃子图 → Top-K 稀疏路由 → 异构选举 → 执行 → GraphUpdate`

详见 [`developer/specs/04_PROTOCOL_SPEC.md`](developer/specs/04_PROTOCOL_SPEC.md)。

---

## 📁 项目结构

```
AegisOS/
├── protocol/          # 契约层（Message/Event/Task/Graph/cyber.py）
├── agents/            # 智能体域
│   ├── action/        #   11 个红蓝紫攻防 Agent
│   ├── memory/        #   压缩 + 唤醒 + 10 子模块
│   ├── planning/      #   拓扑/路由/调度/选举
│   ├── perception/    #   推理/反思/神经符号闭环
│   └── tools/         #   多模型兼容层（OpenAI/Anthropic/Local）
├── backend/           # FastAPI 应用层
├── frontend/          # React + Vite 表现层
├── developer/         # 规范层（specs/ + roadmap/）
├── infrastructure/    # 基建（沙箱/端边云/传输）
├── observability/     # 可观测（监控/基准/评测）
├── data/              # 数据（Neo4j/Qdrant 待接入）
├── tests/             # 测试（59 passed）
└── tooling/           # 工具链（gen_readme/gen_ts_types）
```

> 每个大模块的 `AGENT.md` 末尾附有「📋 模块实现详解」段，说明该模块实现了什么功能，详见下方[模块实现文档](#模块实现文档)表。

<details>
<summary>📖 完整目录树（点击展开）</summary>

```
agents/
├── action/
│   ├── recon/  vuln_correlator/  exploit_planner/  lateral_move/
│   ├── detector/  triage/  threat_hunt/  ir_planner/  forensics/
│   └── critic/  reviewer/
├── api/
├── memory/
│   ├── compression/  recall/  working/  episodic/  semantic/
│   └── vector/  archive/  cache/  checkpoint/  reflection/  ...
├── perception/
│   └── context/  reasoning/  reflection/
├── planning/
│   └── engine/  orchestrator/  planner/
└── tools/
    └── llms/  prompts/  runtime/
backend/
└── routers/  services/  repositories/  models/  core/  schemas/  mocks/
frontend/
└── controllers/  services/  lib/  views/  config/
infrastructure/
└── transport/  nodes/(edge·cloud)  delivery/
observability/
└── inspect/  measure/  present/
developer/
└── specs/  roadmap/(P0-P7)/  CHANGELOG.md
```

</details>

---

## 🔧 模块间 API 解耦

每个域通过 `api/` 子包暴露公共接口，跨域调用仅经 `from {domain}.api import ...`：

| 域 | 接口数 | 公共 API |
|----|--------|----------|
| `agents/` | 5 | RuntimeAPI · AgentRegistry · Memory · Planning · EventBus |
| `backend/` | 5 | Session · Task · MemoryGateway · Graph · EventStream |
| `infrastructure/` | 4 | Communication · NodeRegistry · Sync · Deployment |
| `observability/` | 6 | Monitor · Trace · Replay · Benchmark · Evaluation · Visualization |
| `data/` | 2 | Dataset · ModelSchema |
| `tooling/` | 2 | Config · Script |

> 共 **27** 个公共接口，参数/返回值一律使用 `protocol/` 契约类型。

---

## 🤖 AI 自主开发流程

```
读取 AGENT.md（模块边界）→ specs（规范 SSOT）→ roadmap（定位阶段）
→ protocol（契约）+ api（接口）→ 生成代码 → 质量门禁 → 更新文档 → commit
```

**铁律**：Agent 永不扫描整个项目；改动 ≤1 域 / ≤8 文件；AI 代码加 `@aegis-gen` 注释头。

---

## 📚 关键文档

### 规范与计划

| 文档 | 说明 |
|------|------|
| [`AGENT.md`](AGENT.md) | 仓库总规范（最高优先级） |
| [`developer/specs/00_PROJECT_SPEC.md`](developer/specs/00_PROJECT_SPEC.md) | 项目 SSOT |
| [`developer/specs/04_PROTOCOL_SPEC.md`](developer/specs/04_PROTOCOL_SPEC.md) | 通信协议规范 |
| [`developer/specs/05_API_SPEC.md`](developer/specs/05_API_SPEC.md) | API 接口规范 |
| [`developer/specs/11_AI_CODING_SPEC.md`](developer/specs/11_AI_CODING_SPEC.md) | AI 编码规范 |
| [`developer/roadmap/README.md`](developer/roadmap/README.md) | 开发计划 P0-P7 |
| [`developer/specs/plans/15_CYBERDEFENSE_TASKS.md`](developer/specs/plans/15_CYBERDEFENSE_TASKS.md) | 赛事实施任务清单 |
| 各目录 `AGENT.md` | 模块边界与开发规范（共 78 个） |

### 模块实现文档

| 文档 | 说明 |
|------|------|
| [`AGENT.md`](AGENT.md) | **仓库总规范**：全局铁律 + AI 开发流程 + 模块实现总览（10 大模块「是什么、做了什么、子模块有哪些」逐一介绍） |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 架构仪表盘：全 10 域代码文件数/测试数/实现状态一览 |
| [`protocol/AGENT.md`](protocol/AGENT.md) | 契约层 10 个 .py 文件详解 |
| [`agents/AGENT.md`](agents/AGENT.md) | 智能体域五层架构 + 11 Agent 角色表 |
| [`backend/AGENT.md`](backend/AGENT.md) | FastAPI 全链路：10 REST 端点 + SSE/WS + DI |
| [`frontend/AGENT.md`](frontend/AGENT.md) | React+Vite 架构 + ChatView 实现 |
| [`infrastructure/AGENT.md`](infrastructure/AGENT.md) | 基建层 4 API 协议 + 传输/节点/交付计划 |
| [`observability/AGENT.md`](observability/AGENT.md) | 可观测层 6 API 协议 + inspect/measure/present |
| [`data/AGENT.md`](data/AGENT.md) | 数据层 2 API 协议 + SQLite + Neo4j/Qdrant 待接入 |
| [`tooling/AGENT.md`](tooling/AGENT.md) | 3 个可用脚本详解 + 配置文件 |
| [`developer/AGENT.md`](developer/AGENT.md) | 15 个规范文件索引 + roadmap P0-P7 进度 |

> 各域 `AGENT.md` 末尾附「📋 模块实现详解」段（原 `MODULE.md` 内容已合并至此）。

---

## 📜 许可

（待定）
