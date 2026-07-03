# 15_CYBERDEFENSE_TASKS.md — 赛事作品实施任务清单

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 上游：`plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`（方案 spec）。
> 存放：`developer/specs/plans/`（项目约定覆盖 writing-plans 默认路径）。
> 本机无 Python：`agents/`、`protocol/` 为 Python 域；开发在类 Unix/容器内执行（见 memory `aegisos-windows-no-python`）。前端任务用 node/tsc/vite。

**Goal:** 按 roadmap P1→P7 增量交付「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」，每阶段可演示，2026-09-15 赛事截止前完成 3 场景。

**Architecture:** 复用 AegisOS 8 域分层（见 14 §2）。智能体域 `agents/` 从零构建红蓝紫角色 + router/topology + 记忆压缩；`protocol/` 扩展 `cyber.py` 攻防类型 + 给现有 dataclass 补齐异构路由/记忆压缩所需字段；前后端复用 `13` 通道加攻防端点/视图；基建层加 Docker 靶场 + Neo4j/Qdrant。

**Tech Stack:** FastAPI>=0.110 · Redis>=7 · Neo4j>=5 · Qdrant>=1.8 · Docker · gRPC/MQTT · OpenAI 兼容多模型层 · React18/TS5/Vite5/Zustand/React Flow/Tailwind/shadcn。

## Global Constraints

- `protocol/` 是唯一数据契约；**现有 `protocol/*.py` 为 `@dataclass`（非 Pydantic），`06 §12` 列为向 Pydantic 迁移的待办**——本清单新增类型/字段一律沿用 dataclass 风格匹配同类，不抢先引入 Pydantic；迁移时统一迁移。
- protocol 现有命名约定：id 字段统一 `*_id`（`node_id`/`message_id`/`task_id`）；枚举用驼峰（`NodeKind.Agent`）；`Graph.nodes` 为 `dict[node_id, GraphNode]`（非 list）。
- 跨域调用仅经 `api/` 子包（`from {domain}.api import ...`）；无直接内部 import。
- 跨模块禁裸 dict，用 Message 信封 + protocol 类型。
- **禁低熵全广播**：router 仅 Top-K 稀疏路由；CI 校验非全广播。
- AI 改动 ≤1 域、≤8 文件、行为保持、含测试；AI 代码须 `@aegis-gen` 注释头（date/dev/change，新头叠在旧头之上，不删旧）。
- 攻防工具**仅 Docker 沙箱靶场内**运行，永不触真实网络。
- API 签名变更 = 破坏性（major bump + CHANGELOG + 通知依赖方）。**protocol 字段新增**（B1/C1 会做）须同步 `04_PROTOCOL_SPEC`/`06_SCHEMA` + CHANGELOG。
- 不手改 README 自动生成段；protocol 变更后重跑 `gen:types`。

---

## Scope Note（多子系统）

> 本方案覆盖多个独立子系统（protocol/memory/router/agents/backend/frontend/infra）。按 `writing-plans` 多子系统建议，每个 Phase 可在执行时展开为独立 plan。本文件为**主任务清单**：核心算法任务（B/C）含完整 TDD 代码；其余任务含确切路径 + 接口契约 + 验收命令，执行时按 08_AGENT_SPEC 模式填充。

---

## Phase A — Protocol 攻防类型扩展（P1）

### Task A1：protocol/cyber.py 攻防类型（dataclass）

**Files:**
- Create: `protocol/cyber.py`
- Modify: `protocol/__init__.py`（导出）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`（登记新类型）
- Test: `tests/protocol/test_cyber.py`

**Interfaces:**
- Consumes: `protocol/message.py`（Message 信封）、`protocol/graph.py`（GraphUpdate 载荷）
- Produces: `Asset`/`VulnFinding`/`AttackStep`/`AttackChain`/`Alert`/`DefenseAction`/`ResponsePlan`/`ThreatIntel`（`@dataclass`，id 字段用 `*_id` 约定匹配 `node_id`/`message_id`）

- [ ] **Step 1：写失败测试**

```python
# tests/protocol/test_cyber.py
from protocol.cyber import AttackChain, AttackStep, Asset, VulnFinding, Alert, DefenseAction

