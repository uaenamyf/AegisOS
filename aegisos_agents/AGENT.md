# Agents 智能体域（域根） — AGENT.md

> 本文件是 `agents/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
智能体域：一切与 agent 相关的功能。按认知架构「感知-规划-行动-记忆-工具」五层组织，是系统的智能核心。

## 内部分层（感知-规划-行动-记忆-工具）
| 分类 | 范式 | 说明 |
|------|------|------|
| agents/perception/ | 感知 | 上下文管理、推理、反思（接收理解输入、评估结果） |
| agents/planning/ | 规划 | 规划角色 Agent、编排 Agent、编排引擎（规划/调度/路由/工作流/事件总线/拓扑） |
| agents/action/ | 行动 | 执行角色 Agent（代码/测试/调试/评审/调研/文档）+ 执行能力（沙箱/工具） |
| agents/memory/ | 记忆 | 多层长期记忆（12 子模块，含 semantic 知识库） |
| agents/tools/ | 工具 | 模型调用、提示词模板、运行时托管 |

## 读取目录（允许读）
- protocol/
- agents/planning/engine/
- agents/action/execution/
- tooling/configs/
- developer/specs/08_AGENT_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- developer/

## 输出
- agents/*/ 角色 Agent
- agents/memory/ 记忆（含知识库）
- agents/tools/llms/ 模型调用
- agents/tools/prompts/ 提示词
- agents/tools/runtime/ 运行时
- agents/planning/engine/ 编排引擎（规划/调度/路由/工作流/事件总线/拓扑）
- agents/action/execution/ 执行能力（执行器/工具）

## 依赖
- agents/planning/engine/ 编排调度
- agents/action/execution/ 工具执行
- protocol/ 契约

## 接口
register/invoke(agent) -> Result；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/agents/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/agents/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/agents.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **API 边界**：agents/api/ — from agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块（按感知-规划-行动-记忆-工具分类 + 公共 API）
- **agents/api/** 公共接口层：其他模块通过 `from agents.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **感知 agents/perception/**：`context/`（上下文管理）、`reasoning/`（推理）、`reflection/`（反思评估）
- **规划 agents/planning/**：`planner/`（规划角色 Agent）、`orchestrator/`（编排角色 Agent）、`engine/`（编排引擎：planner/scheduler/router/workflow/eventbus/topology）
- **行动 agents/action/**：`coder/`、`executor/`（执行角色）、`tester/`、`debugger/`、`critic/`、`reviewer/`、`researcher/`、`docwriter/`（角色 Agent）+ `execution/`（executor 沙箱 + tools 工具）
- **记忆 agents/memory/**：12 子模块（working/episodic/semantic/vector/archive/compression/retrieval/reflection/checkpoint/cache/snapshot/sync）
- **工具 agents/tools/**：`llms/`（模型调用）、`prompts/`（提示词，含 roles/）、`runtime/`（运行时托管）

---

## 📋 模块实现详解

> 原 `agents/MODULE.md` 内容，已合并至此。

### 五层架构总览

```
agents/
├── perception/   感知 — context · reasoning · reflection
├── planning/      规划 — engine/(topology · router · scheduler) · planner · orchestrator
├── action/        行动 — 11 个红蓝紫攻防 Agent + execution
├── memory/        记忆 — compression · recall + 10 子模块
├── tools/         工具 — llms(多模型) · prompts · runtime
└── api/           公共接口 — 5 个 Protocol + 3 个 DI 端口
```

### agents/planning/ — 规划引擎

#### ✅ 已实现

##### `engine/topology/topology.py` — 活跃子图

```python
def active_subgraph(graph: Graph, required_capability: str) -> Graph
```

**逻辑**：过滤 `status in {active, degraded}` 且 `required_capability in node.capabilities` 的节点，返回子图。

**测试**：3 个 — capability+status 过滤 · degraded 显式包含 · 无匹配返回空图

---

##### `engine/router/router.py` — 低熵稀疏路由 Top-K

```python
def route(message: Message, topology: Graph, required_capability: str) -> list[NodeRef]
```

**逻辑**：
1. 调用 `active_subgraph()` 获取候选
2. 按 `_affinity(message, node) - _load_penalty(node)` 排序
   - affinity = `success_rate`（默认 1.0）
   - load_penalty = `latency`（默认 0.0）
3. 返回 Top-3（`TOP_K = 3`），**非全广播**

**测试**：4 个 — 稀疏性 · 跳过 idle · 偏好高成功率 · 空候选返回空

---

##### `engine/router/election.py` — 异构选举

```python
def elect(task_features: list[float], instances: list[GraphNode],
          capability_vectors: dict[str, list[float]]) -> NodeRef
```

**逻辑**：计算 `task_features` 与每个实例 `capability_vector` 的点积，选最高分。

**测试**：3 个 — 最优匹配 · 翻转特征后选另一个 · 单实例返回自身

---

##### `engine/scheduler/scheduler.py` — 端边云三层卸载调度

```python
@dataclass
class Model:
    model_id: str
    tier: str       # device | edge | cloud
    size: str       # small | medium | large
    capabilities: list

def schedule(task: Task, models: list[Model], required_capability: str | None = None) -> Model
```

**三层分级**：device（端侧 PC/手机/IoT）→ edge（边侧网关/机架服务器）→ cloud（云侧 GPU 集群/模型 API）

**调度规则（四规则 + 降级）**：
1. `task.privacy == "local"` → 必须 device；无 device 降级取层级最低候选
2. `latency_budget < 1.0`（DEVICE_THRESHOLD）→ 优先 device；无 device 降级到 edge，再缺失取首个
3. `latency_budget < 5.0`（EDGE_THRESHOLD）→ 优先 edge；无 edge 取首个
4. 其余 → cloud；无 cloud 取首个
5. 按 `required_capability` 过滤

**测试**：8 个 — privacy=local 选 device · 超低延迟选 device · 超低延迟无 device 降级 edge · 低延迟选 edge · privacy=local 无 device 降级 edge · 高延迟选 cloud · 能力过滤 · 三层共存选 edge

---

#### 🔲 未实现（仅 AGENT.md）

| 目录 | 计划功能 |
|------|---------|
| `planner/` | 规划器：将 goal 分解为 Plan(DAG) |
| `orchestrator/` | 编排器：协调多 Agent 执行 |
| `engine/workflow/` | 工作流引擎：DAG 执行 |
| `engine/eventbus/` | 事件总线实现（publish/subscribe） |

> **影响**：11 个 Agent 目前只能被 API 逐个手动调用，无法自动协同。

---

### agents/memory/ — 记忆子系统

#### ✅ 已实现

##### `compression/compactor.py` — 上下文压缩

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

##### `recall/recaller.py` — 记忆唤醒

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

##### `working/store.py` — 工作记忆（B3.1）

```python
class WorkingMemory:
    def add(self, packet: MemoryPacket) -> None
    def get(self, session_id: str) -> list[MemoryPacket]
    def clear(self, session_id: str) -> None
    def sessions(self) -> list[str]
```

**逻辑**：按 `session_id` 隔离的内存上下文栈，写入追加栈尾，读取按写入时序返回，会话结束 `clear` 回收。

**测试**：4 个 — 时序保持 · 会话隔离 · clear 回收 · 缺失会话返回空

---

##### `episodic/store.py` — 情景记忆（B3.2）

```python
class EpisodicMemory:
    def add(self, packet: MemoryPacket) -> None
    def all(self) -> list[MemoryPacket]
    def by_task(self, task_id: str) -> MemoryPacket | None
```

**逻辑**：跨会话的历史任务经验累积（内存 list），支持按 task_id 精确回查；recaller 唤醒时扫描本存储。

**测试**：3 个 — 追加与枚举 · 按 task_id 查找 · 缺失返回 None

---

##### `semantic/store.py` — 语义记忆 / 知识库（B3.3）

```python
class SemanticMemory:
    def add(self, concept_id: str, packet: MemoryPacket) -> None
    def get(self, concept_id: str) -> MemoryPacket | None
    def search(self, keyword: str) -> list[MemoryPacket]
    def seed_attack_knowledge(self) -> None
```

**逻辑**：`concept_id -> MemoryPacket` 知识库，构造时预置 8 个 ATT&CK 种子技战术（T1595/T1592/T1210/T1059/T1078/T1046/T1021/T1053）；关键词在 semantic 字段值与 summary 中子串匹配。未来可对接 Neo4j ATT&CK 图（H2）。

**测试**：4 个 — 种子预置 · 缺失返回 None · 关键词命中 · 无命中返回空

---

##### `vector/store.py` — 向量记忆（B3.4）

```python
class VectorMemory:
    def add(self, packet: MemoryPacket) -> None
    def search(self, query: list[float], top_k: int = 5) -> list[MemoryPacket]
```

**逻辑**：余弦相似度（`dot/(|a|*|b|)`）Top-K 检索，仅索引 embedding 非空的记忆；零向量相似度定义为 0。Qdrant 接入预留位，接口稳定可无缝替换。

**测试**：5 个 — 最相似排首 · top_k 截断 · 空 embedding 跳过 · 空查询返回空 · 零向量不抛异常

---

##### `memory_store.py` — 记忆集成存储 / 认知循环中枢（B3.5）

```python
class MemoryStore:  # 实现 agents.api.MemoryAPI
    def read(self, query: dict) -> MemoryPacket
    def write(self, packet: MemoryPacket) -> bool
    def retrieve(self, query: dict) -> list
    def recall(self, trigger: str) -> list[MemoryPacket]
    def search_knowledge(self, keyword: str) -> list[MemoryPacket]
    def compress(self, session_id: str, budget: int) -> list[MemoryPacket]
    def end_session(self, session_id: str) -> None
```

**逻辑**：聚合 working/episodic/semantic/vector 四层 + compactor + recaller。`write` 按内容自动路由（decision/episodic→情景，embedding→向量，semantic+concept_id→知识库，始终入工作记忆）；`retrieve` 合并 recaller 唤醒与语义知识检索。形成认知闭环：推理前 recall + search_knowledge → 推理后 write → 上下文超长 compress → 压缩后情景/向量记忆仍可唤醒。

**测试**：10 个 — 路由决策/向量/语义 · read 聚合 · recall 唤醒 · compress 产生 digest · retrieve 合并去重 · end_session 回收工作记忆保留情景 · 端到端认知循环闭环

---

#### 🔲 未实现（6 个子模块，仅 AGENT.md）

| 子模块 | 计划功能 |
|--------|---------|
| `archive/` | 归档（长期存储） |
| `cache/` | 缓存 |
| `checkpoint/` | 检查点 |
| `reflection/` | 反思记忆 |
| `retrieval/` | 检索引擎 |
| `snapshot/` | 快照 |
| `sync/` | 同步 |

> **B3 已完成**：working/episodic/semantic/vector 四层 + MemoryStore 集成层接入 runtime 认知循环。

---

### agents/action/ — 攻防 Agent（11 个全部完成）

#### 🔴 红队（4 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `recon` | [`recon/agent.py`](action/recon/agent.py) | `scan(target_range: str)` | 目标范围 → `list[Asset]` |
| `vuln_correlator` | [`vuln_correlator/agent.py`](action/vuln_correlator/agent.py) | `correlate(assets, cve_db)` | 资产+CVE → `list[VulnFinding]` |
| `exploit_planner` | [`exploit_planner/agent.py`](action/exploit_planner/agent.py) | `plan(findings)` | 漏洞 → `AttackChain` |
| `lateral_move` | [`lateral_move/agent.py`](action/lateral_move/agent.py) | `plan_moves(chain)` | 攻击链 → 横向移动步骤 |

**流程**：recon → vuln_correlator → exploit_planner → lateral_move

#### 🔵 蓝队（5 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `detector` | [`detector/agent.py`](action/detector/agent.py) | `detect(events)` | 事件流 → `list[Alert]` |
| `triage` | [`triage/agent.py`](action/triage/agent.py) | `triage(alerts)` | 告警 → 按严重度排序 |
| `threat_hunt` | [`threat_hunt/agent.py`](action/threat_hunt/agent.py) | `hunt(alerts)` | 告警 → ATT&CK 假设 |
| `ir_planner` | [`ir_planner/agent.py`](action/ir_planner/agent.py) | `plan_response(hypotheses)` | 假设 → `ResponsePlan`(含 rollback) |
| `forensics` | [`forensics/agent.py`](action/forensics/agent.py) | `investigate(alert)` | 告警 → 取证报告 |

**流程**：detector → triage → threat_hunt → ir_planner → forensics

#### 🟣 紫队（2 个）

| Agent | 文件 | 方法 | 输入 → 输出 |
|-------|------|------|-----------|
| `critic` | [`critic/agent.py`](action/critic/agent.py) | `critique(chain_or_plan)` | 红蓝产出 → 对抗性反驳 |
| `reviewer` | [`reviewer/agent.py`](action/reviewer/agent.py) | `review(inputs)` | 全部产出 → 一致性审查 |

**实现模式**：每个 Agent 接收 `ModelProvider`，通过 LLM ��成结构化 JSON → 解析为 protocol 类型。Mock 测试使用 `MockProvider`。

**测试**：19 个（每个 Agent 1-2 个测试），全部通过。

---

### agents/perception/ — 感知层

#### ✅ 已实现

##### `reasoning/neuro_symbolic.py` — 神经符号闭环

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

#### 🔲 未实现
- `context/` — 上下文管理
- `reflection/` — 反思评估

---

### agents/tools/ — 工具层

#### ✅ 已实现

##### `llms/base.py` — LLM 抽象基类

| 类 | 字段/方法 |
|----|----------|
| `LLMRequest` | `prompt` · `model_id` · `system_prompt` · `temperature` · `max_tokens` |
| `LLMResponse` | `content` · `model_id` · `usage` · `latency_ms` |
| `ModelProvider` | `complete(request) -> LLMResponse`（Protocol） |

##### `llms/mock_provider.py` — Mock 实现

测试用，按预设 response 返回。

##### `llms/model_router.py` — 多模型路由器

```python
class ModelRouter:
    MODEL_PREFIX_MAP = {"gpt": "openai", "o1": "openai", "o3": "openai",
                        "claude": "anthropic", "local": "local", "qwen": "local",
                        "deepseek": "local", "llama": "local", "mock": "mock"}
    TIER_PROVIDER_MAP = {"device": "local", "edge": "local", "cloud": "cloud"}
```

**路由逻辑**：
1. 按 `request.model_id` 前缀匹配 provider
2. 匹配不到 → 使用 `default_provider`
3. `complete_with_model()` 按 scheduler Model.tier（device/edge/cloud）映射到 provider

**测试**：5 个 — mock 返回 · 正确 provider 分发 · fallback 到默认 · 无匹配返回 stub · tier 映射

---

#### 🔲 未实现
- `prompts/` — 提示词管理（仅 AGENT.md）
- `runtime/` — Agent 运行时（仅 AGENT.md，B3 待补）

---

### agents/api/ — 公共接口

#### 5 个 Protocol 接口

| 接口 | 方法 | 调用方 |
|------|------|--------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` | backend |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` | backend |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` | backend |
| `ExecutionAPI` | `execute(call)` | agents/action |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` | agents/planning |

#### 3 个 DI 端口（[`ports.py`](api/ports.py)）

| 端口 | 方法 |
|------|------|
| `PersistencePort` | `save_task(task)` · `load_task(task_id)` |
| `SessionPort` | `get_session(session_id)` · `create_session()` |
| `TaskUpdatePort` | `update_status(task_id, status)` |

---

### 测试总览

| 目录 | 文件数 | 测试数 |
|------|--------|--------|
| `tests/agents/memory/` | 7 | 33 |
| `tests/agents/planning/` | 4 | 18 |
| `tests/agents/tools/` | 1 | 5 |
| `tests/agents/action/` | 11 | 19 |
| `tests/agents/perception/` | 1 | 4 |
| `tests/e2e/` | 1 | 5 |
| **合计** | **25** | **84** |
