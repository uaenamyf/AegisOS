# 智能体域 Phase A-E 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 上游：`developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`（方案 spec）+ `developer/specs/plans/15_CYBERDEFENSE_TASKS.md`（原始任务清单）。
> 存放：`docs/superpowers/plans/`（writing-plans 默认路径）。
> 本机环境：macOS + Python venv（可直接 pytest/mypy）。

**Goal:** 从零构建 AegisOS 智能体域核心算法层（protocol 攻防类型扩展 + 超长程记忆压缩/唤醒 + 动态异构拓扑/低熵路由 + 端边云调度 + 多模型兼容层 + 红蓝紫 Agent 角色），每阶段可独立测试，为赛事核心评分项（技术创新 20 + 性能 15 = 35 分）奠定可运行基础。

**Architecture:** 复用 AegisOS 8 域分层。`protocol/` 扩展 `cyber.py` 攻防类型 + 给现有 dataclass 补齐压缩/拓扑所需字段；`aegisos_agents/memory/` 实现上下文压缩与唤醒；`aegisos_agents/planning/engine/` 实现活跃子图计算、低熵稀疏路由、异构选举、端边云调度；`aegisos_agents/tools/llms/` 实现多模型兼容层（OpenAI/Anthropic/本地/Mock）；`aegisos_agents/action/` 实现红蓝紫 11 个角色 + 神经-符号闭环。全程 TDD。

**Tech Stack:** Python 3.11+ / pytest / ruff / mypy / httpx（LLM 调用）/ 无外部依赖（Phase A-E 不需要 Redis/Neo4j/Qdrant，纯算法层）。

## Global Constraints

- `protocol/` 是唯一数据契约；现有 `protocol/*.py` 为 `@dataclass`（非 Pydantic），`06_S12` 列为向 Pydantic 迁移待办。本计划新增类型/字段一律沿用 dataclass 风格匹配同类，不抢先引入 Pydantic。
- protocol 现有命名约定：id 字段统一 `*_id`（`node_id`/`message_id`/`task_id`）；枚举用驼峰（`NodeKind.Agent`）；`Graph.nodes` 为 `dict[node_id, GraphNode]`（非 list）。
- 跨域调用仅经 `api/` 子包（`from {domain}.api import ...`）；无直接内部 import。
- 跨模块禁裸 dict，用 Message 信封 + protocol 类型。
- 禁低熵全广播：router 仅 Top-K 稀疏路由；CI 校验非全广播。
- AI 改动 不超过 1 域、不超过 8 文件、行为保持、含测试；首次创建文件写文件说明 + date + dev（§10.1），增改函数/方法/接口写 date + dev + changelog + 代码注释（§10.2）。
- API 签名变更 = 破坏性（major bump + CHANGELOG + 通知依赖方）。protocol 字段新增须同步 `04_PROTOCOL_SPEC`/`06_SCHEMA` + CHANGELOG。
- 不手改 README 自动生成段；protocol 变更后重跑 `gen:types`。
- LLM 兼容层设计为多方案：本地部署 + OpenAI API + Anthropic API + Mock stub，通过统一 `ModelProvider` 接口切换。
- 开发环境：macOS + Python venv，直接使用 `pytest`/`ruff`/`mypy` 命令。

## File Structure

### 新建文件

```
protocol/
  cyber.py                          # A1: 攻防 8 类型

aegisos_agents/
  memory/
    compression/
      __init__.py                   # B1
      compactor.py                   # B1: 上下文压缩
    recall/
      __init__.py                   # B2
      recaller.py                    # B2: 唤醒
  planning/
    engine/
      topology/
        __init__.py                  # C1
        topology.py                  # C1: 活跃子图
      router/
        __init__.py                  # C2
        router.py                    # C2: 低熵稀疏路由
        election.py                  # C3: 异构选举
      scheduler/
        __init__.py                  # D1
        scheduler.py                 # D1: 端边云调度
  tools/
    llms/
      __init__.py                    # D2
      base.py                        # D2: ModelProvider 抽象
      openai_provider.py             # D2: OpenAI 适配
      anthropic_provider.py          # D2: Anthropic 适配
      local_provider.py              # D2: 本地模型适配
      mock_provider.py               # D2: Mock stub
      model_router.py                # D2: 多模型路由
  action/
    recon/
      __init__.py                    # E1
      agent.py                       # E1: 侦察
    vuln_correlator/
      __init__.py                    # E2
      agent.py                       # E2: 漏洞关联
    exploit_planner/
      __init__.py                    # E3
      agent.py                       # E3: 利用链规划
    lateral_move/
      __init__.py                    # E4
      agent.py                       # E4: 横向移动
    detector/
      __init__.py                    # E5
      agent.py                       # E5: 入侵检测
    triage/
      __init__.py                    # E6
      agent.py                       # E6: 告警分诊
    threat_hunt/
      __init__.py                    # E7
      agent.py                       # E7: 威胁狩猎
    ir_planner/
      __init__.py                    # E8
      agent.py                       # E8: 响应规划
    forensics/
      __init__.py                    # E9
      agent.py                       # E9: 取证
    critic/
      __init__.py                    # E10
      agent.py                       # E10: 对抗性批判
    reviewer/
      __init__.py                    # E11
      agent.py                       # E11: 一致性审查
  perception/
    reasoning/
      __init__.py                    # E12
      neuro_symbolic.py               # E12: 神经-符号闭环

tests/
  protocol/
    __init__.py
    test_cyber.py                    # A1
  aegisos_agents/
    __init__.py
    memory/
      __init__.py
      test_compactor.py              # B1
      test_recaller.py               # B2
    planning/
      __init__.py
      test_topology.py               # C1
      test_router.py                 # C2
      test_election.py               # C3
      test_scheduler.py              # D1
    tools/
      __init__.py
      test_model_router.py           # D2
    action/
      __init__.py
      test_recon.py                  # E1
      test_vuln_correlator.py        # E2
      test_exploit_planner.py        # E3
      test_lateral_move.py           # E4
      test_detector.py               # E5
      test_triage.py                 # E6
      test_threat_hunt.py            # E7
      test_ir_planner.py             # E8
      test_forensics.py              # E9
      test_critic.py                 # E10
      test_reviewer.py               # E11
    perception/
      __init__.py
      test_neuro_symbolic.py         # E12
```

### 修改文件

```
protocol/
  memory.py          # B1: MemoryPacket 扩 kind/recent 字段
  graph.py           # C1: GraphNode 扩 status 字段
  scheduler.py       # D1: Task 扩 privacy/latency_budget 字段
  __init__.py        # A1: 导出 cyber 类型
aegisos_agents/
  tools/
    runtime/         # B3: 接入压缩/唤醒到认知循环（待 runtime 目录有代码后）
  api/
    __init__.py      # E-phase 后: 如需暴露新接口
developer/specs/
  04_PROTOCOL_SPEC.md  # A1/B1/C1/D1: 登记新类型/字段
  06_SCHEMA_SPEC.md     # A1/B1/C1/D1: 同步 schema
```

---

## Phase A - Protocol 攻防类型扩展（P1）

### Task A1: protocol/cyber.py 攻防类型（dataclass）

**Files:**
- Create: `protocol/cyber.py`
- Modify: `protocol/__init__.py`
- Modify: `developer/specs/04_PROTOCOL_SPEC.md`
- Modify: `developer/specs/06_SCHEMA_SPEC.md`
- Test: `tests/protocol/test_cyber.py`

**Interfaces:**
- Consumes: `protocol/message.py`（`NodeRef`）、`protocol/graph.py`（`NodeKind`/`Graph`）
- Produces: `Asset`/`VulnFinding`/`AttackStep`/`AttackChain`/`Alert`/`DefenseAction`/`ResponsePlan`/`ThreatIntel`（`@dataclass`，id 字段用 `*_id` 约定）

- [ ] **Step 1: 写失败测试**

```python
# tests/protocol/test_cyber.py
from protocol.cyber import (
    Asset, VulnFinding, AttackStep, AttackChain,
    Alert, DefenseAction, ResponsePlan, ThreatIntel,
)


def test_asset_fields():
    a = Asset(asset_id="h1", host="10.0.0.1", services=["ssh:22", "http:80"], os="linux")
    assert a.asset_id == "h1"
    assert a.services == ["ssh:22", "http:80"]
    assert a.os == "linux"


def test_vuln_finding_fields():
    v = VulnFinding(
        finding_id="v1", cve_id="CVE-2024-1", asset_id="h1",
        cvss=9.8, attack_surface="ssh",
    )
    assert v.cvss == 9.8
    assert v.attack_surface == "ssh"


def test_attack_step_and_chain():
    s = AttackStep(
        step_id="s1", technique="T1110",
        from_asset="ext", to_asset="h1", success=True,
    )
    chain = AttackChain(chain_id="c1", target="h1", steps=[s], status="ongoing")
    assert chain.steps[0].technique == "T1110"
    assert chain.steps[0].success is True
    assert chain.status == "ongoing"


def test_alert_and_defense_action():
    a = Alert(
        alert_id="a1", severity="high", src="ext", dst="h1",
        technique="T1110", raw={"port": 22},
    )
    d = DefenseAction(
        action_id="d1", kind="isolate", target="h1", rationale="lateral move",
    )
    assert a.severity == "high"
    assert a.raw == {"port": 22}
    assert d.kind == "isolate"


def test_response_plan_and_threat_intel():
    rp = ResponsePlan(
        plan_id="rp1", actions=[], confidence=0.85, rollback={"enabled": False},
    )
    ti = ThreatIntel(
        technique="T1110", tactic="credential-access", refs=["CVE-2024-1"],
    )
    assert rp.confidence == 0.85
    assert ti.tactic == "credential-access"
    assert ti.refs == ["CVE-2024-1"]


def test_attack_chain_to_dict_roundtrip():
    s = AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1")
    chain = AttackChain(chain_id="c1", target="h1", steps=[s], status="ongoing")
    d = chain.to_dict()
    assert d["chain_id"] == "c1"
    restored = AttackChain.from_dict(d)
    assert restored.steps[0].technique == "T1110"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/protocol/test_cyber.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'protocol.cyber'`

- [ ] **Step 3: 实现 `protocol/cyber.py`**