def test_attack_chain_holds_steps():
    s = AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1", success=True)
    chain = AttackChain(chain_id="c1", target="h1", steps=[s], status="ongoing")
    assert chain.steps[0].technique == "T1110"
    assert chain.steps[0].success is True
    assert chain.status == "ongoing"

def test_vuln_and_alert_fields():
    v = VulnFinding(finding_id="v1", cve_id="CVE-2024-1", asset_id="h1", cvss=9.8, attack_surface="ssh")
    a = Alert(alert_id="a1", severity="high", src="ext", dst="h1", technique="T1110", raw={})
    d = DefenseAction(action_id="d1", kind="isolate", target="h1", rationale="lateral move")
    assert v.cvss == 9.8 and a.severity == "high" and d.kind == "isolate"
```

- [ ] **Step 2：跑测试确认失败** — `pytest tests/protocol/test_cyber.py -v` → FAIL（模块不存在）
- [ ] **Step 3：实现 `protocol/cyber.py`**（`@dataclass` 风格匹配 `protocol/graph.py`/`memory.py`；字段见 14 §4.1，id 字段用 `*_id`；`AttackStep.technique` 为 ATT&CK id；`Alert.raw: dict = field(default_factory=dict)`；可加 `to_dict`/`from_dict` 匹配 `message.py` 惯例）
- [ ] **Step 4：`protocol/__init__.py` 导出**（加 `from .cyber import Asset, VulnFinding, AttackStep, AttackChain, Alert, DefenseAction, ResponsePlan, ThreatIntel` 并入 `__all__`）
- [ ] **Step 5：登记到 `04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`**（新增 cyber 类型小节）
- [ ] **Step 6：跑测试确认通过** — `pytest tests/protocol/test_cyber.py -v` → PASS
- [ ] **Step 7：提交** — `git add protocol/cyber.py protocol/__init__.py tests/protocol/test_cyber.py developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md && git commit -m "feat(protocol): add cyber attack/defense dataclasses (A1)"`

---

## Phase B — 超长程记忆压缩/唤醒（P2）— CORE

### Task B1：memory/compression 上下文压缩

> 协议变更：现有 `MemoryPacket`（`protocol/memory.py`）无「决策点/最近步」标记，无法表达 14 §6.2 的压缩策略。Step 1 先给 `MemoryPacket` 扩展 `kind:str="normal"` 与 `recent:bool=False` 两字段（dataclass，向后兼容默认值）。

**Files:**
- Create: `agents/memory/compression/__init__.py`
- Create: `agents/memory/compression/compactor.py`
- Modify: `protocol/memory.py`（扩 `kind`/`recent` 字段）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`（登记 MemoryPacket 字段扩展）
- Test: `tests/agents/memory/test_compactor.py`

**Interfaces:**
- Consumes: `protocol/memory.py`（`MemoryPacket`：`working`/`semantic`/`episodic`/`archive`/`embedding`/`summary`/`compression`/`session_id`/`task_id` + 新 `kind`/`recent`）
- Produces: `compress(context, budget) -> list[MemoryPacket]`（保留 `kind=="decision"` 与 `recent==True`；其余折叠为一个 `kind=="digest"` 包，摘要入 `summary`，元数据入 `compression`）

- [ ] **Step 1：扩展 `protocol/memory.py` 的 MemoryPacket**

```python
# protocol/memory.py —— 在现有字段末尾追加（默认值保证向后兼容）
@dataclass
class MemoryPacket:
    # ... 现有字段保持不变 ...
    kind: str = "normal"        # normal | decision | digest
    recent: bool = False       # 是否最近步（压缩时保留）
```

- [ ] **Step 2：写失败测试**

