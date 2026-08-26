# P2 感知层补全 — 设计文档

> 日期：2026-08-01 · 状态：设计完成，待评审 · 关联：`developer/plan.md` §3 P2

## 1. 目标与范围

### 1.1 目标

补全 `aegisos_agents/perception/` 下 2 个空模块：
- `context/` — 上下文窗口管理（Token 预算、裁剪、会话隔离）
- `reflection/` — 运行时反思（批判、反馈评分，区别于 `memory/reflection`）

### 1.2 与已有模块的关系

| 模块 | 评估对象 | 触发时机 | 产出 |
|------|---------|----------|------|
| `memory/reflection` ✅ | 历史决策记忆（MemoryPacket） | recall 重排序 / write 预评估 | 评分 float |
| **`perception/reflection`** 🔲 | 当前任务执行结果（runtime output） | Agent 执行完成后 | Feedback → 写回 memory/reflection |

### 1.3 不变约束

- `protocol/` 类型**零改动**（复用现有 MemoryPacket / Task / Session）
- 现有 `perception/reasoning/` **零改动**
- 纯算法实现，不调 LLM（与 AGENT.md 标注一致）
- 遵循 `developer/specs/11_AI_CODING_SPEC.md`

---

## 2. 架构总览

```
perception (v2)
├── [已有] reasoning/
│   ├── strategies/plan_mode.py   ✅
│   ├── strategies/goal_mode.py   ✅
│   └── neuro_symbolic.py         ✅
│
├── [新增] context/
│   ├── window.py    → TokenBudget    Token 估算 + 裁剪
│   └── manager.py   → ContextManager 会话上下文生命周期
│
└── [新增] reflection/
    ├── critic.py    → ExecutionCritic 批判检查
    ├── scoring.py   → OutputScorer    多维评分
    └── feedback.py  → FeedbackLoop    整合 → 写回 memory/reflection
```

### 数据流

```
Agent 执行完成
    ↓
perception/reflection/
    ├─ ExecutionCritic.critique(output) → list[Critique]
    ├─ OutputScorer.score(output, critiques) → OutputScore
    └─ FeedbackLoop.reflect(agent_id, task_id, output, score)
        ├─ memory/reflection.tag_outcome(task_id, "success"/"failure")
        └─ memory/reflection.record_reference(task_id)

perception/context/ (推理前)
    └─ ContextManager.pack(session_id, budget)
        ├─ 从 memory/working 拉当前上下文
        ├─ TokenBudget.trim(packets, budget) 裁剪
        └─ 返回 Context 注入 Agent prompt
```

---

## 3. 模块详细设计

### 3.1 context/window.py — TokenBudget

**类**：`TokenBudget`

**token 估算**：
- `estimate(text: str) -> int`：`len(text) // 4 + 1`
- `estimate_packets(packets: list[MemoryPacket]) -> int`：汇总每条 memory 的 summary + working + episodic 字段字符数

**裁剪策略 `trim(packets, budget) -> list`**：
1. 估算当前总量，未超预算直接返回
2. `keep = [m for m in packets if m.recent or m.kind == "decision"]`
3. `rest = [m for m in packets if m not in keep]`
4. 仍有 rest 且超出预算：保留头尾各 `budget//2` 个字符，中间标记为 truncation
5. 生成一条 truncation digest 摘要

**接口**：
- `estimate(text: str) -> int`
- `estimate_packets(packets: list[MemoryPacket]) -> int`
- `trim(packets: list[MemoryPacket], budget: int) -> list[MemoryPacket]`

---

### 3.2 context/manager.py — ContextManager

**类**：`ContextManager`

**上下文生命周期**：

```
open(session_id, memory_store)
    → 初始化会话上下文（绑定 memory/working 引用）
    → 返回空 Context

close(session_id)
    → 清理该会话的本地上下文缓存
    → 不清理 memory/working（由 MemoryStore.end_session 负责）

pack(session_id, budget: int)
    → 从 memory/working 拉当前会话的 working stack
    → 调用 TokenBudget.trim() 裁剪
    → 返回 Context dict

switch(from_sid, to_sid)
    → 保存当前会话上下文 → 加载目标会话上下文

isolate(session_id)
    → 隔离单个会话的完整上下文快照
```

**Context 数据结构**：
```python
@dataclass
class Context:
    session_id: str
    working_packets: list  # 裁剪后的 MemoryPacket 列表
    token_usage: int       # 实际 token 使用量
    budget_remaining: int  # 剩余 token 预算
    truncated: bool        # 是否发生过裁剪
```

**接口**：
- `open(session_id: str, memory_store: MemoryStore) -> Context`
- `close(session_id: str)`
- `pack(session_id: str, budget: int = 4096) -> Context`
- `switch(from_sid: str, to_sid: str) -> Context`
- `isolate(session_id: str) -> Context | None`

**依赖**：`MemoryStore`（只读 working 层）

---

### 3.3 reflection/critic.py — ExecutionCritic

**类**：`ExecutionCritic`

**四维批判检查**：

| 维度 | 检查内容 | 严重度 |
|------|----------|:------:|
| 结构完整性 | 必需字段是否缺失、类型是否正确 | high |
| 数据合理性 | 值范围（如 ports: 1-65535）、IP 格式 | medium |
| 逻辑一致性 | 输入与输出是否矛盾 | medium |
| 空结果检测 | 空列表/空对象（可能执行失败） | low |

