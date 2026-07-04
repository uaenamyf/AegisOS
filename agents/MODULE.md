# agents/ 模块实现文档

> 智能体域 — 系统的认知核心，五层架构：感知 → 规划 → 行动 → 记忆 → 工具。

📁 规范：[`08_AGENT_SPEC.md`](../developer/specs/08_AGENT_SPEC.md) · 模块规范：[`AGENT.md`](AGENT.md) · 公共接口：[`api/__init__.py`](api/__init__.py)

---

## 五层架构总览

```
agents/
├── perception/   感知 — context · reasoning · reflection
├── planning/      规划 — engine/(topology · router · scheduler) · planner · orchestrator
├── action/        行动 — 11 个红蓝紫攻防 Agent + execution
├── memory/        记忆 — compression · recall + 10 子模块
├── tools/         工具 — llms(多模型) · prompts · runtime
└── api/           公共接口 — 5 个 Protocol + 3 个 DI 端口
```

---

## agents/planning/ — 规划引擎

### ✅ 已实现

#### `engine/topology/topology.py` — 活跃子图

```python
def active_subgraph(graph: Graph, required_capability: str) -> Graph
```

**逻辑**：过滤 `status in {active, degraded}` 且 `required_capability in node.capabilities` 的节点，返回子图。

**测试**：2 个 — capability 过滤 · degraded 包含

---

#### `engine/router/router.py` — 低熵稀疏路由 Top-K

```python
def route(message: Message, topology: Graph, required_capability: str) -> list[NodeRef]
```

**逻辑**：
1. 调用 `active_subgraph()` 获取候选
2. 按 `_affinity(message, node) - _load_penalty(node)` 排序
   - affinity = `success_rate`（默认 1.0）
   - load_penalty = `latency`（默认 0.0）
3. 返回 Top-3（`TOP_K = 3`），**非全广播**

**测试**：3 个 — 稀疏性 · 跳过 idle · 偏好高成功率

---

#### `engine/router/election.py` — 异构选举

```python
def elect(task_features: list[float], instances: list[GraphNode],
          capability_vectors: dict[str, list[float]]) -> NodeRef
```

**逻辑**：计算 `task_features` 与每个实例 `capability_vector` 的点积，选最高分。

**测试**：2 个 — 最优匹配 · 翻转特征后选另一个

---

#### `engine/scheduler/scheduler.py` — 端边云卸载调度

```python
@dataclass
class Model:
    model_id: str
    tier: str       # edge | cloud
    size: str       # small | medium | large
    capabilities: list

def schedule(task: Task, models: list[Model], required_capability: str | None = None) -> Model
```

**调度规则**：
1. `task.privacy == "local"` → 必须 edge
2. `task.latency_budget < 5.0` (EDGE_THRESHOLD) → 偏好 edge
3. 否则 → 偏好 cloud
4. 按 `required_capability` 过滤

**测试**：3 个 — privacy=local 选 edge · 低延迟选 edge · 高延迟选 cloud

---

### 🔲 未实现（仅 AGENT.md）

| 目录 | 计划功能 |
|------|---------|
| `planner/` | 规划器：将 goal 分解为 Plan(DAG) |
| `orchestrator/` | 编排器：协调多 Agent 执行 |
| `engine/workflow/` | 工作流引擎：DAG 执行 |
| `engine/eventbus/` | 事件总线实现（publish/subscribe） |

> **影响**：11 个 Agent 目前只能被 API 逐个手动调用，无法自动协同。

---

## agents/memory/ — 记忆子系统

### ✅ 已实现

#### `compression/compactor.py` — 上下文压缩

```python
def compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]
```

**逻辑**：
1. `_token_estimate()` 估算 context 总 token 数（summary + working + episodic 长度 / 4）
2. 未超 budget → 原样返回
3. 超预算 → 保留 `kind == "decision"` 和 `recent == True` 的包
4. 其余合并为单个 `MemoryPacket(kind="digest")`，summary 为 `" | ".join()`

**测试**：4 个 — 保留 decision+recent+digest · budget 内 noop · 全 decision 全保留 · 空列表

---

#### `recall/recaller.py` — 记忆唤醒

```python
def recall(trigger: str, episodic: list[MemoryPacket], vector: list[MemoryPacket]) -> list[MemoryPacket]
```

**逻辑**：
1. trigger 转小写
2. 在 episodic + vector 中匹配 summary 包含 trigger 的包
3. `kind == "decision"` 优先排列
4. 返回 Top-5（`TOP_K = 5`）

**测试**：3 个 — decision 匹配 · decision 优先 · 空结果

---

### 🔲 未实现（10 个子模块，仅 AGENT.md）

| 子模块 | 计划功能 |
|--------|---------|
| `working/` | 工作记忆（当前上下文） |
| `episodic/` | 情景记忆（历史会话） |
| `semantic/` | 语义记忆（知识库） |
| `vector/` | 向量记忆（嵌入检索） |
| `archive/` | 归档（长期存储） |
| `cache/` | 缓存 |
| `checkpoint/` | 检查点 |
| `reflection/` | 反思记忆 |
| `retrieval/` | 检索引擎 |
| `snapshot/` | 快照 |
| `sync/` | 同步 |

> **影响**：B3 — 压缩/唤醒已实现但从未在 runtime 认知循环中被调用。

---

## agents/action/ — 攻防 Agent（11 个全部完成）