```python
# tests/agents/memory/test_compactor.py
from protocol.memory import MemoryPacket
from agents.memory.compression.compactor import compress

def test_compress_keeps_decision_and_recent_makes_digest():
    ctx = [
        MemoryPacket(task_id="t1", kind="normal", recent=False, summary="noise"),
        MemoryPacket(task_id="t2", kind="decision", recent=False, summary="decide A"),
        MemoryPacket(task_id="t3", kind="normal", recent=True, summary="last step"),
    ]
    out = compress(ctx, budget=1)  # budget=1 触发压缩
    kinds = [m.kind for m in out]
    assert "decision" in kinds            # 决策点保留
    assert any(m.recent for m in out)     # 最近步保留
    assert "digest" in kinds             # 其余折叠为 digest
    digest = next(m for m in out if m.kind == "digest")
    assert digest.compression["count"] == 1   # 仅 t1 被折叠

def test_compress_noop_under_budget():
    ctx = [MemoryPacket(task_id="t1", summary="short")]
    assert compress(ctx, budget=1000) == ctx   # 未超预算原样返回
```

- [ ] **Step 3：跑测试确认失败** — `pytest tests/agents/memory/test_compactor.py -v` → FAIL（模块不存在）
- [ ] **Step 4：实现 compactor.py**

```python
# agents/memory/compression/compactor.py
# @aegis-gen date:2026-07-03 dev:Claude Code change:超长程上下文压缩
from protocol.memory import MemoryPacket

def _token_estimate(ctx: list[MemoryPacket]) -> int:
    return sum(len(str(m.summary)) + len(str(m.working)) + len(str(m.episodic)) for m in ctx) // 4 + 1

def compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]:
    if _token_estimate(context) <= budget:
        return context
    keep = [m for m in context if m.kind == "decision" or m.recent]
    rest = [m for m in context if m not in keep]
    if not rest:
        return keep
    digest = MemoryPacket(
        task_id="digest",
        kind="digest",
        summary=" | ".join((m.summary or m.task_id) for m in rest),
        compression={"count": len(rest), "ids": [m.task_id for m in rest]},
    )
    return keep + [digest]
```

- [ ] **Step 5：登记 `04`/`06` 的 MemoryPacket 字段扩展**
- [ ] **Step 6：跑测试确认通过** — `pytest tests/agents/memory/test_compactor.py -v` → PASS
- [ ] **Step 7：提交** — `git add protocol/memory.py agents/memory/compression/ tests/agents/memory/test_compactor.py developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md && git commit -m "feat(memory): long-context compression + MemoryPacket kind/recent (B1)"`

### Task B2：memory/recall 唤醒

> 协议变更：`MemoryPacket` 已在 B1 扩 `kind`/`recent`；recall 复用 `episodic`/`embedding` 字段。
**Files:** Create `agents/memory/recall/recaller.py` · Test `tests/agents/memory/test_recaller.py`
**Produces:** `recall(trigger, episodic, vector) -> list[MemoryPacket]`（向量 top_k + 情景关键事件；vector 先用 in-memory stub，Qdrant 接入在 H2）
- [ ] 写测试：trigger 命中返回情景关键事件（`kind=="decision"`）+ 向量召回 stub top_k → 失败 → 实现（按 `m.summary` 包含 trigger 召回 + `kind=="decision"` 优先）→ 通过 → 提交 `feat(memory): recall mechanism (B2)`

### Task B3：接入 runtime

**Files:** Modify `agents/tools/runtime/`（在认知循环 perceive→plan 间调 `compress`/`recall`）
**Acceptance:** 单元测试：长上下文注入后运行时 token 估计不超 budget；提交 `feat(memory): wire compression/recall into runtime (B3)`

---

## Phase C — 动态异构拓扑 + 低熵路由（P3）— CORE

### Task C1：topology 活跃子图计算

