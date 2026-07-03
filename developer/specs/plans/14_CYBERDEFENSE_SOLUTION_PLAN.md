# 14_CYBERDEFENSE_SOLUTION_PLAN.md — 面向超长程网络攻击防御的动态异构群体智能协同推理引擎 总体方案

> 上游：`00_PROJECT_SPEC.md`、`01_ARCHITECTURE_SPEC.md`、`04_PROTOCOL_SPEC.md`、`05_API_SPEC.md`、`08_AGENT_SPEC.md`、`12_TECH_STACK_SPEC.md`、`plans/13_FRONTEND_BACKEND_PLAN.md`。
> 本文件是赛事作品（荣耀 XH-202631「面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术」）的总体方案 spec，定义智能体域攻防角色、协议类型扩展、动态异构拓扑与低熵路由、超长程记忆压缩/唤醒、端边云调度、3 场景演示脚本，并对齐 roadmap。
> 存放位置：`developer/specs/plans/`（计划类规范独立子目录）。
> 与 `13` 关系：`13` 定义前后端通道与后端↔智能体双向调用；`14` 定义智能体域的攻防能力、协议扩展、基建扩展与赛事落地，复用 `13` 的通道。

---

## 1. 定位与赛事对齐

### 1.1 产品定位

**AegisOS = Agent Operating System**。本赛事作品以 AegisOS 为底座，构建「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」：

- **超长程**：攻击链/防御响应跨数十~数百步、跨小时~天级时序，单次 LLM 上下文无法承载 → 需记忆压缩 + 唤醒 + 分段推理。
- **动态异构**：Agent 群体由不同模型/不同 Prompt/不同能力域的异构单元组成，拓扑随任务动态重组（非静态流水线）。
- **群体智能**：多 Agent 协同（红蓝紫对抗 + 元认知 critique/review），而非单 Agent 串行。
- **深度协同推理**：神经（LLM）+ 符号（ATT&CK/CVE 知识图）闭环，可解释、可回放、可验证。

### 1.2 赛事映射

| 项 | 值 |
|----|-----|
| 赛事 | 挑战杯揭榜挂帅 XH-202631（荣耀终端股份有限公司） |
| 命题 | 面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术 |
| 能力维度 | ①架构 ②动态异构 ③群体协同 ④深度协同推理 ⑤超长程 |
| 评分构成 | 完整性 40 + 应用创新 25 + 技术创新 20 + 性能 15 |
| 截止 | 2026-09-15 提交（今日 2026-07-03，剩 ~2.5 个月） |

### 1.3 核心命题分解

| 命题关键词 | 本方案对应能力 | 落地位置 |
|-----------|---------------|---------|
| 超长程 | 记忆压缩/唤醒、分段 Planner、时序回放 | `agents/memory/`、`agents/planning/engine/planner/`、`observability/inspect/replay/` |
| 动态异构 | 异构 Agent 池 + 动态拓扑选举 + 多模型兼容层 | `agents/`、`agents/planning/engine/topology/`、`agents/tools/llms/` |
| 群体协同 | 红蓝紫对抗 + router 稀疏路由 + critic/reviewer | `agents/planning/engine/router/`、`agents/action/critic/` |
| 深度协同推理 | 神经-符号闭环（LLM ↔ ATT&CK/CVE 图） | `agents/perception/reasoning/`、`data/` 知识图 |

---

## 2. 总体架构（复用 AegisOS 分层）

### 2.1 分层 + 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│ 前端 IDE（React 18/TS）  chat · canvas · graph · monitor · replay   │
│   ↕ REST/WS/SSE（经 backend gateway，契约见 13 §5）                 │
├─────────────────────────────────────────────────────────────────────┤
│ 后端（FastAPI）  gateway→controllers→services→mappers               │
│   ↕ agents.api（正向编排） + agents.api.ports（反向 DI，见 13 §3） │
├─────────────────────────────────────────────────────────────────────┤
│ 智能体域 agents/  ← 本方案核心扩展                                   │
│   perception(reasoning/reflection)                                   │
│   planning(engine[planner/scheduler/router/workflow/eventbus/topology])│
│   action(recon/exploit/...red · detector/triage/...blue · critic/reviewer)│
│   memory(12 子模块：含 ATT&CK/CVE/向量/情景/压缩/唤醒)              │
│   tools(llms[多模型兼容层]/prompts/runtime)                         │
├─────────────────────────────────────────────────────────────────────┤
│ protocol/  ← 攻防类型扩展（cyber.py：AttackChain/DefenseAction/...） │
├─────────────────────────────────────────────────────────────────────┤
│ 基建：infrastructure（Docker 沙箱靶场/gRPC/MQTT） · observability    │
│       data（Neo4j 拓扑+ATT&CK 图/Qdrant 向量/Redis Streams）         │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 8 域映射