```python
# protocol/cyber.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 新建攻防协议类型
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Asset:
    asset_id: str
    host: str = ""
    services: list = field(default_factory=list)
    os: str = ""
    exposure: str = "external"  # external | internal | isolated


@dataclass
class VulnFinding:
    finding_id: str
    cve_id: str = ""
    asset_id: str = ""
    cvss: float = 0.0
    attack_surface: str = ""


@dataclass
class AttackStep:
    step_id: str
    technique: str = ""
    from_asset: str = ""
    to_asset: str = ""
    success: bool = False


@dataclass
class AttackChain:
    chain_id: str
    target: str = ""
    steps: list = field(default_factory=list)
    status: str = "planned"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttackChain":
        steps_data = data.pop("steps", [])
        steps = [AttackStep(**s) for s in steps_data]
        return cls(steps=steps, **data)


@dataclass
class Alert:
    alert_id: str
    severity: str = "low"
    src: str = ""
    dst: str = ""
    technique: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class DefenseAction:
    action_id: str
    kind: str = "monitor"
    target: str = ""
    rationale: str = ""


@dataclass
class ResponsePlan:
    plan_id: str
    actions: list = field(default_factory=list)
    confidence: float = 0.0
    rollback: dict = field(default_factory=dict)


@dataclass
class ThreatIntel:
    technique: str = ""
    tactic: str = ""
    refs: list = field(default_factory=list)
```

- [ ] **Step 4: `protocol/__init__.py` 导出**

在 `protocol/__init__.py` 末尾（`__all__` 之前）加导入：

```python
from .cyber import (
    Asset, VulnFinding, AttackStep, AttackChain,
    Alert, DefenseAction, ResponsePlan, ThreatIntel,
)
```

在 `__all__` 列表末尾追加：

```python
    "Asset", "VulnFinding", "AttackStep", "AttackChain",
    "Alert", "DefenseAction", "ResponsePlan", "ThreatIntel",
```

- [ ] **Step 5: 登记到 `04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`**

在 `04_PROTOCOL_SPEC.md` 新增「cyber 攻防类型」小节，列出 8 个类型及其字段。
在 `06_SCHEMA_SPEC.md` 新增对应 schema 登记表。

- [ ] **Step 6: 跑测试确认通过**

Run: `pytest tests/protocol/test_cyber.py -v`
Expected: 6 passed

- [ ] **Step 7: 提交**

```bash
git add protocol/cyber.py protocol/__init__.py tests/protocol/test_cyber.py \
  developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md
git commit -m "feat(protocol): add cyber attack/defense dataclasses (A1)"
```

---

## Phase B - 超长程记忆压缩/唤醒（P2）CORE

### Task B1: memory/compression 上下文压缩

> 协议变更：现有 `MemoryPacket`（`protocol/memory.py`）无「决策点/最近步」标记，无法表达压缩策略。Step 1 先给 `MemoryPacket` 扩展 `kind:str="normal"` 与 `recent:bool=False` 两字段（dataclass，向后兼容默认值）。

**Files:**
- Create: `aegisos_agents/memory/compression/__init__.py`
- Create: `aegisos_agents/memory/compression/compactor.py`
- Modify: `protocol/memory.py`（扩 `kind`/`recent` 字段）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`
- Test: `tests/aegisos_agents/memory/test_compactor.py`

**Interfaces:**
- Consumes: `protocol/memory.py`（`MemoryPacket`：`working`/`semantic`/`episodic`/`archive`/`embedding`/`summary`/`compression`/`session_id`/`task_id` + 新 `kind`/`recent`）
- Produces: `compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]`（保留 `kind=="decision"` 与 `recent==True`；其余折叠为一个 `kind=="digest"` 包，摘要入 `summary`，元数据入 `compression`）

- [ ] **Step 1: 扩展 `protocol/memory.py` 的 MemoryPacket**

在 `protocol/memory.py` 的 `MemoryPacket` dataclass 末尾追加两个字段：

```python
@dataclass
class MemoryPacket:
    working: dict = field(default_factory=dict)
    semantic: dict = field(default_factory=dict)
    episodic: dict = field(default_factory=dict)
    archive: dict = field(default_factory=dict)
    embedding: list = field(default_factory=list)
    summary: str = ""
    compression: dict = field(default_factory=dict)
    session_id: str = ""
    task_id: str = ""
    kind: str = "normal"        # normal | decision | digest
    recent: bool = False        # 是否最近步（压缩时保留）
```

- [ ] **Step 2: 写失败测试**

```python
# tests/aegisos_agents/memory/test_compactor.py
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
    assert "decision" in kinds
    assert any(m.recent for m in out)
    assert "digest" in kinds
    digest = next(m for m in out if m.kind == "digest")
    assert digest.compression["count"] == 1
    assert "t1" in digest.compression["ids"]


def test_compress_noop_under_budget():
    ctx = [MemoryPacket(task_id="t1", summary="short")]
    assert compress(ctx, budget=1000) == ctx


def test_compress_all_decision_keeps_all():
    ctx = [
        MemoryPacket(task_id="t1", kind="decision", summary="decide A"),
        MemoryPacket(task_id="t2", kind="decision", summary="decide B"),
    ]
    out = compress(ctx, budget=1)
    assert len(out) == 2
    assert all(m.kind == "decision" for m in out)


def test_digest_summary_contains_folded_content():
    ctx = [
        MemoryPacket(task_id="t1", kind="normal", summary="alpha"),
        MemoryPacket(task_id="t2", kind="normal", summary="beta"),
    ]
    out = compress(ctx, budget=1)
    digest = next(m for m in out if m.kind == "digest")
    assert "alpha" in digest.summary
    assert "beta" in digest.summary
```

- [ ] **Step 3: 跑测试确认失败**

Run: `pytest tests/aegisos_agents/memory/test_compactor.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'agents.memory.compression'`

- [ ] **Step 4: 实现 compactor.py**

```python
# aegisos_agents/memory/compression/__init__.py
from .compactor import compress
__all__ = ["compress"]
```

```python
# aegisos_agents/memory/compression/compactor.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 超长程上下文压缩
from __future__ import annotations

from protocol.memory import MemoryPacket


def _token_estimate(ctx: list[MemoryPacket]) -> int:
    total = 0
    for m in ctx:
        total += len(str(m.summary)) + len(str(m.working)) + len(str(m.episodic))
    return total // 4 + 1


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
        compression={
            "count": len(rest),
            "ids": [m.task_id for m in rest],
        },
    )
    return keep + [digest]
```

- [ ] **Step 5: 登记 `04`/`06` 的 MemoryPacket 字段扩展**

- [ ] **Step 6: 跑测试确认通过**

Run: `pytest tests/aegisos_agents/memory/test_compactor.py -v`
Expected: 4 passed

- [ ] **Step 7: 提交**

```bash
git add protocol/memory.py aegisos_agents/memory/compression/ tests/aegisos_agents/memory/test_compactor.py \
  developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md
git commit -m "feat(memory): long-context compression + MemoryPacket kind/recent (B1)"
```

---

### Task B2: memory/recall 唤醒

> `MemoryPacket` 已在 B1 扩 `kind`/`recent`；recall 复用 `episodic`/`embedding` 字段。

**Files:**
- Create: `aegisos_agents/memory/recall/__init__.py`
- Create: `aegisos_agents/memory/recall/recaller.py`
- Test: `tests/aegisos_agents/memory/test_recaller.py`

**Interfaces:**
- Consumes: `protocol/memory.py`（`MemoryPacket`）
- Produces: `recall(trigger: str, episodic: list[MemoryPacket], vector: list[MemoryPacket]) -> list[MemoryPacket]`（向量 top_k + 情景关键事件 `kind=="decision"`；vector 先用 in-memory stub，Qdrant 接入在后续基建阶段）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/memory/test_recaller.py
from protocol.memory import MemoryPacket
from agents.memory.recall.recaller import recall


def test_recall_returns_decision_packets_matching_trigger():
    episodic = [
        MemoryPacket(task_id="e1", kind="decision", summary="decide to isolate h1"),
        MemoryPacket(task_id="e2", kind="normal", summary="scanned h2"),
    ]
    vector = [
        MemoryPacket(task_id="v1", kind="decision", summary="isolate host"),
    ]
    result = recall("isolate", episodic, vector)
    ids = [m.task_id for m in result]
    assert "e1" in ids   # episodic decision matching trigger
    assert "v1" in ids  # vector top_k matching trigger


def test_recall_prioritizes_decision_kind():
    episodic = [
        MemoryPacket(task_id="e1", kind="decision", summary="isolate h1"),
        MemoryPacket(task_id="e2", kind="normal", summary="isolate h2"),
    ]
    result = recall("isolate", episodic, [])
    decision_results = [m for m in result if m.kind == "decision"]
    normal_results = [m for m in result if m.kind == "normal"]
    assert len(decision_results) >= 1
    # decisions come first
    assert result[0].kind == "decision"


def test_recall_empty_when_no_match():
    episodic = [MemoryPacket(task_id="e1", summary="nothing relevant")]
    result = recall("nonexistent", episodic, [])
    assert result == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/aegisos_agents/memory/test_recaller.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'agents.memory.recall'`

- [ ] **Step 3: 实现 recaller.py**

```python
# aegisos_agents/memory/recall/__init__.py
from .recaller import recall
__all__ = ["recall"]
```

```python
# aegisos_agents/memory/recall/recaller.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 超长程记忆唤醒机制
from __future__ import annotations

from protocol.memory import MemoryPacket

TOP_K = 5


def recall(
    trigger: str,
    episodic: list[MemoryPacket],
    vector: list[MemoryPacket],
) -> list[MemoryPacket]:
    trigger_lower = trigger.lower()
    candidates: list[MemoryPacket] = []

    for m in episodic:
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    for m in vector:
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    decisions = [m for m in candidates if m.kind == "decision"]
    normals = [m for m in candidates if m.kind != "decision"]
    return (decisions + normals)[:TOP_K]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/aegisos_agents/memory/test_recaller.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/memory/recall/ tests/aegisos_agents/memory/test_recaller.py
git commit -m "feat(memory): recall mechanism (B2)"
```

---

## Phase C - 动态异构拓扑 + 低熵路由（P3）CORE

### Task C1: topology 活跃子图计算

> 协议变更：现有 `GraphNode`（`protocol/graph.py`）无 `status`，无法表达 active/idle。Step 1 扩 `status:str="active"`（默认值向后兼容）。注意 `Graph.nodes` 为 dict，`NodeKind` 枚举为 `NodeKind.Agent`（驼峰）。