### 🔴 红队（4 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `recon` | [`recon/agent.py`](action/recon/agent.py) | `scan(target_range: str)` | 目标范围 → `list[Asset]` |
| `vuln_correlator` | [`vuln_correlator/agent.py`](action/vuln_correlator/agent.py) | `correlate(assets, cve_db)` | 资产+CVE → `list[VulnFinding]` |
| `exploit_planner` | [`exploit_planner/agent.py`](action/exploit_planner/agent.py) | `plan(findings)` | 漏洞 → `AttackChain` |
| `lateral_move` | [`lateral_move/agent.py`](action/lateral_move/agent.py) | `plan_moves(chain)` | 攻击链 → 横向移动步骤 |

**流程**：recon → vuln_correlator → exploit_planner → lateral_move

### 🔵 蓝队（5 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `detector` | [`detector/agent.py`](action/detector/agent.py) | `detect(events)` | 事件流 → `list[Alert]` |
| `triage` | [`triage/agent.py`](action/triage/agent.py) | `triage(alerts)` | 告警 → 按严重度排序 |
| `threat_hunt` | [`threat_hunt/agent.py`](action/threat_hunt/agent.py) | `hunt(alerts)` | 告警 → ATT&CK 假设 |
| `ir_planner` | [`ir_planner/agent.py`](action/ir_planner/agent.py) | `plan_response(hypotheses)` | 假设 → `ResponsePlan`(含 rollback) |
| `forensics` | [`forensics/agent.py`](action/forensics/agent.py) | `investigate(alert)` | 告警 → 取证报告 |

**流程**：detector → triage → threat_hunt → ir_planner → forensics

### 🟣 紫队（2 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `critic` | [`critic/agent.py`](action/critic/agent.py) | `critique(chain_or_plan)` | 红蓝产出 → 对抗性反驳 |
| `reviewer` | [`reviewer/agent.py`](action/reviewer/agent.py) | `review(inputs)` | 全部产出 → 一致性审查 |

**实现模式**：每个 Agent 接收 `ModelProvider`，通过 LLM 生成结构化 JSON → 解析为 protocol 类型。Mock 测试使用 `MockProvider`。

**测试**：15 个（每个 Agent 1-2 个测试），全部通过。

---

## agents/perception/ — 感知层

### ✅ 已实现

#### `reasoning/neuro_symbolic.py` — 神经符号闭环

```python
def validate_chain(chain: AttackChain, rules: dict) -> list[str]

class NeuroSymbolicLoop:
    def __init__(self, provider: ModelProvider)
    def validate_and_fix(self, chain: AttackChain, rules: dict, max_iterations: int = 3) -> AttackChain
```

**逻辑**：
1. **符号验证**：`validate_chain()` 检查每个 step.technique 是否在 `rules["allowed_techniques"]` 中
2. **神经生成**：LLM 根据验证错误重新生成 AttackChain
3. **闭环**：验证 → 生成 → 验证，最多 `max_iterations` 次

**测试**：4 个 — 合法链通过 · 非法技术被标记 · 闭环修复 · 迭代上限

---

### 🔲 未实现
- `context/` — 上下文管理
- `reflection/` — 反思评估

---

## agents/tools/ — 工具层

### ✅ 已实现

#### `llms/base.py` — LLM 抽象基类

| 类 | 字段/方法 |
|----|----------|
| `LLMRequest` | `prompt` · `model_id` · `system_prompt` · `temperature` · `max_tokens` |
| `LLMResponse` | `content` · `model_id` · `usage` · `latency_ms` |
| `ModelProvider` | `complete(request) -> LLMResponse`（Protocol） |

#### `llms/mock_provider.py` — Mock 实现

测试用，按预设 response 返回。

#### `llms/model_router.py` — 多模型路由器

```python
class ModelRouter:
    MODEL_PREFIX_MAP = {"gpt": "openai", "o1": "openai", "o3": "openai",
                        "claude": "anthropic", "local": "local", "qwen": "local",
                        "deepseek": "local", "llama": "local", "mock": "mock"}
```

**路由逻辑**：
1. 按 `request.model_id` 前缀匹配 provider
2. 匹配不到 → 使用 `default_provider`
3. `complete_with_model()` 按 scheduler Model.tier 映射

**测试**：5 个 — mock 返回 · 正确 provider 分发 · fallback 到默认 · 无匹配返回 stub · tier 映射

---

### 🔲 未实现
- `prompts/` — 提示词管理（仅 AGENT.md）
- `runtime/` — Agent 运行时（仅 AGENT.md，B3 待补）

---

## agents/api/ — 公共接口

### 5 个 Protocol 接口

| 接口 | 方法 | 调用方 |
|------|------|--------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` | backend |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` | backend |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` | backend |
| `ExecutionAPI` | `execute(call)` | agents/action |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` | agents/planning |

### 3 个 DI 端口（[`ports.py`](api/ports.py)）

| 端口 | 方法 |
|------|------|
| `PersistencePort` | `save_task(task)` · `load_task(task_id)` |
| `SessionPort` | `get_session(session_id)` · `create_session()` |
| `TaskUpdatePort` | `update_status(task_id, status)` |

---

## 测试总览

| 目录 | 文件数 | 测试数 |
|------|--------|--------|
| `tests/agents/memory/` | 2 | 7 |
| `tests/agents/planning/` | 4 | 10 |
| `tests/agents/tools/` | 1 | 5 |
| `tests/agents/action/` | 11 | 15 |
| `tests/agents/perception/` | 1 | 4 |
| **合计** | **19** | **41** |