> 协议变更：现有 `GraphNode`（`protocol/graph.py`）无 `status`，无法表达 active/idle。Step 1 扩 `status:str="active"`（默认值向后兼容）。注意 `Graph.nodes` 为 dict，`NodeKind` 枚举为 `NodeKind.Agent`（驼峰）。

**Files:**
- Create: `agents/planning/engine/topology/topology.py`
- Modify: `protocol/graph.py`（`GraphNode` 扩 `status` 字段）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`
- Test: `tests/agents/planning/test_topology.py`

**Interfaces:**
- Consumes: `protocol/graph.py`（`Graph`/`GraphNode`/`NodeKind`；`Graph.nodes` 为 dict）
- Produces: `active_subgraph(graph, required_capability) -> Graph`（仅 `status=="active"` 且 `required_capability in capabilities` 的节点 + 相关边）

- [ ] **Step 1：扩展 `protocol/graph.py` 的 GraphNode**

```python
# protocol/graph.py —— GraphNode 末尾追加
@dataclass
class GraphNode:
    # ... 现有字段保持不变（node_id/kind/name/capabilities/trust_score/success_rate/latency）...
    status: str = "active"   # active | idle | degraded
```

- [ ] **Step 2：写失败测试**

```python
# tests/agents/planning/test_topology.py
from protocol.graph import Graph, GraphNode, NodeKind
from agents.planning.engine.topology.topology import active_subgraph

def test_active_subgraph_filters_capability_and_status():
    a = GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="active")
    b = GraphNode(node_id="b", kind=NodeKind.Agent, capabilities=["recon"], status="idle")
    c = GraphNode(node_id="c", kind=NodeKind.Agent, capabilities=["hunt"], status="active")
    g = Graph()
    for n in (a, b, c):
        g.add_node(n)
    sub = active_subgraph(g, required_capability="recon")
    assert list(sub.nodes.keys()) == ["a"]   # 仅 active + 具备 recon 能力
```

- [ ] **Step 3：跑确认失败** — `pytest tests/agents/planning/test_topology.py -v` → FAIL
- [ ] **Step 4：实现 topology.py**

```python
# agents/planning/engine/topology/topology.py
# @aegis-gen date:2026-07-03 dev:Claude Code change:活跃子图计算
from protocol.graph import Graph, GraphNode

def active_subgraph(graph: Graph, required_capability: str) -> Graph:
    sub = Graph()
    for n in graph.nodes.values():
        if getattr(n, "status", "active") == "active" and required_capability in n.capabilities:
            sub.add_node(n)
    return sub
```

- [ ] **Step 5：登记 `04`/`06` 的 GraphNode.status 扩展**
- [ ] **Step 6：跑确认通过** — `pytest tests/agents/planning/test_topology.py -v` → PASS
- [ ] **Step 7：提交** — `git add protocol/graph.py agents/planning/engine/topology/topology.py tests/agents/planning/test_topology.py developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md && git commit -m "feat(planning): active subgraph computation + GraphNode.status (C1)"`

### Task C2：router 低熵稀疏路由

> `Message`（`protocol/message.py`）无 `required_capability` 字段——`route()` 改为显式参数 `required_capability`（不扩 Message）。返回 `NodeRef(node_id=..., node_type=...)`（匹配 `message.py` 的 NodeRef 构造）。

**Files:**
- Create: `agents/planning/engine/router/router.py`
- Test: `tests/agents/planning/test_router.py`

**Interfaces:**
- Consumes: C1 `active_subgraph`、`protocol/message.py`（`Message`/`NodeRef`）、`protocol/graph.py`（`Graph`；`Graph.nodes` 为 dict）
- Produces: `route(message, topology, required_capability) -> list[NodeRef]`（Top-K，`TOP_K=3`，非全广播）

- [ ] **Step 1：写失败测试**

```python
# tests/agents/planning/test_router.py
from protocol.message import Message, NodeRef
from protocol.graph import Graph, GraphNode, NodeKind
from agents.planning.engine.router.router import route, TOP_K