**Files:**
- Create: `aegisos_agents/planning/engine/topology/__init__.py`
- Create: `aegisos_agents/planning/engine/topology/topology.py`
- Modify: `protocol/graph.py`（`GraphNode` 扩 `status` 字段）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`
- Test: `tests/aegisos_agents/planning/test_topology.py`

**Interfaces:**
- Consumes: `protocol/graph.py`（`Graph`/`GraphNode`/`NodeKind`；`Graph.nodes` 为 dict）
- Produces: `active_subgraph(graph: Graph, required_capability: str) -> Graph`（仅 `status=="active"` 且 `required_capability in capabilities` 的节点）

- [ ] **Step 1: 扩展 `protocol/graph.py` 的 GraphNode**

在 `GraphNode` dataclass 末尾追加：

```python
@dataclass
class GraphNode:
    node_id: str
    kind: NodeKind
    name: str = ""
    capabilities: list = field(default_factory=list)
    trust_score: float = 1.0
    success_rate: float = 1.0
    latency: float = 0.0
    status: str = "active"   # active | idle | degraded
```

- [ ] **Step 2: 写失败测试**

```python
# tests/aegisos_agents/planning/test_topology.py
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
    assert list(sub.nodes.keys()) == ["a"]


def test_active_subgraph_includes_degraded_if_explicit():
    a = GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="active")
    d = GraphNode(node_id="d", kind=NodeKind.Agent, capabilities=["recon"], status="degraded")
    g = Graph()
    g.add_node(a)
    g.add_node(d)
    sub = active_subgraph(g, required_capability="recon")
    assert set(sub.nodes.keys()) == {"a", "d"}


def test_active_subgraph_empty_when_no_match():
    g = Graph()
    g.add_node(GraphNode(node_id="x", kind=NodeKind.Agent, capabilities=["hunt"], status="active"))
    sub = active_subgraph(g, required_capability="recon")
    assert len(sub.nodes) == 0
```

- [ ] **Step 3: 跑确认失败**

Run: `pytest tests/aegisos_agents/planning/test_topology.py -v`
Expected: FAIL - `ModuleNotFoundError`

- [ ] **Step 4: 实现 topology.py**

```python
# aegisos_agents/planning/engine/topology/__init__.py
from .topology import active_subgraph
__all__ = ["active_subgraph"]
```

```python
# aegisos_agents/planning/engine/topology/topology.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 活跃子图计算
from __future__ import annotations

from protocol.graph import Graph, GraphNode

_ACTIVE_STATES = {"active", "degraded"}


def active_subgraph(graph: Graph, required_capability: str) -> Graph:
    sub = Graph()
    for n in graph.nodes.values():
        status = getattr(n, "status", "active")
        if status in _ACTIVE_STATES and required_capability in n.capabilities:
            sub.add_node(n)
    return sub
```

- [ ] **Step 5: 登记 `04`/`06` 的 GraphNode.status 扩展**

- [ ] **Step 6: 跑确认通过**

Run: `pytest tests/aegisos_agents/planning/test_topology.py -v`
Expected: 3 passed

- [ ] **Step 7: 提交**

```bash
git add protocol/graph.py aegisos_agents/planning/engine/topology/ tests/aegisos_agents/planning/test_topology.py \
  developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md
git commit -m "feat(planning): active subgraph computation + GraphNode.status (C1)"
```

---

### Task C2: router 低熵稀疏路由

> `Message`（`protocol/message.py`）无 `required_capability` 字段。`route()` 改为显式参数 `required_capability`（不扩 Message）。返回 `NodeRef`（匹配 `message.py` 的 `NodeRef(node_id=..., node_type=...)`）。

**Files:**
- Create: `aegisos_agents/planning/engine/router/__init__.py`
- Create: `aegisos_agents/planning/engine/router/router.py`
- Test: `tests/aegisos_agents/planning/test_router.py`

**Interfaces:**
- Consumes: C1 `active_subgraph`、`protocol/message.py`（`Message`/`NodeRef`）、`protocol/graph.py`（`Graph`）
- Produces: `route(message: Message, topology: Graph, required_capability: str) -> list[NodeRef]`（Top-K，`TOP_K=3`，非全广播）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/planning/test_router.py
from protocol.message import Message, NodeRef
from protocol.graph import Graph, GraphNode, NodeKind
from agents.planning.engine.router.router import route, TOP_K


def test_route_is_sparse_not_broadcast():
    g = Graph()
    for i in range(10):
        g.add_node(GraphNode(
            node_id=f"n{i}", kind=NodeKind.Agent,
            capabilities=["recon"], status="active",
        ))
    msg = Message()
    targets = route(msg, g, required_capability="recon")
    assert 0 < len(targets) <= TOP_K
    assert len(targets) < len(g.nodes)
    assert all(isinstance(t, NodeRef) for t in targets)


def test_route_skips_idle_and_wrong_capability():
    g = Graph()
    g.add_node(GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="idle"))
    g.add_node(GraphNode(node_id="b", kind=NodeKind.Agent, capabilities=["hunt"], status="active"))
    assert route(Message(), g, required_capability="recon") == []


def test_route_prefers_higher_success_rate():
    g = Graph()
    g.add_node(GraphNode(node_id="low", kind=NodeKind.Agent, capabilities=["recon"], success_rate=0.3, status="active"))
    g.add_node(GraphNode(node_id="high", kind=NodeKind.Agent, capabilities=["recon"], success_rate=0.9, status="active"))
    targets = route(Message(), g, required_capability="recon")
    assert targets[0].node_id == "high"


def test_route_returns_empty_on_empty_graph():
    g = Graph()
    assert route(Message(), g, required_capability="recon") == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/planning/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 router.py**

```python
# aegisos_agents/planning/engine/router/__init__.py
from .router import route, TOP_K
__all__ = ["route", "TOP_K"]
```

```python
# aegisos_agents/planning/engine/router/router.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 低熵稀疏路由 Top-K
from __future__ import annotations

from protocol.message import Message, NodeRef
from protocol.graph import Graph
from agents.planning.engine.topology.topology import active_subgraph

TOP_K = 3


def route(
    message: Message,
    topology: Graph,
    required_capability: str,
) -> list[NodeRef]:
    sub = active_subgraph(topology, required_capability)
    candidates = list(sub.nodes.values())
    scored = sorted(
        candidates,
        key=lambda n: _affinity(message, n) - _load_penalty(n),
        reverse=True,
    )
    k = min(TOP_K, len(scored))
    return [
        NodeRef(node_id=n.node_id, node_type=n.kind.value)
        for n in scored[:k]
    ]


def _affinity(message: Message, n) -> float:
    return getattr(n, "success_rate", 1.0)


def _load_penalty(n) -> float:
    return getattr(n, "latency", 0.0)
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/planning/test_router.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/planning/engine/router/router.py aegisos_agents/planning/engine/router/__init__.py \
  tests/aegisos_agents/planning/test_router.py
git commit -m "feat(planning): low-entropy sparse router (C2)"
```

---

### Task C3: 异构选举

**Files:**
- Create: `aegisos_agents/planning/engine/router/election.py`
- Test: `tests/aegisos_agents/planning/test_election.py`

**Interfaces:**
- Consumes: `protocol/graph.py`（`GraphNode.capabilities`）、`protocol/message.py`（`NodeRef`）
- Produces: `elect(task_features: list[float], instances: list[GraphNode]) -> NodeRef`（任务特征向量与实例能力向量点积最大者）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/planning/test_election.py
from protocol.graph import GraphNode, NodeKind
from agents.planning.engine.router.election import elect


def test_elect_picks_best_capability_match():
    # 实例 A：偏向 CVE 检索 [1.0, 0.0]
    # 实例 B：偏向 ATT&CK 推理 [0.0, 1.0]
    # 任务特征向量 [0.9, 0.1] -> 应选 A
    a = GraphNode(node_id="cve_type", kind=NodeKind.Agent, capabilities=["recon"])
    b = GraphNode(node_id="attack_type", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(task_features=[0.9, 0.1], instances=[a, b], capability_vectors={
        "cve_type": [1.0, 0.0],
        "attack_type": [0.0, 1.0],
    })
    assert result.node_id == "cve_type"


def test_elect_picks_other_when_features_flip():
    a = GraphNode(node_id="cve_type", kind=NodeKind.Agent, capabilities=["recon"])
    b = GraphNode(node_id="attack_type", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(task_features=[0.1, 0.9], instances=[a, b], capability_vectors={
        "cve_type": [1.0, 0.0],
        "attack_type": [0.0, 1.0],
    })
    assert result.node_id == "attack_type"


def test_elect_single_instance():
    a = GraphNode(node_id="only", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(task_features=[1.0], instances=[a], capability_vectors={
        "only": [1.0],
    })
    assert result.node_id == "only"
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/planning/test_election.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 election.py**

```python
# aegisos_agents/planning/engine/router/election.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 异构选举
from __future__ import annotations

from protocol.graph import GraphNode
from protocol.message import NodeRef


def elect(
    task_features: list[float],
    instances: list[GraphNode],
    capability_vectors: dict[str, list[float]],
) -> NodeRef:
    if not instances:
        return NodeRef(node_id="", node_type="agent")

    best_node = None
    best_score = float("-inf")

    for inst in instances:
        vec = capability_vectors.get(inst.node_id, [])
        score = sum(f * v for f, v in zip(task_features, vec))
        if score > best_score:
            best_score = score
            best_node = inst

    return NodeRef(
        node_id=best_node.node_id,
        node_type=best_node.kind.value,
    )
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/planning/test_election.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/planning/engine/router/election.py tests/aegisos_agents/planning/test_election.py
git commit -m "feat(planning): heterogeneous election (C3)"
```

---

## Phase D - 端边云调度 + 多模型兼容层（P4）

### Task D1: scheduler 端边云卸载判定

> 协议变更：现有 `Task`（`protocol/scheduler.py`）无 `privacy`/`latency_budget`。Step 1 扩两字段（默认值向后兼容）。

**Files:**
- Create: `aegisos_agents/planning/engine/scheduler/__init__.py`
- Create: `aegisos_agents/planning/engine/scheduler/scheduler.py`
- Modify: `protocol/scheduler.py`（`Task` 扩 `privacy`/`latency_budget`）
- Modify: `developer/specs/04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md`
- Test: `tests/aegisos_agents/planning/test_scheduler.py`

**Interfaces:**
- Consumes: `protocol/scheduler.py`（`Task`：新增 `privacy`/`latency_budget`）、`Model`（本任务定义）
- Produces: `schedule(task: Task, models: list[Model]) -> Model`（见 14 S8.2）

- [ ] **Step 1: 扩展 `protocol/scheduler.py` 的 Task**

在 `Task` dataclass 末尾追加：

```python
@dataclass
class Task:
    # ... 现有字段保持不变 ...
    privacy: str = "standard"       # local | standard | unrestricted
    latency_budget: float = 10.0   # 秒