| 域 | 现状 | 本方案作用 |
|----|------|-----------|
| `agents/` | 仅 `api/__init__.py`+`ports.py` | **主战场**：红蓝紫角色、router、topology、记忆压缩全在此实现 |
| `protocol/` | 10 模块（message/event/.../sync） | 扩展 `cyber.py` 攻防类型；不破坏现有契约 |
| `backend/` | 骨架（见 13 B0-B6） | 加攻防场景端点（靶场/攻击链/回放） |
| `frontend/` | 骨架（见 13 F0-F5） | 加攻击链可视化、防御看板、时序回放 |
| `infrastructure/` | 骨架 | Docker 沙箱靶场、gRPC/MQTT、端边云调度 |
| `observability/` | 骨架 | replay/benchmark/evaluation |
| `data/` | 骨架 | Neo4j（拓扑+ATT&CK 图）、Qdrant（向量）、Redis Streams |
| `tooling/` | 脚本 | 靶场编排、评测脚本、类型生成 |

---

## 3. 智能体域设计（agents/）— 核心

> 现状 `agents/` 仅有 `api/`，全部角色为待建（对齐 roadmap P5）。角色遵循 `08_AGENT_SPEC.md` 生命周期（init→perceive→plan→act→reflect→respond）。

### 3.1 红队 Agent（攻击链推理）

| 角色 | 目录 | 职责 | 主要输入 | 主要输出 |
|------|------|------|---------|---------|
| recon | `agents/action/recon/` | 资产/服务/端口侦察 | 目标范围 | AssetInventory |
| vuln_correlator | `agents/action/vuln_correlator/` | 漏洞关联（CVE 库 + ATT&CK） | AssetInventory | VulnFinding[] |
| exploit_planner | `agents/action/exploit_planner/` | 利用链规划（DAG） | VulnFinding[] | ExploitPlan |
| lateral_move | `agents/action/lateral_move/` | 横向移动规划 | ExploitPlan + Topology | LateralStep[] |

### 3.2 蓝队 Agent（防御）

| 角色 | 目录 | 职责 | 主要输入 | 主要输出 |
|------|------|------|---------|---------|
| detector | `agents/action/detector/` | 异常/入侵检测 | 事件流 | Alert[] |
| triage | `agents/action/triage/` | 告警分诊/去噪/优先级 | Alert[] | PrioritizedAlert[] |
| threat_hunt | `agents/action/threat_hunt/` | 主动威胁狩猎 | PrioritizedAlert + ATT&CK 图 | HuntHypothesis[] |
| ir_planner | `agents/action/ir_planner/` | 响应规划（隔离/阻断） | HuntHypothesis | ResponsePlan |
| forensics | `agents/action/forensics/` | 取证/根因 | ResponsePlan | ForensicReport |

### 3.3 紫队 / 元认知 Agent（协同）

| 角色 | 目录 | 职责 |
|------|------|------|
| planner | `agents/planning/engine/planner/` | 超长程任务分段（DAG） |
| orchestrator | `agents/planning/engine/` | 群体编排、阶段切换 |
| router | `agents/planning/engine/router/` | 低熵稀疏路由（不全广播） |
| scheduler | `agents/planning/engine/scheduler/` | 调度执行 + 端边云卸载 |
| critic | `agents/action/critic/` | 对抗性批判（红蓝互评） |
| reviewer | `agents/action/reviewer/` | 结果审查 + 一致性校验 |

### 3.4 异构性来源