def test_route_is_sparse_not_broadcast():
    g = Graph()
    for i in range(10):
        g.add_node(GraphNode(node_id=f"n{i}", kind=NodeKind.Agent,
                             capabilities=["recon"], status="active"))
    msg = Message()
    targets = route(msg, g, required_capability="recon")
    assert 0 < len(targets) <= TOP_K          # 非空且非全广播
    assert len(targets) < len(g.nodes)         # 严格少于总数（低熵）
    assert all(isinstance(t, NodeRef) for t in targets)

def test_route_skips_idle_and_wrong_capability():
    g = Graph()
    g.add_node(GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="idle"))
    g.add_node(GraphNode(node_id="b", kind=NodeKind.Agent, capabilities=["hunt"], status="active"))
    assert route(Message(), g, required_capability="recon") == []
```

- [ ] **Step 2：跑确认失败** — `pytest tests/agents/planning/test_router.py -v` → FAIL
- [ ] **Step 3：实现 router.py**（见 14 §5.3：能力过滤 → 亲和度-load 打分 → Top-K）

```python
# agents/planning/engine/router/router.py
# @aegis-gen date:2026-07-03 dev:Claude Code change:低熵稀疏路由 Top-K
from protocol.message import NodeRef

TOP_K = 3

def route(message, topology, required_capability: str) -> list[NodeRef]:
    candidates = [n for n in topology.nodes.values()
                  if required_capability in n.capabilities
                  and getattr(n, "status", "active") == "active"]
    scored = sorted(candidates,
                    key=lambda n: _affinity(message, n) - _load_penalty(n),
                    reverse=True)
    k = min(TOP_K, len(scored))
    return [NodeRef(node_id=n.node_id, node_type=n.kind.value) for n in scored[:k]]

def _affinity(message, n) -> float:
    return getattr(n, "success_rate", 1.0)

def _load_penalty(n) -> float:
    return getattr(n, "latency", 0.0)
