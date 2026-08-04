# Agents 智能体域（域根） — AGENT.md

> 本文件是 `aegisos_agents/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
智能体域：一切与 agent 相关的功能。按认知架构「感知-规划-行动-记忆-工具」五层组织，是系统的智能核心。

## 内部分层（感知-规划-行动-记忆-工具）
| 分类 | 范式 | 说明 |
|------|------|------|
| aegisos_agents/perception/ | 感知 | 上下文管理、推理、反思（接收理解输入、评估结果） |
| aegisos_agents/planning/ | 规划 | 规划角色 Agent、编排 Agent、编排引擎（规划/调度/路由/工作流/事件总线/拓扑） |
| aegisos_agents/action/ | 行动 | 执行角色 Agent（代码/测试/调试/评审/调研/文档）+ 执行能力（沙箱/工具） |
| aegisos_agents/memory/ | 记忆 | 多层长期记忆（12 子模块，含 semantic 知识库） |
| aegisos_agents/tools/ | 工具 | 模型调用、提示词模板、运行时托管 |

## 读取目录（允许读）
- protocol/
- aegisos_agents/planning/engine/
- aegisos_agents/action/execution/
- tooling/configs/
- developer/specs/08_AGENT_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- developer/

## 输出
- aegisos_agents/*/ 角色 Agent
- aegisos_agents/memory/ 记忆（含知识库）
- aegisos_agents/tools/llms/ 模型调用
- aegisos_agents/tools/prompts/ 提示词
- aegisos_agents/tools/runtime/ 运行时
- aegisos_agents/planning/engine/ 编排引擎（规划/调度/路由/工作流/事件总线/拓扑）
- aegisos_agents/action/execution/ 执行能力（执行器/工具）

## 依赖
- aegisos_agents/planning/engine/ 编排调度
- aegisos_agents/action/execution/ 工具执行
- protocol/ 契约

## 接口
register/invoke(agent) -> Result；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/aegisos_agents/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/aegisos_agents/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

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
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 下辖子模块（按感知-规划-行动-记忆-工具分类 + 公共 API）
- **aegisos_agents/api/** 公共接口层：其他模块通过 `from aegisos_agents.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **感知 aegisos_agents/perception/**：`context/`（上下文管理）、`reasoning/`（推理）、`reflection/`（反思评估）
- **规划 aegisos_agents/planning/**：`planner/`（规划角色 Agent）、`orchestrator/`（编排角色 Agent）、`engine/`（编排引擎：planner/scheduler/router/workflow/eventbus/topology）
- **行动 aegisos_agents/action/**：`coder/`、`executor/`（执行角色）、`tester/`、`debugger/`、`critic/`、`reviewer/`、`researcher/`、`docwriter/`（角色 Agent）+ `execution/`（executor 沙箱 + tools 工具）
- **记忆 aegisos_agents/memory/**：12 子模块（working/episodic/semantic/vector/archive/compression/retrieval/reflection/checkpoint/cache/snapshot/sync）
- **工具 aegisos_agents/tools/**：`llms/`（模型调用）、`prompts/`（提示词，含 roles/）、`runtime/`（运行时托管）

---

## 📋 模块实现详解

> 原 `aegisos_agents/MODULE.md` 内容，已合并至此。

### 五层架构总览

```
aegisos_agents/
├── perception/   感知 — context · reasoning · reflection
├── planning/      规划 — engine/(topology · router · scheduler) · planner · orchestrator
├── action/        行动 — 11 个红蓝紫攻防 Agent + execution
├── memory/        记忆 — compression · recall + 10 子模块
├── tools/         工具 — llms(多模型) · prompts · runtime
└── api/           公共接口 — 5 个 Protocol + 3 个 DI 端口
```

### aegisos_agents/planning/ — 规划引擎

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

##### `engine/eventbus/impl.py` — 事件总线（P1 完成）

```python
class EventBus:
    def subscribe(topic: EventType, handler) -> Callable[[], None]
    def publish(event: Event) -> None
    def history(topic=None, task_id=None) -> list[Event]
    def dead_letters() -> list[tuple[Event, str]]
```

**逻辑**：基于 `EventType` 8 topic 的发布/订阅。FIFO 顺序保证；handler 异常隔离（捕获后入死信队列，不中断后续 handler）；历史记录 deque（上限 1000，供 `observability/inspect/replay/` 消费）；`subscribe` 返回取消订阅闭包。

**测试**：8 个 — 订阅接收 · 多订阅顺序 · 主题过滤 · 取消订阅 · 异常隔离死信 · 历史过滤 · 历史截断 · clear 重置

---

##### `engine/workflow/engine.py` — DAG 工作流引擎（P1 完成）

```python
class WorkflowEngine:
    def run(nodes: dict[str, WorkflowNode], context=None, task_id="") -> WorkflowResult
```

**逻辑**：Kahn 拓扑排序（分层 + 循环检测抛 ValueError）→ 同层 `ThreadPoolExecutor` 并行执行 → 条件分支（`condition` 谓词 False → Skipped）→ 失败传播（Failed 下游 Skipped）→ 可选注入 `EventBus` 发布 `AgentStart`/`AgentFinish` 事件。`WorkflowNode.executor(upstream: dict) -> Any` 接收上游产出字典。

**测试**：8 个 — 线性链顺序 · 并行扇出汇聚 · 条件跳过 · 失败传播 · 循环检测 · context 合并 · 事件发布 · 失败事件

---

##### `planner/planner.py` — 任务规划器（P1 完成）

```python
class Planner:
    def plan(goal: str, scenario: str | None = None) -> Plan
```

**逻辑**：4 场景模板纯算法分解（不调 LLM）：`cyber_red`（recon→vuln→exploit→lateral 链）、`cyber_blue`（detector→triage→hunt→ir 链）、`cyber_purple`（critic+reviewer 并行）、`generic`（analyze→execute→verify）。输出 `protocol.Plan`（dag + tasks），dag key 为 node_id（=agent_id），与 `WorkflowNode.dependencies` 对齐。

**测试**：7 个 — 红队链 · 蓝队链 · 紫队并行 · 默认 generic · 未知场景报错 · task_id 唯一 · 场景列表

---

##### `orchestrator/orchestrator.py` — 通用编排器（P1 完成）

```python
class Orchestrator:
    def execute(goal: str, runtime: RuntimeAPI, scenario=None, context=None) -> WorkflowResult
    def execute_plan(plan: Plan, runtime: RuntimeAPI, context=None) -> WorkflowResult
```

**逻辑**：整合 Planner + WorkflowEngine + EventBus。`execute` 一站式（goal→Plan→WorkflowNode→执行）；`execute_plan` 执行已构造 Plan；内部将 `Plan.dag` 转 `WorkflowNode`，executor 调用 `runtime.run(node_id, task)`，上游产出注入 `task.plan["upstream"]`。

**测试**：6 个 — 红队链执行 · 紫队并行 · 事件发布 · 上游传递 · 失败传播 · plan 不一致报错

---

##### `orchestrator/runtime.py` — CyberRuntime 真实运行时（P1 完成）

```python
class CyberRuntime:  # 实现 RuntimeAPI
    def run(agent_id: str, task: Task) -> dict
```

**逻辑**：委托 `CyberOrchestrator` 红蓝紫三条链，替代 `MockRuntime` 85 行 dispatch map。`run("red_chain", task)` → `run_red_chain()`；`run("blue_chain", task)` → `run_blue_chain()`；`run("purple_review", task)` → `run_purple_review()`。protocol dataclass → dict 序列化。`MockRuntime` 保留作兼容层。

**测试**：7 个 — 红蓝紫链 · submit/stop/heartbeat · 未知 agent_id 兜底

---

#### 🔲 未实现（仅 AGENT.md）

> P1 编排器 5 子任务已全部完成（EventBus / Workflow / Planner / Orchestrator / CyberRuntime）。
> 以下为 engine 子模块内的占位（系统级 planner，区别于 planning/planner/ 角色级）。

| 目录 | 计划功能 |
|------|---------|
| `engine/planner/` | 系统级规划器（engine 内部，区别于 `planning/planner/` 角色级） |
| `engine/eventbus/handlers/` | 事件总线内置 handler（当前由各模块自行注册） |
| `engine/eventbus/topics/` | 主题管理（当前由 EventType 枚举覆盖） |
| `engine/workflow/dags/` | 预置 DAG 模板库（当前由 Planner 模板覆盖） |
| `engine/workflow/nodes/` | 预置节点类型库（当前由 WorkflowNode 覆盖） |

> **影响**：编排器已就绪，11 个 Agent 可通过 `Orchestrator.execute(goal, CyberRuntime())` 自动协同。

---

### aegisos_agents/memory/ — 记忆子系统

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
class MemoryStore:  # 实现 aegisos_agents.api.MemoryAPI
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

> **✅ P2 全部完成（2026-08-01）**：archive/cache/checkpoint/reflection/retrieval/snapshot/sync 7 子模块全部实现。详见 `developer/CHANGELOG.md` [P2] 2026-08-01。

---

### aegisos_agents/action/ — 攻防 Agent（11 个全部完成）

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

**实现模式**：每个 Agent 继承 `StructuredAgent[T]`（`action/structured_agent.py`），通过 openai-agents SDK `Agent` + `Runner.run_sync` + `output_type`（Pydantic BaseModel）实现结构化输出，无需手写 `json.loads`。Mock 测试使用 `MockSDKModel`（适配 SDK `Model` 接口）。详见 `action/AGENT.md`。

**测试**：19 个（每个 Agent 1-2 个测试），全部通过。

**SDK 集成状态**：✅ 11 个攻防 Agent 已全部迁移到 openai-agents SDK（S1-S4 完成）。

---

### aegisos_agents/perception/ — 感知层

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

**✅ SDK 重构完成（R4.1）**：已迁移到 `NeuroSymbolicAgent(StructuredAgent[ExploitPlannerResult])`，SDK `output_type` 替代旧 `ModelProvider.complete()` + `json.loads`。`validate_chain` 符号侧保留。

---

> **✅ P2 完成（2026-08-01）**：context/（TokenBudget + ContextManager）+ reflection/（ExecutionCritic + OutputScorer + FeedbackLoop）。

---

### aegisos_agents/tools/ — 工具层

#### ✅ 已实现

##### `llms/sdk_provider.py` — openai-agents SDK 适配器（✅ S2 完成）

`SDKProvider` 桥接项目 `ModelProvider` Protocol 到 SDK `OpenAIChatCompletionsModel`，支持双模式：
- **Mock 模式**（`AEGIS_USE_MOCK=1`）：走 `MockSDKModel`，测试无需真实 API
- **真实 API 模式**（`OPENAI_API_KEY` / `OPENAI_BASE_URL`）：走火山引擎 ARK 等

##### `llms/mock_sdk_model.py` — SDK Mock 适配器（✅ S2 完成）

`MockSDKModel(Model)` 实现 SDK `Model` 接口，将 `MockProvider` 包装为 SDK `ModelResponse`。

##### `llms/base.py` — LLM 请求/响应数据结构（✅ R5.1 清理后）

R5.1 清理后仅保留 `LLMRequest` / `LLMResponse`（MockProvider 与 MockSDKModel 内部数据契约）。`ModelProvider` Protocol 已删除（SDK 有自己的 `ModelProvider`）。

| 类 | 字段/方法 |
|----|----------|
| `LLMRequest` | `prompt` · `model_id` · `system_prompt` · `temperature` · `max_tokens` |
| `LLMResponse` | `text` · `ok` · `error` · `usage` · `model_id` |

##### `llms/mock_provider.py` — Mock 实现

测试用，按预设 response 返回。

##### ~~`llms/model_router.py`~~ — R5.2 已删除

R5.2 删除（无业务代码引用）。模型选择由 `Agent(model=...)` 或 `RunConfig(model=...)` 指定。

---

> **✅ P2 完成（2026-08-03）**：prompts/（PromptRegistry + PromptRenderer）+ runtime/（AgentLifecycle + RuntimeSupervisor）。

---

### aegisos_agents/api/ — 公共接口

#### 5 个 Protocol 接口

| 接口 | 方法 | 调用方 |
|------|------|--------|
| `AgentRegistryAPI` | `register(agent)` · `get(agent_id)` · `list_agents()` | backend |
| `RuntimeAPI` | `submit(task)` · `run(agent_id, task)` · `stop(agent_id)` · `heartbeat(agent_id)` | backend |
| `MemoryAPI` | `read(query)` · `write(packet)` · `retrieve(query)` | backend |
| `ExecutionAPI` | `execute(call)` | aegisos_agents/action |
| `EventBusAPI` | `publish(event)` · `subscribe(topic, handler)` | aegisos_agents/planning |

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
| `tests/aegisos_agents/memory/` | 7 | 33 |
| `tests/aegisos_agents/planning/` | 4 | 18 |
| `tests/aegisos_agents/tools/` | 1 | 5 |
| `tests/aegisos_agents/action/` | 11 | 19 |
| `tests/aegisos_agents/perception/` | 1 | 4 |
| `tests/e2e/` | 1 | 5 |
| **合计** | **25** | **84** |

---

### 🔧 openai-agents SDK 集成状态

> 2026-07-06 全量排查。详见 `developer/plan.md`「openai-agents SDK 重构排查」段。

#### ✅ 已完成（S1-S4 + R4 + R5）

| 文件 | SDK 能力 | 状态 |
|------|---------|------|
| `action/structured_agent.py` | `Agent` + `Runner.run_sync` + `output_type` + `_run_streamed`（R5.3） | ✅ |
| `action/output_types.py` | 11 个 Pydantic BaseModel 作为 `output_type` | ✅ |
| `action/{11个攻防Agent}/agent.py` | 全部继承 `StructuredAgent[T]`，支持 `model=` 真实 API 注入 | ✅ |
| `tools/llms/sdk_provider.py` | `OpenAIChatCompletionsModel` + `set_default_openai_api("chat_completions")` | ✅ |
| `tools/llms/mock_sdk_model.py` | SDK `Model` 接口实现（Mock 适配） | ✅ |
| `planning/orchestrator/cyber_orchestrator.py` | 9 SDK Agent + handoffs + guardrails + tracing + FunctionTool | ✅ R4 |
| `perception/reasoning/neuro_symbolic.py` | `NeuroSymbolicAgent`（SDK 结构化输出） | ✅ R4.1 |
| `observability/inspect/monitor/tracing/hooks.py` | `CyberAgentHooks` + eventbus 发布（R5.4） | ✅ R5.4 |
| `backend/routers/stream.py` | SDK `Runner.run_streamed()` → SSE 流式（R5.3） | ✅ R5.3 |

#### ✅ R5 清理已完成

| # | 任务 | 状态 |
|---|------|------|
| R5.1 | `base.py` 删除 `ModelProvider` Protocol，保留 `LLMRequest`/`LLMResponse` | ✅ |
| R5.2 | 删除 `model_router.py`（无业务引用） | ✅ |
| R5.3 | SDK `Runner.run_streamed()` → SSE → 前端实时展示 | ✅ |
| R5.4 | `AgentHooks` 发布事件到 `EventBus`（AgentStart/AgentFinish/ToolCall/ToolFinish） | ✅ |
| R5.5 | 179 测试全通过 | ✅ |