每个角色可绑定多个**异构实例**（同角色不同模型/Prompt/温度）：
- 模型异构：`agents/tools/llms/` 多模型兼容层（OpenAI 兼容接口，接 GPT/Claude/本地模型/端侧小模型）。
- Prompt 异构：`agents/tools/prompts/` 角色多版本 Prompt。
- 能力异构：同一 `vuln_correlator` 可有「CVE 检索型」「ATT&CK 推理型」两实例，由 router 按任务特征动态选举。

---

## 4. 攻防协议类型设计（protocol/ 扩展）

### 4.1 新增模块 `protocol/cyber.py`

> 遵循 `04_PROTOCOL_SPEC.md`：protocol 是唯一数据契约，攻防类型不另起并行结构。`cyber.py` 与现有 `message.py`/`event.py`/`graph.py` 同级，被 `protocol/__init__.py` 导出。

| 类型 | 字段（节选） | 用途 |
|------|-------------|------|
| `Asset` | id, host, services[], os, exposure | 侦察资产 |
| `VulnFinding` | cve_id, asset_id, cvss, attack_surface | 漏洞关联结果 |
| `AttackStep` | id, technique(ATT&CK id), from_asset, to_asset, success | 攻击链节点 |
| `AttackChain` | id, target, steps[], status | 攻击链（DAG 序列化） |
| `Alert` | id, severity, src, dst, technique, raw | 蓝队告警 |
| `DefenseAction` | id, type(isolate/block/decoy), target, rationale | 防御动作 |
| `ResponsePlan` | id, actions[], confidence, rollback | 响应计划 |
| `ThreatIntel` | technique, tactic, refs[] | ATT&CK/CVE 情报 |

### 4.2 与现有协议的关系

- `AttackChain` 作为 `Task.plan` 的领域载荷，经 `GraphUpdate` 事件回传后端展示（复用 `graph.py`）。
- `AttackStep.technique` 引用 ATT&CK id，与 `data/` 知识图节点对齐。
- 红蓝交互走 `Message` 信封 + `Event` 总线，**不另起并行通信结构**（`11_AI_CODING_SPEC` 禁止跨模块裸 dict）。

---

## 5. 动态异构拓扑 + 低熵通信

### 5.1 拓扑建模（Neo4j）

- 节点：Agent 实例（带 `role`/`model`/`capability`/`load` 属性）。
- 边：可达路由（带 `affinity`/`cost`/`entropy` 权重）。
- 动态性：每次任务由 `topology/` 计算当前活跃子图，`router/` 在子图内稀疏路由。

### 5.2 低熵稀疏路由（核心算法）

> **约束**：禁止低熵全广播（`00_PROJECT_SPEC` 原则 + `11_AI_CODING_SPEC`）。Router 按能力亲和度 + 负载选 Top-K 候选，仅向其稀疏投递，非全量广播。

### 5.3 router 伪代码

```python
def route(message: Message, topology: Graph) -> list[NodeRef]:
    # 1. 能力过滤：只保留具备 message.required_capability 的节点
    candidates = [n for n in topology.nodes
                  if message.required_capability in n.capabilities
                  and n.status == "active"]
    # 2. 亲和度打分（任务类型 × 节点 role 异构实例）
    scored = [(n, affinity(message, n) - load_penalty(n)) for n in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    # 3. Top-K 稀疏选择（K=2~3，非全广播）
    k = min(TOP_K, len(scored))
    return [NodeRef(id=n.id) for n, _ in scored[:k]]
```

### 5.4 异构选举

同一角色多实例时，router 按「任务特征 → 实例能力向量」点积选举：
- 例：`exploit_planner` 有「CVE 检索型」与「ATT&CK 推理型」两实例 → 输入含明确 CVE 走检索型，输入需推理走 ATT&CK 型。

---

## 6. 超长程记忆（agents/memory/ 12 子模块）

### 6.1 攻防场景记忆映射

| memory 子模块 | 攻防用途 |
|--------------|---------|
| `working/` | 当前攻击链/响应步上下文 |
| `episodic/` | 历史攻防回合（可回放） |
| `semantic/` | ATT&CK/CVE 知识（与 `data/` Neo4j 同步） |
| `vector/` | Qdrant 向量检索（相似历史攻击） |
| `compression/` | 长程上下文压缩 |
| `recall/` | 唤醒机制（按需检索历史段） |
| 其余 6 子模块 | 通用（procedural/affective/...） |

### 6.2 压缩与唤醒机制