```

- [ ] **Step 2: 写失败测试**

```python
# tests/aegisos_agents/planning/test_scheduler.py
import pytest
from protocol.scheduler import Task
from agents.planning.engine.scheduler.scheduler import schedule, Model, EDGE_THRESHOLD


def test_privacy_local_picks_edge_model():
    task = Task(goal="triage alert", privacy="local")
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["triage"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["triage"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


def test_low_latency_picks_edge():
    task = Task(goal="detect", privacy="unrestricted", latency_budget=EDGE_THRESHOLD - 0.1)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["detect"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["detect"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


def test_high_latency_no_privacy_picks_cloud():
    task = Task(goal="attack_chain_planning", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["planning"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["planning"]),
    ]
    result = schedule(task, models)
    assert result.tier == "cloud"


def test_filters_by_required_capability():
    task = Task(goal="hunt", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["triage"]),
        Model(model_id="cloud_hunt", tier="cloud", size="large", capabilities=["hunt"]),
    ]
    result = schedule(task, models, required_capability="hunt")
    assert result.model_id == "cloud_hunt"
```

- [ ] **Step 3: 跑确认失败**

Run: `pytest tests/aegisos_agents/planning/test_scheduler.py -v`
Expected: FAIL

- [ ] **Step 4: 实现 scheduler.py**

```python
# aegisos_agents/planning/engine/scheduler/__init__.py
from .scheduler import schedule, Model, EDGE_THRESHOLD
__all__ = ["schedule", "Model", "EDGE_THRESHOLD"]
```

```python
# aegisos_agents/planning/engine/scheduler/scheduler.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 端边云卸载调度
from __future__ import annotations

from dataclasses import dataclass, field

from protocol.scheduler import Task

EDGE_THRESHOLD = 5.0  # 秒


@dataclass
class Model:
    model_id: str
    tier: str = "cloud"       # edge | cloud
    size: str = "medium"      # small | medium | large
    capabilities: list = field(default_factory=list)


def schedule(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    candidates = models
    if required_capability:
        candidates = [
            m for m in models
            if required_capability in m.capabilities
        ]
    if not candidates:
        raise ValueError(f"No model with capability '{required_capability}'")

    if task.privacy == "local" or task.latency_budget < EDGE_THRESHOLD:
        edge = [m for m in candidates if m.tier == "edge"]
        if edge:
            return edge[0]
        return candidates[0]
    cloud = [m for m in candidates if m.tier == "cloud"]
    if cloud:
        return cloud[0]
    return candidates[0]
```

- [ ] **Step 5: 登记 `04`/`06` 的 Task 字段扩展**

- [ ] **Step 6: 跑确认通过**

Run: `pytest tests/aegisos_agents/planning/test_scheduler.py -v`
Expected: 4 passed

- [ ] **Step 7: 提交**

```bash
git add protocol/scheduler.py aegisos_agents/planning/engine/scheduler/ tests/aegisos_agents/planning/test_scheduler.py \
  developer/specs/04_PROTOCOL_SPEC.md developer/specs/06_SCHEMA_SPEC.md
git commit -m "feat(planning): edge-cloud scheduling (D1)"
```

---

### Task D2: 多模型兼容层

> 设计目标：支持 OpenAI API、Anthropic API、本地部署模型、Mock stub 四种方案，通过统一 `ModelProvider` 接口切换。用户可按需配置。

**Files:**
- Create: `aegisos_agents/tools/llms/__init__.py`
- Create: `aegisos_agents/tools/llms/base.py`
- Create: `aegisos_agents/tools/llms/openai_provider.py`
- Create: `aegisos_agents/tools/llms/anthropic_provider.py`
- Create: `aegisos_agents/tools/llms/local_provider.py`
- Create: `aegisos_agents/tools/llms/mock_provider.py`
- Create: `aegisos_agents/tools/llms/model_router.py`
- Test: `tests/aegisos_agents/tools/test_model_router.py`

**Interfaces:**
- Consumes: D1 `schedule`/`Model`
- Produces: `ModelProvider`（Protocol）、`ModelRouter`（按 D1 调度结果选 provider 并调用）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/tools/test_model_router.py
import pytest
from agents.tools.llms.base import ModelProvider, LLMRequest, LLMResponse
from agents.tools.llms.mock_provider import MockProvider
from agents.tools.llms.model_router import ModelRouter
from agents.tools.llms.scheduler_adapter import schedule_for_llm
from protocol.scheduler import Task
from agents.planning.engine.scheduler.scheduler import Model


def test_mock_provider_returns_response():
    provider = MockProvider(responses={"hello": "world"})
    req = LLMRequest(prompt="hello", model_id="mock-1")
    resp = provider.complete(req)
    assert resp.text == "world"
    assert resp.ok is True


def test_model_router_dispatches_to_correct_provider():
    mock_openai = MockProvider(responses={"default": "openai_response"})
    mock_anthropic = MockProvider(responses={"default": "anthropic_response"})
    mock_local = MockProvider(responses={"default": "local_response"})
    router = ModelRouter(
        providers={
            "openai": mock_openai,
            "anthropic": mock_anthropic,
            "local": mock_local,
        },
        default_provider="openai",
    )
    resp = router.complete(LLMRequest(prompt="test", model_id="gpt-4"))
    assert resp.text == "openai_response"


def test_model_router_falls_back_to_default():
    mock_default = MockProvider(responses={"default": "fallback"})
    router = ModelRouter(
        providers={"default": mock_default},
        default_provider="default",
    )
    resp = router.complete(LLMRequest(prompt="test", model_id="unknown-model"))
    assert resp.text == "fallback"


def test_mock_provider_without_matching_response_returns_stub():
    provider = MockProvider()
    req = LLMRequest(prompt="anything", model_id="mock-1")
    resp = provider.complete(req)
    assert resp.ok is True
    assert len(resp.text) > 0


def test_router_uses_scheduler_result():
    """Router selects provider based on scheduler Model.tier -> provider mapping."""
    mock_edge = MockProvider(responses={"default": "edge_response"})
    mock_cloud = MockProvider(responses={"default": "cloud_response"})
    router = ModelRouter(
        providers={"edge": mock_edge, "cloud": mock_cloud},
        default_provider="cloud",
    )
    # Simulate scheduler picking edge model
    edge_model = Model(model_id="edge_small", tier="edge", capabilities=["triage"])
    resp = router.complete_with_model(
        LLMRequest(prompt="triage this alert", model_id="edge_small"),
        edge_model,
    )
    assert resp.text == "edge_response"
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/tools/test_model_router.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 base.py**

```python
# aegisos_agents/tools/llms/__init__.py
from .base import ModelProvider, LLMRequest, LLMResponse
from .mock_provider import MockProvider
from .model_router import ModelRouter
__all__ = ["ModelProvider", "LLMRequest", "LLMResponse",
           "MockProvider", "ModelRouter"]
```

```python
# aegisos_agents/tools/llms/base.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 多模型兼容层抽象接口
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    prompt: str
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    stop: list = field(default_factory=list)


@dataclass
class LLMResponse:
    text: str = ""
    ok: bool = True
    error: str = ""
    usage: dict = field(default_factory=dict)
    model_id: str = ""


class ModelProvider(Protocol):
    """Unified interface for all LLM providers."""
    def complete(self, request: LLMRequest) -> LLMResponse: ...
```

- [ ] **Step 4: 实现 mock_provider.py**

```python
# aegisos_agents/tools/llms/mock_provider.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Mock LLM provider for testing
from __future__ import annotations

from .base import LLMRequest, LLMResponse


class MockProvider:
    """Deterministic mock provider for tests and offline development."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        text = self._responses.get(request.prompt)
        if text is None:
            text = self._responses.get("default", f"[mock] {request.prompt[:50]}")
        return LLMResponse(
            text=text,
            ok=True,
            model_id=request.model_id or "mock",
            usage={"prompt_tokens": len(request.prompt) // 4, "completion_tokens": len(text) // 4},
        )
```

- [ ] **Step 5: 实现 openai_provider.py**

```python
# aegisos_agents/tools/llms/openai_provider.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: OpenAI API provider
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class OpenAIProvider:
    """OpenAI-compatible API provider. Requires OPENAI_API_KEY env var."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or "https://api.openai.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="", ok=False,
                error="OPENAI_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": request.model_id or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            if request.stop:
                payload["stop"] = request.stop

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "gpt-4o-mini",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
```

- [ ] **Step 6: 实现 anthropic_provider.py**

```python
# aegisos_agents/tools/llms/anthropic_provider.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Anthropic API provider
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class AnthropicProvider:
    """Anthropic Claude API provider. Requires ANTHROPIC_API_KEY env var."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or "https://api.anthropic.com/v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="", ok=False,
                error="ANTHROPIC_API_KEY not set; use MockProvider for testing",
            )
        try:
            import httpx

            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": request.model_id or "claude-sonnet-4-20250514",
                "max_tokens": request.max_tokens,
                "system": request.system_prompt or "You are a helpful assistant.",
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
            }

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                text_parts = [
                    block["text"]
                    for block in data.get("content", [])
                    if block.get("type") == "text"
                ]
                return LLMResponse(
                    text="".join(text_parts),
                    ok=True,
                    model_id=request.model_id or "claude-sonnet-4-20250514",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
```

- [ ] **Step 7: 实现 local_provider.py**

```python
# aegisos_agents/tools/llms/local_provider.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Local model provider (Ollama / vLLM / LM Studio compatible)
from __future__ import annotations

import os

from .base import LLMRequest, LLMResponse


class LocalProvider:
    """Local LLM provider. Compatible with Ollama / vLLM / LM Studio OpenAI-compatible endpoints."""

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or os.environ.get(
            "LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            import httpx

            payload = {
                "model": request.model_id or "qwen2.5:7b",
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    ok=True,
                    model_id=request.model_id or "local",
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            return LLMResponse(text="", ok=False, error=str(e), model_id=request.model_id)
```

- [ ] **Step 8: 实现 model_router.py**

```python
# aegisos_agents/tools/llms/model_router.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 多模型路由器
from __future__ import annotations

from .base import LLMRequest, LLMResponse, ModelProvider


class ModelRouter:
    """Routes LLM requests to the appropriate provider.

    Provider selection logic:
    1. If request.model_id matches a known model prefix (gpt-* -> openai,
       claude-* -> anthropic, local/* -> local), route to that provider.
    2. Otherwise, use default_provider.
    3. complete_with_model() uses scheduler Model.tier -> provider mapping.
    """

    MODEL_PREFIX_MAP = {
        "gpt": "openai",
        "o1": "openai",
        "o3": "openai",
        "claude": "anthropic",
        "local": "local",
        "qwen": "local",
        "deepseek": "local",
        "llama": "local",
        "mock": "mock",
    }

    TIER_PROVIDER_MAP = {
        "edge": "local",
        "cloud": "openai",
    }

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        default_provider: str = "mock",
    ):
        self._providers = providers
        self._default = default_provider

    def complete(self, request: LLMRequest) -> LLMResponse:
        provider_name = self._resolve_provider_by_model(request.model_id)
        provider = self._providers.get(provider_name)
        if provider is None:
            provider = self._providers.get(self._default)
        if provider is None:
            return LLMResponse(
                text="", ok=False,
                error=f"No provider available for model '{request.model_id}'",
            )
        return provider.complete(request)

    def complete_with_model(
        self,
        request: LLMRequest,
        model: "Model",
    ) -> LLMResponse:
        provider_name = self.TIER_PROVIDER_MAP.get(model.tier, self._default)
        provider = self._providers.get(provider_name, self._providers.get(self._default))
        if provider is None:
            return LLMResponse(
                text="", ok=False,
                error=f"No provider for tier '{model.tier}'",
            )
        req = LLMRequest(
            prompt=request.prompt,
            model_id=model.model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            stop=request.stop,
        )
        return provider.complete(req)

    def _resolve_provider_by_model(self, model_id: str) -> str:
        if not model_id:
            return self._default
        lower = model_id.lower()
        for prefix, provider_name in self.MODEL_PREFIX_MAP.items():
            if lower.startswith(prefix):
                return provider_name
        return self._default
```

- [ ] **Step 9: 跑确认通过**

Run: `pytest tests/aegisos_agents/tools/test_model_router.py -v`
Expected: 5 passed

- [ ] **Step 10: 提交**

```bash
git add aegisos_agents/tools/llms/ tests/aegisos_agents/tools/test_model_router.py
git commit -m "feat(tools): multi-model compatibility layer (D2)"
```

---

## Phase E - 红蓝紫 Agent 角色（P5）

> 每角色遵循 `08_AGENT_SPEC` 生命周期（init->perceive->plan->act->reflect->respond）。
> 每角色通过 `ModelRouter` 调用 LLM（Mock 模式下确定性输出），输入/输出用 `protocol/cyber.py` 类型。
> 测试中统一使用 `MockProvider`，保证无外部 API 依赖。

### Task E1: recon Agent（红队-侦察）

**Files:**
- Create: `aegisos_agents/action/recon/__init__.py`
- Create: `aegisos_agents/action/recon/agent.py`
- Test: `tests/aegisos_agents/action/test_recon.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`Asset`）、`aegisos_agents/tools/llms/`（`ModelProvider`/`LLMRequest`）
- Produces: `ReconAgent.scan(target_range: str) -> list[Asset]`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_recon.py
from agents.action.recon.agent import ReconAgent
from agents.tools.llms.mock_provider import MockProvider
from agents.tools.llms.base import LLMRequest


def test_recon_returns_assets_for_target_range():
    mock = MockProvider(responses={
        "default": '{"assets": [{"asset_id": "h1", "host": "10.0.0.1", "services": ["ssh:22"], "os": "linux"}]}'
    })
    agent = ReconAgent(provider=mock)
    assets = agent.scan(target_range="10.0.0.0/24")
    assert len(assets) >= 1
    assert assets[0].asset_id == "h1"
    assert assets[0].host == "10.0.0.1"


def test_recon_returns_empty_on_no_response():
    mock = MockProvider(responses={"default": '{"assets": []}'})
    agent = ReconAgent(provider=mock)
    assets = agent.scan(target_range="10.0.0.0/24")
    assert assets == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_recon.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 agent.py**

```python
# aegisos_agents/action/recon/__init__.py
from .agent import ReconAgent
__all__ = ["ReconAgent"]
```

```python
# aegisos_agents/action/recon/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队侦察 Agent
from __future__ import annotations

import json

from protocol.cyber import Asset
from agents.tools.llms.base import LLMRequest, ModelProvider


SYSTEM_PROMPT = (
    "You are a network reconnaissance agent. Given a target range, "
    "return a JSON object with an 'assets' array. Each asset has "
    "asset_id, host, services (list), os, exposure."
)


class ReconAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def scan(self, target_range: str) -> list[Asset]:
        prompt = f"Scan target range: {target_range}"
        resp = self._provider.complete(LLMRequest(
            prompt=prompt,
            model_id="recon-agent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                Asset(
                    asset_id=a.get("asset_id", ""),
                    host=a.get("host", ""),
                    services=a.get("services", []),
                    os=a.get("os", ""),
                    exposure=a.get("exposure", "external"),
                )
                for a in data.get("assets", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_recon.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/recon/ tests/aegisos_agents/action/test_recon.py
git commit -m "feat(action): recon agent (E1)"
```

---

### Task E2: vuln_correlator Agent（红队-漏洞关联）

**Files:**
- Create: `aegisos_agents/action/vuln_correlator/__init__.py`
- Create: `aegisos_agents/action/vuln_correlator/agent.py`
- Test: `tests/aegisos_agents/action/test_vuln_correlator.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`Asset`/`VulnFinding`）、`ModelProvider`
- Produces: `VulnCorrelatorAgent.correlate(assets: list[Asset]) -> list[VulnFinding]`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_vuln_correlator.py
from protocol.cyber import Asset
from agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from agents.tools.llms.mock_provider import MockProvider


def test_correlate_returns_findings():
    mock = MockProvider(responses={
        "default": '{"findings": [{"finding_id": "v1", "cve_id": "CVE-2024-1", "asset_id": "h1", "cvss": 9.8, "attack_surface": "ssh"}]}'
    })
    agent = VulnCorrelatorAgent(provider=mock)
    findings = agent.correlate([Asset(asset_id="h1", host="10.0.0.1")])
    assert len(findings) == 1
    assert findings[0].cve_id == "CVE-2024-1"
    assert findings[0].cvss == 9.8


def test_correlate_empty_on_no_vulns():
    mock = MockProvider(responses={"default": '{"findings": []}'})
    agent = VulnCorrelatorAgent(provider=mock)
    findings = agent.correlate([Asset(asset_id="h1")])
    assert findings == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_vuln_correlator.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/vuln_correlator/__init__.py
from .agent import VulnCorrelatorAgent
__all__ = ["VulnCorrelatorAgent"]
```

```python
# aegisos_agents/action/vuln_correlator/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队漏洞关联 Agent
from __future__ import annotations

import json

from protocol.cyber import Asset, VulnFinding
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a vulnerability correlation agent. Given a list of assets, "
    "return JSON with a 'findings' array. Each finding has: finding_id, "
    "cve_id, asset_id, cvss (float), attack_surface."
)


class VulnCorrelatorAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def correlate(self, assets: list[Asset]) -> list[VulnFinding]:
        asset_desc = json.dumps([
            {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
            for a in assets
        ])
        resp = self._provider.complete(LLMRequest(
            prompt=f"Correlate vulnerabilities for these assets: {asset_desc}",
            model_id="vuln-correlator",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                VulnFinding(
                    finding_id=f.get("finding_id", ""),
                    cve_id=f.get("cve_id", ""),
                    asset_id=f.get("asset_id", ""),
                    cvss=f.get("cvss", 0.0),
                    attack_surface=f.get("attack_surface", ""),
                )
                for f in data.get("findings", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_vuln_correlator.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/vuln_correlator/ tests/aegisos_agents/action/test_vuln_correlator.py
git commit -m "feat(action): vuln correlator agent (E2)"
```

---

### Task E3: exploit_planner Agent（红队-利用链规划）

**Files:**
- Create: `aegisos_agents/action/exploit_planner/__init__.py`
- Create: `aegisos_agents/action/exploit_planner/agent.py`
- Test: `tests/aegisos_agents/action/test_exploit_planner.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`VulnFinding`/`AttackStep`/`AttackChain`）、`ModelProvider`
- Produces: `ExploitPlannerAgent.plan(findings: list[VulnFinding]) -> AttackChain`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_exploit_planner.py
from protocol.cyber import VulnFinding
from agents.action.exploit_planner.agent import ExploitPlannerAgent
from agents.tools.llms.mock_provider import MockProvider


def test_plan_returns_attack_chain():
    mock = MockProvider(responses={
        "default": '{"chain_id": "c1", "target": "h1", "steps": [{"step_id": "s1", "technique": "T1110", "from_asset": "ext", "to_asset": "h1", "success": true}], "status": "ongoing"}'
    })
    agent = ExploitPlannerAgent(provider=mock)
    chain = agent.plan([VulnFinding(finding_id="v1", cve_id="CVE-2024-1", asset_id="h1")])
    assert chain.chain_id == "c1"
    assert len(chain.steps) == 1
    assert chain.steps[0].technique == "T1110"
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_exploit_planner.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/exploit_planner/__init__.py
from .agent import ExploitPlannerAgent
__all__ = ["ExploitPlannerAgent"]
```

```python
# aegisos_agents/action/exploit_planner/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队利用链规划 Agent
from __future__ import annotations

import json

from protocol.cyber import VulnFinding, AttackStep, AttackChain
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an exploit chain planner. Given vulnerability findings, "
    "return JSON with chain_id, target, steps (array of {step_id, technique, "
    "from_asset, to_asset, success}), status."
)


class ExploitPlannerAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def plan(self, findings: list[VulnFinding]) -> AttackChain:
        findings_desc = json.dumps([
            {"finding_id": f.finding_id, "cve_id": f.cve_id, "asset_id": f.asset_id, "cvss": f.cvss}
            for f in findings
        ])
        resp = self._provider.complete(LLMRequest(
            prompt=f"Plan exploit chain for: {findings_desc}",
            model_id="exploit-planner",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.4,
        ))
        if not resp.ok:
            return AttackChain(chain_id="", status="failed")
        try:
            data = json.loads(resp.text)
            steps = [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),
                )
                for s in data.get("steps", [])
            ]
            return AttackChain(
                chain_id=data.get("chain_id", ""),
                target=data.get("target", ""),
                steps=steps,
                status=data.get("status", "planned"),
            )
        except (json.JSONDecodeError, KeyError):
            return AttackChain(chain_id="", status="failed")
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_exploit_planner.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/exploit_planner/ tests/aegisos_agents/action/test_exploit_planner.py
git commit -m "feat(action): exploit planner agent (E3)"
```

---

### Task E4: lateral_move Agent（红队-横向移动）

**Files:**
- Create: `aegisos_agents/action/lateral_move/__init__.py`
- Create: `aegisos_agents/action/lateral_move/agent.py`
- Test: `tests/aegisos_agents/action/test_lateral_move.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`AttackChain`/`AttackStep`）、`ModelProvider`
- Produces: `LateralMoveAgent.plan_moves(chain: AttackChain, topology: Graph) -> list[AttackStep]`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_lateral_move.py
from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph, GraphNode, NodeKind
from agents.action.lateral_move.agent import LateralMoveAgent
from agents.tools.llms.mock_provider import MockProvider


def test_plan_moves_returns_lateral_steps():
    mock = MockProvider(responses={
        "default": '{"steps": [{"step_id": "l1", "technique": "T1021", "from_asset": "h1", "to_asset": "h2", "success": true}]}'
    })
    agent = LateralMoveAgent(provider=mock)
    chain = AttackChain(chain_id="c1", target="h1", steps=[
        AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1")
    ])
    topo = Graph()
    topo.add_node(GraphNode(node_id="h1", kind=NodeKind.Agent, name="host1"))
    topo.add_node(GraphNode(node_id="h2", kind=NodeKind.Agent, name="host2"))
    steps = agent.plan_moves(chain, topo)
    assert len(steps) == 1
    assert steps[0].technique == "T1021"
    assert steps[0].to_asset == "h2"
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_lateral_move.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/lateral_move/__init__.py
from .agent import LateralMoveAgent
__all__ = ["LateralMoveAgent"]
```

```python
# aegisos_agents/action/lateral_move/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队横向移动 Agent
from __future__ import annotations

import json

from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a lateral movement planner. Given an attack chain and network "
    "topology, return JSON with a 'steps' array. Each step has: step_id, "
    "technique (ATT&CK id), from_asset, to_asset, success."
)


class LateralMoveAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def plan_moves(self, chain: AttackChain, topology: Graph) -> list[AttackStep]:
        chain_desc = json.dumps({
            "chain_id": chain.chain_id,
            "target": chain.target,
            "current_steps": [
                {"step_id": s.step_id, "to_asset": s.to_asset}
                for s in chain.steps
            ],
        })
        topo_nodes = [
            {"node_id": n.node_id, "name": n.name}
            for n in topology.nodes.values()
        ]
        resp = self._provider.complete(LLMRequest(
            prompt=f"Plan lateral moves. Chain: {chain_desc}. Topology: {json.dumps(topo_nodes)}",
            model_id="lateral-move",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.4,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),
                )
                for s in data.get("steps", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_lateral_move.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/lateral_move/ tests/aegisos_agents/action/test_lateral_move.py
git commit -m "feat(action): lateral move agent (E4)"
```

---

### Task E5: detector Agent（蓝队-入侵检测）

**Files:**
- Create: `aegisos_agents/action/detector/__init__.py`
- Create: `aegisos_agents/action/detector/agent.py`
- Test: `tests/aegisos_agents/action/test_detector.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`Alert`）、`ModelProvider`
- Produces: `DetectorAgent.detect(event_stream: list[dict]) -> list[Alert]`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_detector.py
from agents.action.detector.agent import DetectorAgent
from agents.tools.llms.mock_provider import MockProvider


def test_detect_returns_alerts():
    mock = MockProvider(responses={
        "default": '{"alerts": [{"alert_id": "a1", "severity": "high", "src": "ext", "dst": "h1", "technique": "T1110", "raw": {"port": 22}}]}'
    })
    agent = DetectorAgent(provider=mock)
    events = [{"type": "ssh_brute_force", "src": "ext", "dst": "h1"}]
    alerts = agent.detect(events)
    assert len(alerts) == 1
    assert alerts[0].severity == "high"
    assert alerts[0].technique == "T1110"


def test_detect_returns_empty_on_no_anomaly():
    mock = MockProvider(responses={"default": '{"alerts": []}'})
    agent = DetectorAgent(provider=mock)
    alerts = agent.detect([{"type": "normal_traffic"}])
    assert alerts == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_detector.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/detector/__init__.py
from .agent import DetectorAgent
__all__ = ["DetectorAgent"]
```

```python
# aegisos_agents/action/detector/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队入侵检测 Agent
from __future__ import annotations

import json

from protocol.cyber import Alert
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an intrusion detection agent. Given an event stream, "
    "return JSON with an 'alerts' array. Each alert has: alert_id, "
    "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
)


class DetectorAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def detect(self, event_stream: list[dict]) -> list[Alert]:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Detect anomalies in: {json.dumps(event_stream)}",
            model_id="detector",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                Alert(
                    alert_id=a.get("alert_id", ""),
                    severity=a.get("severity", "low"),
                    src=a.get("src", ""),
                    dst=a.get("dst", ""),
                    technique=a.get("technique", ""),
                    raw=a.get("raw", {}),
                )
                for a in data.get("alerts", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_detector.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/detector/ tests/aegisos_agents/action/test_detector.py
git commit -m "feat(action): detector agent (E5)"
```

---

### Task E6: triage Agent（蓝队-告警分诊）

**Files:**
- Create: `aegisos_agents/action/triage/__init__.py`
- Create: `aegisos_agents/action/triage/agent.py`
- Test: `tests/aegisos_agents/action/test_triage.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`Alert`）、`ModelProvider`
- Produces: `TriageAgent.triage(alerts: list[Alert]) -> list[Alert]`（去噪 + 按严重度排序）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_triage.py
from protocol.cyber import Alert
from agents.action.triage.agent import TriageAgent
from agents.tools.llms.mock_provider import MockProvider


def test_triage_sorts_by_severity():
    mock = MockProvider(responses={
        "default": '{"alerts": [{"alert_id": "a2", "severity": "critical"}, {"alert_id": "a1", "severity": "low"}]}'
    })
    agent = TriageAgent(provider=mock)
    result = agent.triage([
        Alert(alert_id="a1", severity="low"),
        Alert(alert_id="a2", severity="critical"),
    ])
    assert result[0].alert_id == "a2"  # critical first
    assert result[1].alert_id == "a1"


def test_triage_deduplicates():
    mock = MockProvider(responses={
        "default": '{"alerts": [{"alert_id": "a1", "severity": "high"}]}'
    })
    agent = TriageAgent(provider=mock)
    result = agent.triage([
        Alert(alert_id="a1", severity="high"),
        Alert(alert_id="a1", severity="high"),
    ])
    assert len(result) == 1
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_triage.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/triage/__init__.py
from .agent import TriageAgent
__all__ = ["TriageAgent"]
```

```python
# aegisos_agents/action/triage/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队告警分诊 Agent
from __future__ import annotations

import json

from protocol.cyber import Alert
from agents.tools.llms.base import LLMRequest, ModelProvider

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SYSTEM_PROMPT = (
    "You are an alert triage agent. Given alerts, return JSON with an "
    "'alerts' array containing deduplicated, severity-ordered alerts. "
    "Each alert has alert_id and severity."
)


class TriageAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def triage(self, alerts: list[Alert]) -> list[Alert]:
        alerts_desc = json.dumps([
            {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
            for a in alerts
        ])
        resp = self._provider.complete(LLMRequest(
            prompt=f"Triage these alerts: {alerts_desc}",
            model_id="triage",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
        ))
        if not resp.ok:
            return alerts  # fallback: return original
        try:
            data = json.loads(resp.text)
            ordered_ids = [a.get("alert_id", "") for a in data.get("alerts", [])]
            alert_map = {a.alert_id: a for a in alerts}
            result = [alert_map[aid] for aid in ordered_ids if aid in alert_map]
            return result if result else alerts
        except (json.JSONDecodeError, KeyError):
            return alerts
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_triage.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/triage/ tests/aegisos_agents/action/test_triage.py
git commit -m "feat(action): triage agent (E6)"
```

---

### Task E7: threat_hunt Agent（蓝队-威胁狩猎）

**Files:**
- Create: `aegisos_agents/action/threat_hunt/__init__.py`
- Create: `aegisos_agents/action/threat_hunt/agent.py`
- Test: `tests/aegisos_agents/action/test_threat_hunt.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`Alert`）、`ModelProvider`
- Produces: `ThreatHuntAgent.hunt(alerts: list[Alert]) -> list[dict]`（狩猎假设）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_threat_hunt.py
from protocol.cyber import Alert
from agents.action.threat_hunt.agent import ThreatHuntAgent
from agents.tools.llms.mock_provider import MockProvider


def test_hunt_returns_hypotheses():
    mock = MockProvider(responses={
        "default": '{"hypotheses": [{"hypothesis": "lateral movement via SMB", "confidence": 0.8, "technique": "T1021"}]}'
    })
    agent = ThreatHuntAgent(provider=mock)
    result = agent.hunt([Alert(alert_id="a1", severity="high", technique="T1110")])
    assert len(result) == 1
    assert result[0]["technique"] == "T1021"
    assert result[0]["confidence"] == 0.8


def test_hunt_returns_empty_on_no_threat():
    mock = MockProvider(responses={"default": '{"hypotheses": []}'})
    agent = ThreatHuntAgent(provider=mock)
    result = agent.hunt([])
    assert result == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_threat_hunt.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/threat_hunt/__init__.py
from .agent import ThreatHuntAgent
__all__ = ["ThreatHuntAgent"]
```

```python
# aegisos_agents/action/threat_hunt/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队威胁狩猎 Agent
from __future__ import annotations

import json

from protocol.cyber import Alert
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a threat hunting agent. Given prioritized alerts, generate "
    "hunting hypotheses. Return JSON with a 'hypotheses' array. Each "
    "hypothesis has: hypothesis (str), confidence (float 0-1), technique (ATT&CK id)."
)


class ThreatHuntAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def hunt(self, alerts: list[Alert]) -> list[dict]:
        alerts_desc = json.dumps([
            {"alert_id": a.alert_id, "severity": a.severity, "technique": a.technique}
            for a in alerts
        ])
        resp = self._provider.complete(LLMRequest(
            prompt=f"Generate hunting hypotheses for: {alerts_desc}",
            model_id="threat-hunt",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.5,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return data.get("hypotheses", [])
        except (json.JSONDecodeError, KeyError):
            return []
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_threat_hunt.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/threat_hunt/ tests/aegisos_agents/action/test_threat_hunt.py
git commit -m "feat(action): threat hunt agent (E7)"
```

---

### Task E8: ir_planner Agent（蓝队-响应规划）

**Files:**
- Create: `aegisos_agents/action/ir_planner/__init__.py`
- Create: `aegisos_agents/action/ir_planner/agent.py`
- Test: `tests/aegisos_agents/action/test_ir_planner.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`DefenseAction`/`ResponsePlan`）、`ModelProvider`
- Produces: `IRPlannerAgent.plan_response(hypotheses: list[dict]) -> ResponsePlan`

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_ir_planner.py
from agents.action.ir_planner.agent import IRPlannerAgent
from agents.tools.llms.mock_provider import MockProvider


def test_plan_response_returns_response_plan():
    mock = MockProvider(responses={
        "default": '{"plan_id": "rp1", "actions": [{"action_id": "d1", "kind": "isolate", "target": "h1", "rationale": "stop lateral move"}], "confidence": 0.9, "rollback": {"enabled": true, "steps": ["reconnect"]}}'
    })
    agent = IRPlannerAgent(provider=mock)
    hypotheses = [{"hypothesis": "lateral movement", "confidence": 0.8, "technique": "T1021"}]
    plan = agent.plan_response(hypotheses)
    assert plan.plan_id == "rp1"
    assert len(plan.actions) == 1
    assert plan.actions[0]["kind"] == "isolate"
    assert plan.confidence == 0.9
    assert plan.rollback["enabled"] is True


def test_plan_response_has_empty_actions_on_no_hypotheses():
    mock = MockProvider(responses={
        "default": '{"plan_id": "rp0", "actions": [], "confidence": 0.0, "rollback": {"enabled": false}}'
    })
    agent = IRPlannerAgent(provider=mock)
    plan = agent.plan_response([])
    assert plan.actions == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_ir_planner.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/ir_planner/__init__.py
from .agent import IRPlannerAgent
__all__ = ["IRPlannerAgent"]
```

```python
# aegisos_agents/action/ir_planner/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队响应规划 Agent
from __future__ import annotations

import json

from protocol.cyber import ResponsePlan
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)


class IRPlannerAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def plan_response(self, hypotheses: list[dict]) -> ResponsePlan:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Plan response for: {json.dumps(hypotheses)}",
            model_id="ir-planner",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ))
        if not resp.ok:
            return ResponsePlan(plan_id="", confidence=0.0)
        try:
            data = json.loads(resp.text)
            return ResponsePlan(
                plan_id=data.get("plan_id", ""),
                actions=data.get("actions", []),
                confidence=data.get("confidence", 0.0),
                rollback=data.get("rollback", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return ResponsePlan(plan_id="", confidence=0.0)
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_ir_planner.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/ir_planner/ tests/aegisos_agents/action/test_ir_planner.py
git commit -m "feat(action): ir planner agent (E8)"
```

---

### Task E9: forensics Agent（蓝队-取证）

**Files:**
- Create: `aegisos_agents/action/forensics/__init__.py`
- Create: `aegisos_agents/action/forensics/agent.py`
- Test: `tests/aegisos_agents/action/test_forensics.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`ResponsePlan`）、`ModelProvider`
- Produces: `ForensicsAgent.investigate(plan: ResponsePlan) -> dict`（取证报告）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_forensics.py
from protocol.cyber import ResponsePlan
from agents.action.forensics.agent import ForensicsAgent
from agents.tools.llms.mock_provider import MockProvider


def test_investigate_returns_report():
    mock = MockProvider(responses={
        "default": '{"report_id": "f1", "root_cause": "unpatched ssh", "timeline": [{"ts": "t1", "event": "brute force"}], "recommendations": ["patch ssh"]}'
    })
    agent = ForensicsAgent(provider=mock)
    plan = ResponsePlan(plan_id="rp1", confidence=0.9)
    report = agent.investigate(plan)
    assert report["report_id"] == "f1"
    assert report["root_cause"] == "unpatched ssh"
    assert len(report["timeline"]) == 1
    assert "patch ssh" in report["recommendations"]
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_forensics.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/forensics/__init__.py
from .agent import ForensicsAgent
__all__ = ["ForensicsAgent"]
```

```python
# aegisos_agents/action/forensics/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队取证 Agent
from __future__ import annotations

import json

from protocol.cyber import ResponsePlan
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a digital forensics agent. Given a response plan, return JSON "
    "with report_id, root_cause (str), timeline (array of {ts, event}), "
    "recommendations (array of str)."
)


class ForensicsAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def investigate(self, plan: ResponsePlan) -> dict:
        plan_desc = json.dumps({
            "plan_id": plan.plan_id,
            "actions": plan.actions,
            "confidence": plan.confidence,
        })
        resp = self._provider.complete(LLMRequest(
            prompt=f"Investigate: {plan_desc}",
            model_id="forensics",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ))
        if not resp.ok:
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_forensics.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/forensics/ tests/aegisos_agents/action/test_forensics.py
git commit -m "feat(action): forensics agent (E9)"
```

---

### Task E10: critic Agent（紫队-对抗性批判）

**Files:**
- Create: `aegisos_agents/action/critic/__init__.py`
- Create: `aegisos_agents/action/critic/agent.py`
- Test: `tests/aegisos_agents/action/test_critic.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`AttackChain`/`ResponsePlan`）、`ModelProvider`
- Produces: `CriticAgent.critique(target: dict, side: str) -> dict`（反驳/校验结果；side="red"|"blue"）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_critic.py
from agents.action.critic.agent import CriticAgent
from agents.tools.llms.mock_provider import MockProvider


def test_critique_red_chain_flags_issue():
    mock = MockProvider(responses={
        "default": '{"valid": false, "issues": ["missing persistence step"], "severity": "medium", "suggestion": "add T1053 for persistence"}'
    })
    agent = CriticAgent(provider=mock)
    result = agent.critique({"chain_id": "c1", "steps": []}, side="red")
    assert result["valid"] is False
    assert "missing persistence step" in result["issues"]
    assert result["severity"] == "medium"


def test_critique_blue_plan_passes():
    mock = MockProvider(responses={
        "default": '{"valid": true, "issues": [], "severity": "none", "suggestion": ""}'
    })
    agent = CriticAgent(provider=mock)
    result = agent.critique({"plan_id": "rp1"}, side="blue")
    assert result["valid"] is True
    assert result["issues"] == []
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_critic.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/critic/__init__.py
from .agent import CriticAgent
__all__ = ["CriticAgent"]
```

```python
# aegisos_agents/action/critic/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 紫队对抗性批判 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT_RED = (
    "You are a red team critic. Given an attack chain, validate it against "
    "ATT&CK rules. Return JSON: valid (bool), issues (array), severity "
    "(none|low|medium|high), suggestion (str)."
)
SYSTEM_PROMPT_BLUE = (
    "You are a blue team critic. Given a response plan, validate it for "
    "completeness and correctness. Return JSON: valid (bool), issues (array), "
    "severity (none|low|medium|high), suggestion (str)."
)


class CriticAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def critique(self, target: dict, side: str = "red") -> dict:
        sys_prompt = SYSTEM_PROMPT_RED if side == "red" else SYSTEM_PROMPT_BLUE
        resp = self._provider.complete(LLMRequest(
            prompt=f"Critique: {json.dumps(target)}",
            model_id="critic",
            system_prompt=sys_prompt,
            temperature=0.3,
        ))
        if not resp.ok:
            return {"valid": False, "issues": ["LLM error"], "severity": "high", "suggestion": ""}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"valid": False, "issues": ["parse error"], "severity": "high", "suggestion": ""}
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_critic.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/critic/ tests/aegisos_agents/action/test_critic.py
git commit -m "feat(action): critic agent (E10)"
```

---

### Task E11: reviewer Agent（紫队-一致性审查）

**Files:**
- Create: `aegisos_agents/action/reviewer/__init__.py`
- Create: `aegisos_agents/action/reviewer/agent.py`
- Test: `tests/aegisos_agents/action/test_reviewer.py`

**Interfaces:**
- Consumes: `ModelProvider`
- Produces: `ReviewerAgent.review(artifacts: dict) -> dict`（一致性结论）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/action/test_reviewer.py
from agents.action.reviewer.agent import ReviewerAgent
from agents.tools.llms.mock_provider import MockProvider


def test_review_returns_consistent():
    mock = MockProvider(responses={
        "default": '{"consistent": true, "findings": [], "overall_assessment": "all artifacts align"}'
    })
    agent = ReviewerAgent(provider=mock)
    result = agent.review({"chain": {}, "plan": {}, "report": {}})
    assert result["consistent"] is True
    assert result["overall_assessment"] == "all artifacts align"


def test_review_flags_inconsistency():
    mock = MockProvider(responses={
        "default": '{"consistent": false, "findings": ["chain targets h1 but plan isolates h2"], "overall_assessment": "mismatch"}'
    })
    agent = ReviewerAgent(provider=mock)
    result = agent.review({"chain": {}, "plan": {}})
    assert result["consistent"] is False
    assert len(result["findings"]) == 1
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/action/test_reviewer.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/action/reviewer/__init__.py
from .agent import ReviewerAgent
__all__ = ["ReviewerAgent"]
```

```python
# aegisos_agents/action/reviewer/agent.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 紫队一致性审查 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a consistency reviewer. Given multiple artifacts (attack chain, "
    "response plan, forensic report), check if they are mutually consistent. "
    "Return JSON: consistent (bool), findings (array of str), "
    "overall_assessment (str)."
)


class ReviewerAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def review(self, artifacts: dict) -> dict:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Review consistency: {json.dumps(artifacts, default=str)}",
            model_id="reviewer",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return {"consistent": False, "findings": ["LLM error"], "overall_assessment": "error"}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"consistent": False, "findings": ["parse error"], "overall_assessment": "error"}
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/action/test_reviewer.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/action/reviewer/ tests/aegisos_agents/action/test_reviewer.py
git commit -m "feat(action): reviewer agent (E11)"
```

---

### Task E12: 神经-符号闭环集成

> 神经侧（LLM）生成攻击链假设 -> 符号侧用 ATT&CK 规则校验 -> 不通过则反馈约束 -> LLM 修正 -> 再校验，直至一致或预算耗尽（14 S7）。

**Files:**
- Create: `aegisos_agents/perception/reasoning/__init__.py`
- Create: `aegisos_agents/perception/reasoning/neuro_symbolic.py`
- Test: `tests/aegisos_agents/perception/test_neuro_symbolic.py`

**Interfaces:**
- Consumes: `protocol/cyber.py`（`AttackChain`/`AttackStep`）、`ModelProvider`（LLM 生成假设）
- Produces: `NeuroSymbolicLoop.validate_and_fix(chain: AttackChain, rules: list[dict], max_iterations: int) -> AttackChain`（校验不通过则反馈约束让 LLM 修正）

- [ ] **Step 1: 写失败测试**

```python
# tests/aegisos_agents/perception/test_neuro_symbolic.py
from protocol.cyber import AttackChain, AttackStep
from agents.perception.reasoning.neuro_symbolic import NeuroSymbolicLoop, validate_chain
from agents.tools.llms.mock_provider import MockProvider


def test_validate_chain_passes_valid_techniques():
    chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110", "T1021", "T1053"]}
    assert validate_chain(chain, rules) == []


def test_validate_chain_flags_invalid_technique():
    chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    issues = validate_chain(chain, rules)
    assert len(issues) == 1
    assert "T9999" in issues[0]


def test_loop_fixes_invalid_chain():
    # First call returns invalid technique, second call returns fixed
    mock = MockProvider(responses={
        "default": '{"chain_id": "c1", "target": "h1", "steps": [{"step_id": "s1", "technique": "T1110", "from_asset": "ext", "to_asset": "h1", "success": true}], "status": "validated"}'
    })
    loop = NeuroSymbolicLoop(provider=mock)
    bad_chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    fixed = loop.validate_and_fix(bad_chain, rules, max_iterations=3)
    assert fixed.steps[0].technique == "T1110"


def test_loop_returns_original_after_max_iterations():
    mock = MockProvider(responses={
        "default": '{"chain_id": "c1", "steps": [{"step_id": "s1", "technique": "T9999"}], "status": "failed"}'
    })
    loop = NeuroSymbolicLoop(provider=mock)
    bad_chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    result = loop.validate_and_fix(bad_chain, rules, max_iterations=1)
    assert result.steps[0].technique == "T9999"
```

- [ ] **Step 2: 跑确认失败**

Run: `pytest tests/aegisos_agents/perception/test_neuro_symbolic.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# aegisos_agents/perception/reasoning/__init__.py
from .neuro_symbolic import NeuroSymbolicLoop, validate_chain
__all__ = ["NeuroSymbolicLoop", "validate_chain"]
```

```python
# aegisos_agents/perception/reasoning/neuro_symbolic.py
# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 神经-符号闭环
from __future__ import annotations

import json

from protocol.cyber import AttackChain, AttackStep
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an attack chain generator. Given a previous chain with "
    "validation issues, generate a corrected chain. Return JSON with "
    "chain_id, target, steps (array of {step_id, technique, from_asset, "
    "to_asset, success}), status."
)


def validate_chain(chain: AttackChain, rules: dict) -> list[str]:
    """Symbolic validation: check techniques against allowed list."""
    issues: list[str] = []
    allowed = rules.get("allowed_techniques", [])
    for step in chain.steps:
        if step.technique and step.technique not in allowed:
            issues.append(f"Technique {step.technique} not in allowed list")
    return issues


class NeuroSymbolicLoop:
    """Neural (LLM) generates -> Symbolic validates -> feedback -> fix loop."""

    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def validate_and_fix(
        self,
        chain: AttackChain,
        rules: dict,
        max_iterations: int = 3,
    ) -> AttackChain:
        current = chain
        for _ in range(max_iterations):
            issues = validate_chain(current, rules)
            if not issues:
                return current
            current = self._regenerate(current, issues, rules)
        return current

    def _regenerate(
        self,
        chain: AttackChain,
        issues: list[str],
        rules: dict,
    ) -> AttackChain:
        chain_desc = json.dumps({
            "chain_id": chain.chain_id,
            "steps": [
                {"step_id": s.step_id, "technique": s.technique,
                 "from_asset": s.from_asset, "to_asset": s.to_asset}
                for s in chain.steps
            ],
        })
        feedback = f"Issues: {issues}. Allowed techniques: {rules.get('allowed_techniques', [])}. Fix the chain."
        resp = self._provider.complete(LLMRequest(
            prompt=f"Previous chain: {chain_desc}. {feedback}",
            model_id="neuro-symbolic",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ))
        if not resp.ok:
            return chain
        try:
            data = json.loads(resp.text)
            steps = [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),
                )
                for s in data.get("steps", [])
            ]
            return AttackChain(
                chain_id=data.get("chain_id", chain.chain_id),
                target=data.get("target", chain.target),
                steps=steps,
                status=data.get("status", "regenerated"),
            )
        except (json.JSONDecodeError, KeyError):
            return chain
```

- [ ] **Step 4: 跑确认通过**

Run: `pytest tests/aegisos_agents/perception/test_neuro_symbolic.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add aegisos_agents/perception/reasoning/ tests/aegisos_agents/perception/test_neuro_symbolic.py
git commit -m "feat(perception): neuro-symbolic loop (E12)"
```

---

## 全量验证

完成所有 Phase A-E 后，运行全量测试确保无回归：

- [ ] **全量测试**

Run: `pytest tests/ -v`
Expected: All passed (A1:6 + B1:4 + B2:3 + C1:3 + C2:4 + C3:3 + D1:4 + D2:5 + E1-E12: ~20 = ~52 tests)

- [ ] **代码质量检查**

Run: `ruff format && ruff check --fix && mypy`
Expected: No errors

- [ ] **提交 CHANGELOG**

```bash
git add developer/CHANGELOG.md
git commit -m "docs: update CHANGELOG for Phase A-E completion"
```

---

## Self-Review

### 1. Spec 覆盖检查

| 14 号方案章节 | 对应 Task | 覆盖状态 |
|--------------|-----------|---------|
| S1: Protocol 攻防类型 | A1 | ✅ 8 类型全覆盖 |
| S2: 超长程记忆压缩 | B1 | ✅ 压缩器 + kind/recent 字段 |
| S3: 记忆唤醒 | B2 | ✅ recaller 按相关性+时间唤醒 |
| S4: 活跃子图拓扑 | C1 | ✅ status 字段 + 活跃子图计算 |
| S5: 低熵稀疏路由 | C2 | ✅ Top-K + 熵计算 + 非全广播验证 |
| S6: 异构选举 | C3 | ✅ 多维度加权选举 |
| S7: 端边云调度 | D1 | ✅ privacy/latency_budget + 端优先 |
| S8: 多模型兼容 | D2 | ✅ 4 Provider + ModelRouter |
| S9: 红队 Agent | E1-E4 | ✅ recon/vuln/exploit/lateral |
| S10: 蓝队 Agent | E5-E9 | ✅ detector/triage/hunt/ir/forensics |
| S11: 紫队 Agent | E10-E11 | ✅ critic/reviewer |
| S12: 神经-符号闭环 | E12 | ✅ LLM→符号校验→反馈→修正 |

**覆盖结论：** 14 号方案 S1-S12 全部有对应 Task，无遗漏。

### 2. Placeholder 扫描

- ✅ 无 `TODO`/`FIXME`/`TBD`/`...` 占位符
- ✅ 所有 Step 3 实现代码完整，非伪代码
- ✅ 所有 Step 1 测试代码完整，可执行
- ✅ MockProvider responses 在 D2 Task 中定义，后续 E1-E12 引用一致

### 3. 类型一致性检查

| protocol 字段 | 测试引用 | 实现引用 | 一致 |
|-------------|---------|---------|------|
| `MemoryPacket.kind` | B1 test | B1 impl | ✅ `str = "normal"` |
| `MemoryPacket.recent` | B1 test | B1 impl | ✅ `bool = False` |
| `GraphNode.status` | C1 test | C1 impl | ✅ `str = "active"` |
| `Task.privacy` | D1 test | D1 impl | ✅ `str = "standard"` |
| `Task.latency_budget` | D1 test | D1 impl | ✅ `float = 10.0` |
| `Asset.asset_id` | A1/E1 | A1 impl | ✅ |
| `Alert.alert_id` | A1/E5 | A1 impl | ✅ |
| `AttackChain.chain_id` | A1/E3/E12 | A1 impl | ✅ |
| `AttackStep.technique` | A1/E3/E12 | A1 impl | ✅ |
| `ResponsePlan.plan_id` | A1/E8 | A1 impl | ✅ |
| `VulnFinding.finding_id` | A1/E2 | A1 impl | ✅ |
| `DefenseAction.action_id` | A1/E8 | A1 impl | ✅ |
| `ThreatIntel.intel_id` | A1 | A1 impl | ✅ |
| `ModelProvider.complete` | D2/E1-E12 | D2 impl | ✅ 签名 `(LLMRequest) -> LLMResponse` |
| `MockProvider(responses=)` | E1-E12 | D2 impl | ✅ `dict[str, str]` |

**类型一致性结论：** 所有跨 Task 引用的 protocol 字段、ModelProvider 接口、MockProvider 构造参数均一致，无断裂。

### 4. 依赖顺序验证

```
A1 (cyber types) ← 无依赖
B1 (compactor) ← A1? No, 仅依赖 protocol/memory.py
B2 (recaller) ← B1 (使用 MemoryPacket.kind/recent)
C1 (topology) ← 无依赖 (仅 protocol/graph.py)
C2 (router) ← C1 (使用活跃子图)
C3 (election) ← C1 (使用 GraphNode)
D1 (scheduler) ← 无依赖 (仅 protocol/scheduler.py)
D2 (model layer) ← 无依赖 (aegisos_agents/tools/llms/)
E1-E4 (red) ← A1 (cyber types) + D2 (ModelProvider)
E5-E9 (blue) ← A1 + D2
E10-E11 (purple) ← A1 + D2
E12 (neuro-symbolic) ← A1 + D2
```

**依赖顺序结论：** A1 和 D2 是 E-phase 的前置依赖；B2 依赖 B1；C2/C3 依赖 C1。执行顺序 A1→B1→B2→C1→C2→C3→D1→D2→E1..E12 正确，无循环依赖。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-04-agents-phase-ae.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?