```

- [ ] **Step 4：跑确认通过** — `pytest tests/agents/planning/test_router.py -v` → PASS
- [ ] **Step 5：提交** — `git add agents/planning/engine/router/router.py tests/agents/planning/test_router.py && git commit -m "feat(planning): low-entropy sparse router (C2)"`

### Task C3：异构选举

**Files:** Create `agents/planning/engine/router/election.py` · Test `tests/agents/planning/test_election.py`
**Interfaces:** Consumes `protocol/graph.py`（`GraphNode.capabilities`）；Produces `elect(message, instances, required_capability) -> NodeRef`（任务特征向量 · 实例能力向量点积最大者）
- [ ] 测试：同角色两异构实例（capabilities 不同）按任务特征选不同实例 → 实现 → 通过 → 提交 `feat(planning): heterogeneous election (C3)`

### Task C4：全广播违规 CI 校验

**Files:** Create `tooling/scripts/check_no_broadcast.py` · Test
**Acceptance:** 静态扫描 `route(` 调用点，断言返回数 ≤ `TOP_K`；CI 中 `python3 tooling/scripts/check_no_broadcast.py` 退出码 0；提交 `chore: CI guard against full-broadcast routing (C4)`

---

## Phase D — 调度 + 端边云（P4）

### Task D1：scheduler 卸载判定
**Files:** Create `agents/planning/engine/scheduler/scheduler.py` · Test
**Produces:** `schedule(task, models) -> Model`（见 14 §8.2：`task` 的 `privacy`/`latency_budget` + `model.size` 决策端 vs 云）
- [ ] 测试：privacy=local → 端模型；latency 大且无隐私约束 → 云模型 → 实现 → 通过 → 提交 `feat(planning): edge-cloud scheduling (D1)`

> 注：`Task`（`protocol/scheduler.py`）字段需含 `privacy`/`latency_budget`；若缺，D1 Step 1 扩之（同 B1/C1 的协议变更流程）。

### Task D2：多模型兼容层
**Files:** Create `agents/tools/llms/model_router.py`（OpenAI 兼容接口抽象，按 D1 结果选实例）
- [ ] 单元测试 mock 两个模型按调度结果返回；提交 `feat(tools): multi-model compatibility layer (D2)`

---

## Phase E — 红蓝紫 Agent 角色（P5）

> 每角色一个目录，遵循 `08_AGENT_SPEC` 生命周期（init→perceive→plan→act→reflect→respond）。每任务：建目录 + `AGENT.md` + runtime stub + 单元测试（输入→输出契约）+ 提交。

| Task | 目录 | Consumes→Produces | 验收 |
|------|------|-------------------|------|
| E1 recon | `agents/action/recon/` | range target → `Asset[]` | 测试：给定目标范围返回 Asset[]；提交 |
| E2 vuln_correlator | `agents/action/vuln_correlator/` | `Asset[]` → `VulnFinding[]` | 关联 CVE；提交 |
| E3 exploit_planner | `agents/action/exploit_planner/` | `VulnFinding[]` → `ExploitPlan` | 输出 DAG；提交 |
| E4 lateral_move | `agents/action/lateral_move/` | `ExploitPlan`+Topology → `LateralStep[]` | 提交 |
| E5 detector | `agents/action/detector/` | 事件流 → `Alert[]` | 提交 |
| E6 triage | `agents/action/triage/` | `Alert[]` → `PrioritizedAlert[]` | 去噪+优先级；提交 |
| E7 threat_hunt | `agents/action/threat_hunt/` | `PrioritizedAlert`+ATT&CK → `HuntHypothesis[]` | 提交 |
| E8 ir_planner | `agents/action/ir_planner/` | `HuntHypothesis` → `ResponsePlan` | 含 rollback；提交 |
| E9 forensics | `agents/action/forensics/` | `ResponsePlan` → `ForensicReport` | 提交 |
| E10 critic | `agents/action/critic/` | 红蓝产出 → 反驳/校验 | 提交 |
| E11 reviewer | `agents/action/reviewer/` | 产出 → 一致性结论 | 提交 |

### Task E12：神经-符号闭环集成
**Files:** Create `agents/perception/reasoning/neuro_symbolic.py`（LLM 假设 → ATT&CK 图校验 → 反馈约束 → 修正，见 14 §7）
- [ ] 测试：不合法攻击链被符号侧驳回并触发修正；提交 `feat(perception): neuro-symbolic loop (E12)`

### Task E13：场景 1 端到端
**Files:** `tests/e2e/test_scenario1_defense.py`
- [ ] 集成测试：红队攻击 → 蓝队响应 → 紫队 critique → GraphUpdate 可回放；提交 `test(e2e): scenario1 defense end-to-end (E13)`

---

## Phase F — 后端攻防端点（P6 backend）

> 复用 13 B0-B6 通道。每端点：controller（校验+调 service）→ service（调 `agents.api`）→ 测试。

| Task | 端点 | → service | 验收 |
|------|------|-----------|------|
| F1 | POST /api/v1/range/start · GET /range/{id}/topology · POST /range/{id}/red/attack · GET /range/{id}/chain · GET /range/{id}/defense | range.* | 契约测试通过；提交 |
| F2 | GET /api/v1/threat/attack-techniques | threat.techniques | ATT&CK 图查询；提交 |

> 编排仍走 `RuntimeAPI.submit(task)`（13 §3.1）；端点仅领域入口。

---

## Phase G — 前端攻防视图（P6 frontend）

> 复用 13 F0-F5。前端本地类型用 `@/protocol/frontend-types`，协议类型用 `@/protocol/types`（已规范）。

| Task | 视图 | 内容 | 验收 |
|------|------|------|------|
| G1 | `views/canvas/` | 攻击链 DAG（React Flow） | 渲染 AttackChain；`tsc -b && vite build` 通过；提交 |
| G2 | `views/monitor/` | Agent 负载/模型/路由 + 防御看板 | 订阅 GraphUpdate；提交 |
| G3 | `views/replay/` | 时序回放（压缩点折叠/展开） | 回放 AttackChain 时序；提交 |

- [ ] 每任务：组件 + 类型（`@/protocol/frontend-types`）+ store + 单元测试（Vitest）+ `tsc -b && vite build` 通过 + 提交

---

## Phase H — 基建 + 演示（P7）

### Task H1：Docker 沙箱靶场
**Files:** `infrastructure/sandbox/`（Dockerfile + 编排；攻击工具仅靶场内）
**Acceptance:** 靶场可启停、可重置快照、隔离网络（不触真实网络）；提交 `feat(infra): docker sandboxed cyber range (H1)`

### Task H2：Neo4j + Qdrant 接入
**Files:** `data/graph/neo4j_store.py`（拓扑+ATT&CK 图）、`data/vector/qdrant_store.py`（替换 B2 vector stub）
**Acceptance:** C1 topology 从 Neo4j 加载；B2 recall 走 Qdrant；提交 `feat(data): neo4j+qdrant backends (H2)`

### Task H3：场景 2 软件工程
**Files:** `tests/e2e/test_scenario2_software.py`（多 Agent 跨文件重构 + 记忆压缩跨长上下文）
- [ ] 提交 `test(e2e): scenario2 software engineering (H3)`

### Task H4：场景 3 金融投研
**Files:** `tests/e2e/test_scenario3_finance.py`（多源检索 → 假设 → 符号校验 → 报告）
- [ ] 提交 `test(e2e): scenario3 investment research (H4)`

### Task H5：benchmark + 5 维度评测
**Files:** `observability/benchmark/`（延迟/吞吐/路由稀疏度）、`observability/evaluation/`（5 维度评分）
**Acceptance:** 生成评测报告；提交 `feat(observability): benchmark + 5-dim evaluation (H5)`

---

## Self-Review 摘要

- **Spec coverage**：14 §3 角色 → E1-E11；§4 protocol → A1；§5 拓扑/路由 → C1-C4；§6 记忆 → B1-B3；§7 神经-符号 → E12；§8 端边云 → D1-D2；§9 后端 → F；§10 前端 → G；§11 基建 → H1-H2；§13 三场景 → E13/H3/H4；§15 评分 → H5。✅ 全覆盖。
- **Placeholder scan**：核心算法任务（A1/B1/C1/C2）含完整测试 + 实现代码，且已对齐真实 protocol dataclass 类型；其余任务含确切路径 + 接口契约 + 验收命令（多子系统拆分，见 Scope Note，执行时按 08_AGENT_SPEC 填充）。
- **Type consistency**（已据真实 `protocol/*.py` 校正）：
  - `MemoryPacket`（B1）：扩 `kind`/`recent`；digest 用真实 `summary`/`compression` 字段。✅
  - `GraphNode`（C1）：用 `node_id`/`NodeKind.Agent`/`status`（新扩）；`Graph.nodes` 按 dict 遍历。✅
  - `route`（C2）：`required_capability` 为显式参数（不扩 `Message`）；返回 `NodeRef(node_id, node_type)` 匹配 `message.py`。✅
  - `Asset`/`AttackStep`/`AttackChain` 等（A1）：id 字段用 `*_id` 约定匹配 `node_id`/`message_id`。✅
  - 协议字段扩展（MemoryPacket.kind/recent、GraphNode.status、Task.privacy/latency_budget）均按 Global Constraints 标注 04/06 + CHANGELOG 同步。✅

---

## Execution Handoff

**Plan complete and saved to `developer/specs/plans/15_CYBERDEFENSE_TASKS.md`. Two execution options:**

1. **Subagent-Driven（推荐）** — 按 Phase 派发 fresh subagent 逐 Task 执行，两阶段 review，快速迭代。REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`。
2. **Inline Execution** — 本会话内按 `superpowers:executing-plans` 批量执行 + checkpoint review。

> 建议 Phase A→B→C 优先（契约 + 核心算法），其余 Phase 可并行。