超长程任务上下文超阈值时触发压缩：保留关键决策点（AttackStep/DefenseAction/critic 结论），丢弃冗余中间态；后续阶段按需从 `recall/` 唤醒压缩段。

### 6.3 压缩/唤醒伪代码

```python
def maybe_compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]:
    if token_estimate(context) <= budget:
        return context
    # 保留：决策点 + 最近 N 步；压缩其余为摘要
    keep = [m for m in context if m.is_decision or m.recent]
    digest = summarize([m for m in context if m not in keep])
    return keep + [MemoryPacket(type="digest", payload=digest)]

def recall(trigger: str, episodic, vector) -> list[MemoryPacket]:
    # 向量召回相似历史段 + 情景关键事件
    return vector.search(trigger, top_k=5) + episodic.key_events(trigger)
```

---

## 7. 神经-符号协同推理

- **神经侧**：LLM 生成假设/规划（recon 假设、exploit 链、hunt 假设）。
- **符号侧**：ATT&CK/CVE 知识图做一致性校验（`critic`/`reviewer` 用图规则反驳不合法链）。
- **闭环**：LLM 出假设 → 符号校验 → 不通过则反馈约束 → LLM 修正 → 再校验，直至一致或预算耗尽。

---

## 8. 端边云调度（edge-cloud adaptive）

### 8.1 策略

- **端侧（小模型）**：低延迟、隐私敏感（本机告警分诊、轻量检测）。
- **云侧（大模型）**：重推理（攻击链规划、威胁狩猎假设）。
- **卸载判定**：按 `task.latency_budget` + `task.privacy` + `model.size` 决策。

### 8.2 调度算法

```python
def schedule(task: Task, models: list[Model]) -> Model:
    if task.privacy == "local" or task.latency_budget < EDGE_THRESHOLD:
        return pick(models, tier="edge")
    return pick(models, tier="cloud", capability=task.required_capability)
```

### 8.3 通信

- 实时事件流：Redis Streams（后端内）+ MQTT（端↔云轻量信令）。
- Agent 间强类型 RPC：gRPC（复用 `protocol/` 序列化）。

---

## 9. 后端（复用 13 + 攻防扩展）

| 新增端点 | → service | 说明 |
|---------|-----------|------|
| POST /api/v1/range/start | range.start | 启动靶场会话 |
| GET /api/v1/range/{id}/topology | range.topology | 靶场网络拓扑 |
| POST /api/v1/range/{id}/red/attack | range.red_attack | 提交红队目标→群体推理攻击链 |
| GET /api/v1/range/{id}/chain | range.chain | 攻击链 DAG |
| GET /api/v1/range/{id}/defense | range.defense | 蓝队响应 + 防御动作 |
| GET /api/v1/threat/attack-techniques | threat.techniques | ATT&CK 图查询 |

> 红蓝编排仍走 `RuntimeAPI.submit(task)`（见 13 §3.1），攻防端点仅是领域入口。

---

## 10. 前端（复用 13 + 攻防扩展）

| 视图 | 攻防扩展 |
|------|---------|
| `chat` | 红蓝对抗对话流 |
| `canvas` | 攻击链 DAG 画布 |
| `graph` | 动态异构群体拓扑 + ATT&CK 图增量渲染 |
| `monitor` | Agent 负载/模型/路由监控 + 防御看板 |
| `replay` | 超长程时序回放（压缩点折叠/展开） |

---

## 11. 基建层

- **Docker 沙箱靶场**（`infrastructure/`）：攻击工具（nmap/metasploit 占位/自定义）**仅限靶场内运行，永不触真实网络**（安全约束）。
- **网络靶场**（cyber range）：虚拟网络 + 蜜罐 + 可重置快照。
- **可观测**：`observability/inspect/replay/` 全链路回放；`benchmark/` 性能基准；`evaluation/` 5 维度评测。

---

## 12. 技术栈表（生产级，完整）