**数据类型**：
```python
@dataclass
class Critique:
    dimension: str      # completeness / sanity / consistency / emptiness
    severity: str       # high / medium / low
    message: str        # 人类可读的问题描述
    field: str = ""     # 关联字段名（可选）
```

**接口**：
- `critique(output: dict, expected_fields: list[str] | None = None) -> list[Critique]`
- `has_blocker(critiques: list[Critique]) -> bool` — 是否有 high 严重度问题

---

### 3.4 reflection/scoring.py — OutputScorer

**类**：`OutputScorer`

**四维评分**（每维 0.0-1.0）：

| 维度 | 计算方式 | 权重 |
|------|----------|:----:|
| completeness | `filled_fields / expected_fields`（字段填充率） | 0.3 |
| correctness | `1.0 - min(critique_count / 10, 1.0)`（批判越少分越高） | 0.3 |
| efficiency | 基于步骤数/冗余度（`1.0 / (1 + steps/10)`） | 0.2 |
| safety | 破坏性操作标记检测（无标记=1.0，有标记=0.5） | 0.2 |

**综合分**：`0.3×completeness + 0.3×correctness + 0.2×efficiency + 0.2×safety`

**数据类型**：
```python
@dataclass
class OutputScore:
    completeness: float
    correctness: float
    efficiency: float
    safety: float
    overall: float          # 加权综合分
    grade: str              # success(>=0.7) / pass(>=0.5) / fail(<0.5)
```

**接口**：
- `score(output: dict, critiques: list[Critique], expected_fields: list[str] | None = None) -> OutputScore`
- `quick_score(output: dict) -> OutputScore` — 不依赖 critique 的快速评分（仅 completeness + safety）

---

### 3.5 reflection/feedback.py — FeedbackLoop

**类**：`FeedbackLoop`

**反思闭环**：

```
reflect(agent_id, task_id, output, expected_fields)
    1. ExecutionCritic.critique(output, expected_fields) → critiques
    2. OutputScorer.score(output, critiques, expected_fields) → score
    3. 生成 FeedbackRecord
    4. 写回 memory/reflection:
       - tag_outcome(task_id, score.grade)
       - record_reference(task_id)
    5. 返回 FeedbackRecord
```

**数据类型**：
```python
@dataclass
class FeedbackRecord:
    agent_id: str
    task_id: str
    score: OutputScore
    critiques: list[Critique]
    grade: str             # success / pass / fail
    summary: str           # 人类可读的反馈摘要
```

**接口**：
- `reflect(agent_id: str, task_id: str, output: dict, expected_fields: list[str] | None = None, reflection_engine: ReflectionEngine | None = None) -> FeedbackRecord`
- `batch_reflect(results: list[dict]) -> list[FeedbackRecord]` — 批量反思

**依赖**：`memory/reflection` ReflectionEngine（可选，反馈写回）

---

## 4. 与 MemoryStore 的对接

```
ContextManager.open(session_id, memory_store)
    → 从 memory_store.working.get(session_id) 读取工作记忆

ContextManager.pack() 超预算时
    → 调用 memory_store.compress(session_id, budget) 触发记忆压缩

FeedbackLoop.reflect()
    → 调用 reflection_engine.tag_outcome(task_id, grade)
    → 调用 reflection_engine.record_reference(task_id)
```

---

## 5. 测试计划

| 文件 | 用例数 | 关键场景 |
|------|:------:|----------|
| `context/window.py` | 5 | token 估算精度 + trim 保留决策+最近 + 空列表 + 充足预算不裁剪 + 边界 |
| `context/manager.py` | 5 | open→pack→close 生命周期 + switch 切换 + isolate 隔离 |
| `reflection/critic.py` | 5 | 四维检查 + 空输出检测 + 完美输出 + has_blocker 判断 |
| `reflection/scoring.py` | 5 | 四维评分 + 加权综合 + quick_score + 满分/零分边界 |
| `reflection/feedback.py` | 5 | reflect 完整链路 + 写回 memory/reflection + 批量 + 无 engine 降级 |

**总计**：25 新测试

---

## 6. 文件清单

```
新增（10 个）:
aegisos_agents/perception/context/__init__.py
aegisos_agents/perception/context/window.py
aegisos_agents/perception/context/manager.py
aegisos_agents/perception/reflection/__init__.py
aegisos_agents/perception/reflection/critic.py
aegisos_agents/perception/reflection/scoring.py
aegisos_agents/perception/reflection/feedback.py
tests/aegisos_agents/perception/test_context.py
tests/aegisos_agents/perception/test_reflection.py

修改（3 个）:
aegisos_agents/perception/AGENT.md  — 更新子模块状态
developer/plan.md                   — 勾选完成
developer/CHANGELOG.md              — 记录变更
```

---

## 7. 验收标准

1. 2 个模块的 `__init__.py` + 核心类文件全部创建（5 个 .py）
2. 25 新测试全部通过
3. 3 已有 perception 测试无回归（test_plan_mode / test_goal_mode / test_neuro_symbolic）
4. `ruff format && ruff check --fix` 零告警
5. `aegisos_agents/perception/AGENT.md` 更新
6. `developer/CHANGELOG.md` 记录变更