| 层 | 技术 | 版本约束 | 用途 |
|----|------|---------|------|
| 后端 | FastAPI | >=0.110 | REST/WS/SSE |
| 后端 | Uvicorn | >=0.29 | ASGI |
| 后端 | SQLAlchemy + aiosqlite/PostgreSQL | >=2.0 | ORM |
| 消息 | Redis Streams | >=7 | 事件流/可靠投递 |
| 图 | Neo4j | >=5 | 拓扑 + ATT&CK 图 |
| 向量 | Qdrant | >=1.8 | 记忆向量检索 |
| 沙箱 | Docker | — | 靶场隔离 |
| 通信 | gRPC / MQTT | — | RPC / 端边云信令 |
| LLM | OpenAI 兼容多模型层 | — | 云+端混合 |
| 前端 | React 18 / TS 5 / Vite 5 | — | IDE |
| 前端 | Zustand / TanStack Query / React Flow / Tailwind / shadcn | — | 状态/数据/图/UI |

> 完整约束写入 `12_TECH_STACK_SPEC.md`（任务清单 §global constraints 落地）。

---

## 13. 3 场景演示脚本

> 跨领域演示证明引擎对「超长程复杂任务」的通用性（赛事创新分）。

### 场景 1 — 网络防御（核心）
红队对靶场发起多阶段攻击 → 蓝队检测/分诊/狩猎/响应 → 紫队 critique 复盘 → 全程时序回放。

### 场景 2 — 软件工程（长程代码任务）
多 Agent 协同完成跨文件重构：planner 分段 → coder/debugger/reviewer 协同 → 记忆压缩跨越长上下文。

### 场景 3 — 金融投研（长程多源推理）
多源数据检索 → 假设生成 → 符号校验 → 投研报告，展示端边云调度与多模型协同。

---

## 14. roadmap 对齐（2.5 个月 → 2026-09-15）

| roadmap | 内容 | 本方案映射 |
|---------|------|-----------|
| P0 | 初始化（已完成） | 骨架就位 |
| P1 | Protocol | 现有 10 模块 + `cyber.py` 扩展 |
| P2 | Memory | 12 子模块 + 压缩/唤醒 |
| P3 | Router | 低熵稀疏路由 + 异构选举 |
| P4 | Scheduler | 调度 + 端边云卸载 |
| P5 | Planner+Agents | 红蓝紫角色 + 神经-符号闭环 |
| P6 | Frontend | 5 视图 + 攻击链/防御/回放 |
| P7 | Deployment | Docker 靶场 + 开箱部署 |
| —（新增） | 攻防基建 | 靶场、Neo4j/Qdrant、3 场景演示 |

> 详细任务拆解见 `plans/15_CYBERDEFENSE_TASKS.md`。

---

## 15. 赛事评分对齐表

| 评分维度 | 占比 | 本方案产物 |
|---------|------|-----------|
| 完整性 | 40 | 8 域全实现 + 3 场景可演示 + 回放 |
| 应用创新 | 25 | 攻防对抗仿真 + 跨领域 3 场景 |
| 技术创新 | 20 | 动态异构拓扑 + 低熵路由 + 神经-符号闭环 + 记忆压缩唤醒 |
| 性能 | 15 | benchmark + 端边云调度优化 |

---

## 16. 风险与对策

| 风险 | 对策 |
|------|------|
| 超长程上下文爆 | 记忆压缩/唤醒 + 分段 Planner + 回放折叠 |
| 异构模型不可控 | 多模型兼容层抽象 + critic 兜底校验 |
| 全广播低熵违规 | router Top-K 稀疏路由 + CI 校验 |
| 攻防工具外泄 | Docker 沙箱 + 靶场网络隔离 + 不触真实网络 |
| 赛事时间紧 | 按 P1→P7 增量交付，每阶段可演示；先跑通场景 1 |
| 本机无 Python | .venv 为 macOS-only；开发用类 Unix/容器，CI 用 Linux（见 memory） |

---

## 17. 里程碑验收

| 里程碑 | 验收标准 |
|--------|----------|
| M1（P1-P2） | `cyber.py` 类型可序列化往返；记忆压缩单元测试通过 |
| M2（P3-P4） | router 稀疏路由可计算且非全广播；调度可卸载 |
| M3（P5） | 红蓝紫 Agent 端到端跑通场景 1（攻击链→响应→回放） |
| M4（P6） | 5 视图可交互，攻击链 DAG 可视化 + 回放 |
| M5（P7+演示） | 3 场景可演示，benchmark + 5 维度评测报告就绪 |
