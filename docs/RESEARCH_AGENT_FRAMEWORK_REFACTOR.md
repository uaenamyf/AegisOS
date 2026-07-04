# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 新建 Agent 框架替换/规范化方案——逐模块分析可替换性 + 分层架构 + 迁移路线

# Agent 框架规范化与替换方案

> 本文档基于对 `agents/`、`protocol/`、`backend/`、`agents/tools/llms/`、`agents/planning/engine/`、`agents/memory/` 的完整代码审查。
>
> **核心问题**：项目有一套功能正确但"手写"的 Agent 框架，存在大量可以用标准库/成熟框架替换的重复逻辑。

---

## 1. 现状诊断：7 类"重复造轮子"

### 1.1 LLM 调用层（4 个 Provider 全是手写 HTTP）

**现状**：`agents/tools/llms/` 下 4 个 Provider 各自手写 httpx 请求：

| 文件 | 重复逻辑 | 可替换为 |
|------|---------|---------|
| `openai_provider.py` | 手写 httpx POST + auth header + payload 构造 + JSON parse | `litellm.completion()` 一行 |
| `anthropic_provider.py` | 手写 httpx POST + anthropic-version header + content block 解析 | `litellm.completion()` 一行 |
| `local_provider.py` | 手写 httpx POST（OpenAI 兼容格式） | `litellm.completion()` 一行 |
| `mock_provider.py` | 前缀匹配 + 预置 JSON | `litellm` mock adapter 或 `unittest.mock` |

**代码量**：4 文件 × ~55 行 = ~220 行，可压缩到 1 文件 ~30 行。

**根因**：每个 Provider 重复实现了：认证、请求构造、超时、错误处理、响应解析。这正是 `litellm` 要解决的问题。

### 1.2 结构化输出（11 个 Agent 全是 `json.loads` + try/except）

**现状**：每个攻防 Agent 的模式完全相同：

```python
resp = self._provider.complete(LLMRequest(...))
if not resp.ok:
    return [] / {} / FallbackObject()
try:
    data = json.loads(resp.text)
    return [SomeDataclass(**a) for a in data.get("key", [])]
except (json.JSONDecodeError, KeyError):
    return [] / {} / FallbackObject()
```

| Agent 文件 | JSON 解析逻辑 | 错误兜底 |
|-----------|-------------|---------|
| `recon/agent.py` | `json.loads` → `[Asset(**a)]` | `return []` |
| `detector/agent.py` | `json.loads` → `[Alert(**a)]` | `return []` |
| `vuln_correlator/agent.py` | `json.loads` → `[VulnFinding(**f)]` | `return []` |
| `exploit_planner/agent.py` | `json.loads` → `AttackChain(**data)` | `return AttackChain(chain_id="", status="failed")` |
| `lateral_move/agent.py` | `json.loads` → `[AttackStep(**s)]` | `return []` |
| `triage/agent.py` | `json.loads` → `[Alert]` | `return alerts` (原始) |
| `threat_hunt/agent.py` | `json.loads` → `list[dict]` | `return []` |
| `ir_planner/agent.py` | `json.loads` → `ResponsePlan(**data)` | `return ResponsePlan(plan_id="")` |
| `forensics/agent.py` | `json.loads` → `dict` | `return {"report_id": "", ...}` |
| `critic/agent.py` | `json.loads` → `dict` | `return {"valid": False, ...}` |
| `reviewer/agent.py` | `json.loads` → `dict` | `return {"consistent": False, ...}` |

**代码量**：11 文件 × ~50 行 = ~550 行，其中 ~60% 是重复的 JSON parse + error fallback。

**可替换为**：`instructor` 库 + Pydantic，或 `langchain` `StructuredOutputParser`。

### 1.3 Agent 类结构（11 个几乎一模一样）

**现状**：每个 Agent 类的结构完全相同：

```python
class XxxAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def do_something(self, input_data) -> SomeOutputType:
        resp = self._provider.complete(LLMRequest(
            prompt=f"... {json.dumps(input)}",
            model_id="xxx",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.x,
        ))
        # json parse + fallback
```

唯一差异：system_prompt 文本、temperature、输入→输出映射。

**可替换为**：一个泛型基类 + 声明式配置（见下文 §3）。

### 1.4 运行时调度（MockRuntime 手写 dispatch map）

**现状**：`backend/src/composition.py` 中 `MockRuntime` 有一个 ~120 行的手写 `_cyber_dispatch_map()`，每个 handler 手动做类型转换 + 调用 + `asdict`。

**可替换为**：LangGraph `StateGraph` + 自动状态传递，或注册表模式。

### 1.5 记忆系统（只有骨架无持久化）

**现状**：`agents/memory/` 12 个子模块只有 `compression/` 和 `recall/` 有实现（各 ~30 行），其余为空目录。

**可替换为**：`langgraph.checkpoint`（状态持久化）+ `langchain.memory`（对话记忆）+ Qdrant 向量（已有规划）。

### 1.6 Protocol 类型（dataclass 而非 Pydantic）

**现状**：`protocol/*.py` 全是 `@dataclass`，手动写 `to_dict()` / `from_dict()`。

**可替换为**：Pydantic BaseModel（`06_SCHEMA_SPEC §12` 已列迁移待办）。

### 1.7 事件总线（只有接口无实现）

**现状**：`agents/api/__init__.py` 定义了 `EventBusAPI` Protocol（publish/subscribe），但无任何实现。

**可替换为**：`blinker`（轻量）或 `fastapi.Event` + SSE stream，或 LangGraph callback。

---

## 2. 推荐方案：三层替换架构

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: 工作流编排 (LangGraph)                               │
│  替换: MockRuntime dispatch map + 缺失的 orchestrator         │
│  能力: 有环图 / checkpoint / 条件路由 / 流式 / Agent 间通信    │
├──────────────────────────────────────────────────────────────┤
│  Layer 2: LLM 调用 + 结构化输出 (litellm + instructor/pydantic)│
│  替换: 4 个手写 Provider + 11 处 json.loads/try-except          │
│  能力: 100+ 模型统一接口 / 自动重试 / 结构化输出 / 工具调用    │
├──────────────────────────────────────────────────────────────┤
│  Layer 1: 数据契约 (Pydantic)                                 │
│  替换: protocol/ 下所有 @dataclass                            │
│  能力: 序列化/反序列化/验证/JSON Schema 自动生成                │
├──────────────────────────────────────────────────────────────┤
│  保留不变 (自定义核心算法)                                     │
│  protocol/cyber.py (攻防类型) / engine/router (Top-K)         │
│  engine/election (点积选举) / engine/scheduler (端边云)        │
│  engine/topology (活跃子图) / memory/compression / recall     │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 逐层替换细节

### Layer 1: Protocol → Pydantic

**替换范围**：`protocol/*.py`（9 文件）

**变更模式**（以 `cyber.py` 为例）：

```python
# ---------- 现在 ----------
from dataclasses import dataclass, field

@dataclass
class Asset:
    asset_id: str
    host: str = ""
    services: list = field(default_factory=list)
    # ...
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Asset:
        # 手动写

# ---------- 替换后 ----------
from pydantic import BaseModel, Field

class Asset(BaseModel):
    asset_id: str
    host: str = ""
    services: list = Field(default_factory=list)
    # ... 自动获得 model_dump() / model_validate()
```

**收益**：
- 删除所有手写 `to_dict()` / `from_dict()` 方法
- 自动获得 JSON Schema（可用于 API 文档生成）
- 自动验证（非法类型直接报错）
- `06_SCHEMA_SPEC §12` 迁移待办完成

**风险**：低。dataclass → BaseModel 行为基本兼容，唯一注意点是 `asdict()` → `model_dump()`。

### Layer 2: LLM Provider → litellm + instructor

**替换范围**：`agents/tools/llms/`（8 文件 → 3 文件）

#### 2a. 统一 LLM 调用：litellm

```python
# ---------- 现在：4 个 Provider 各 55 行 ----------
# openai_provider.py / anthropic_provider.py / local_provider.py / mock_provider.py

# ---------- 替换后：1 个文件 ----------
# agents/tools/llms/provider.py (~30 行)
import litellm

class UnifiedProvider:
    """所有模型统一调用入口，litellm 处理路由 + 认证 + 重试。"""

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            resp = litellm.completion(
                model=request.model_id,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop or None,
            )
            return LLMResponse(
                text=resp.choices[0].message.content,
                ok=True,
                model_id=request.model_id,
                usage=resp.usage.model_dump() if resp.usage else {},
            )
        except Exception as e:
            return LLMResponse(ok=False, error=str(e), model_id=request.model_id)
```

litellm 自动处理：
- OpenAI (gpt-*) / Anthropic (claude-*) / Local (ollama/vllm) / Azure / Cohere / 100+ providers
- API key 从环境变量自动读取
- 超时/重试可配置
- 嵌套调用降级（fallback models）

#### 2b. 结构化输出：instructor

```python
# ---------- 现在：11 个 Agent 各写 json.loads + try/except ----------
class ReconAgent:
    def scan(self, target_range: str) -> list[Asset]:
        resp = self._provider.complete(LLMRequest(...))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [Asset(**a) for a in data.get("assets", [])]
        except (json.JSONDecodeError, KeyError):
            return []

# ---------- 替换后 ----------
import instructor
from pydantic import BaseModel

class ReconResult(BaseModel):
    assets: list[Asset]

class ReconAgent:
    def __init__(self, provider: UnifiedProvider):
        self._client = instructor.from_litellm(provider.complete)

    def scan(self, target_range: str) -> list[Asset]:
        result = self._client(
            response_model=ReconResult,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Scan target range: {target_range}"},
            ],
        )
        return result.assets
```

instructor 自动处理：
- Prompt 中注入 JSON Schema 指令
- 自动 `json.loads` + Pydantic 验证
- 失败时自动重试（可配置重试次数）
- 嵌套模型自动展开

**收益**：
- 11 个 Agent 的 `json.loads` + `try/except` 全部删除
- 每个 Agent 从 ~50 行降到 ~20 行
- 结构化输出有类型保证，消除运行时 parse 错误

#### 2c. ModelRouter 保留但简化

`ModelRouter` 的前缀路由逻辑和 `scheduler` 的 tier 路由逻辑保留——这是项目特有的「端边云调度」需求，litellm 不提供。但实现可以简化为：

```python
class ModelRouter:
    """项目特有的端边云模型路由器，复用 litellm 调用。"""

    TIER_MODEL_MAP = {
        "edge": "ollama/qwen2.5:7b",
        "cloud": "gpt-4o-mini",
    }

    def complete_with_model(self, request: LLMRequest, model: Model) -> LLMResponse:
        model_id = self.TIER_MODEL_MAP.get(model.tier, request.model_id)
        request.model_id = model_id
        return self._provider.complete(request)
```

### Layer 3: 工作流编排 → LangGraph

**替换范围**：`backend/src/composition.py` 的 `MockRuntime` (~200 行)

#### 现状问题

`MockRuntime._cyber_dispatch_map()` 手写了 11 个 handler，每个做：
1. 从 `payload` 提取参数
2. 类型转换（dict → dataclass）
3. 调用 Agent 方法
4. `asdict()` 转回 dict

这是典型的"手写状态机"，且没有：
- Agent 间数据自动传递
- 错误重试
- checkpoint/resume
- 红蓝紫对抗循环

#### 替换后

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# State 复用 protocol 类型
class AttackChainState(TypedDict):
    target_range: str
    assets: list[dict]           # Asset.model_dump()
    findings: list[dict]         # VulnFinding.model_dump()
    chain: dict | None           # AttackChain.model_dump()
    lateral_steps: list[dict]
    critique: dict | None
    valid: bool

# 节点 = 现有 Agent 的包装
def recon_node(state: AttackChainState) -> dict:
    agent = ReconAgent(provider)
    assets = agent.scan(state["target_range"])
    return {"assets": [a.model_dump() for a in assets]}

def vuln_node(state: AttackChainState) -> dict:
    agent = VulnCorrelatorAgent(provider)
    findings = agent.correlate([Asset(**a) for a in state["assets"]])
    return {"findings": [f.model_dump() for f in findings]}

def exploit_node(state: AttackChainState) -> dict:
    agent = ExploitPlannerAgent(provider)
    chain = agent.plan([VulnFinding(**f) for f in state["findings"]])
    return {"chain": chain.model_dump()}

def critic_node(state: AttackChainState) -> dict:
    agent = CriticAgent(provider)
    result = agent.critique(state["chain"], side="red")
    return {"critique": result, "valid": result.get("valid", False)}

# 条件路由：神经-符号循环
def route_after_critic(state: AttackChainState) -> str:
    """如果 critic 不通过，回到 exploit_planner 重新规划。"""
    if not state.get("valid", False):
        return "exploit_planner"  # 循环
    return "lateral_move"

# 构建图
graph = StateGraph(AttackChainState)
graph.add_node("recon", recon_node)
graph.add_node("vuln_correlator", vuln_node)
graph.add_node("exploit_planner", exploit_node)
graph.add_node("critic", critic_node)
graph.add_node("lateral_move", lateral_node)

graph.set_entry_point("recon")
graph.add_edge("recon", "vuln_correlator")
graph.add_edge("vuln_correlator", "exploit_planner")
graph.add_edge("exploit_planner", "critic")
graph.add_conditional_edges("critic", route_after_critic)  # 有环！
graph.add_edge("lateral_move", END)

app = graph.compile(checkpointer=MemorySaver())  # 自动 checkpoint
```

**收益**：
- 删除 ~200 行手写 dispatch map
- 获得 checkpoint/resume（超长程任务可中断恢复）
- 获得流式输出（`app.stream()` → SSE → 前端）
- 神经-符号循环自然表达（有环图）
- 蓝队防御链同理（detector → triage → threat_hunt → ir_planner → forensics）

---

## 4. 替换前后代码量对比

| 模块 | 替换前 | 替换后 | 减少 |
|------|--------|--------|------|
| `agents/tools/llms/` (4 Provider) | ~220 行 / 4 文件 | ~30 行 / 1 文件 | -86% |
| `agents/action/` (11 Agent JSON parse) | ~550 行 | ~220 行 | -60% |
| `backend/src/composition.py` MockRuntime | ~200 行 dispatch | ~60 行 graph | -70% |
| `protocol/*.py` (to_dict/from_dict) | ~50 行手写序列化 | 0 行（Pydantic 自动） | -100% |
| **合计** | ~1020 行 | ~310 行 | **-70%** |

同时新增能力：checkpoint / 流式 / 有环图 / 自动重试 / JSON Schema / 100+ 模型兼容。

---

## 5. 保留不变的模块

| 模块 | 保留原因 |
|------|---------|
| `protocol/cyber.py` 的攻防类型定义 | 业务领域类型，框架无关（仅 dataclass→Pydantic 迁移） |
| `protocol/graph.py` 的拓扑类型 | 业务领域类型，Graph/GraphNode/GraphEdge 是项目核心 |
| `protocol/message.py` 的 Message 信封 | 项目通信契约，不应由框架定义 |
| `agents/planning/engine/router/` Top-K 路由 | 项目特有算法，LangGraph 不提供低熵稀疏路由 |
| `agents/planning/engine/router/election.py` 异构选举 | 项目特有点积选举算法 |
| `agents/planning/engine/scheduler/` 端边云调度 | 项目特有调度策略 |
| `agents/planning/engine/topology/` 活跃子图 | 项目特有拓扑计算 |
| `agents/memory/compression/` 上下文压缩 | 项目特有超长程压缩算法 |
| `agents/memory/recall/` 唤醒机制 | 项目特有记忆检索策略 |

**原则**：业务领域逻辑保留，基础设施层替换。

---

## 6. 迁移路线（5 阶段）

### 阶段 1: Protocol Pydantic 迁移（1 域 / ≤8 文件）
- [ ] `protocol/cyber.py` → Pydantic BaseModel
- [ ] `protocol/message.py` → Pydantic
- [ ] `protocol/graph.py` → Pydantic
- [ ] `protocol/agent.py` → Pydantic
- [ ] `protocol/event.py` → Pydantic
- [ ] `protocol/scheduler.py` → Pydantic
- [ ] `protocol/memory.py` → Pydantic
- [ ] `protocol/tool.py` / `heartbeat.py` / `sync.py` → Pydantic
- [ ] 更新所有引用 `asdict()` → `model_dump()` / `from_dict()` → `model_validate()`
- [ ] 55 测试全通过

### 阶段 2: LLM Provider 统一（≤4 文件）
- [ ] 安装 `litellm` + `instructor`
- [ ] 新建 `agents/tools/llms/unified_provider.py`
- [ ] `ModelRouter` 改为委托 `UnifiedProvider`
- [ ] MockProvider 保留（测试用），但实现 `litellm` mock adapter
- [ ] 删除 `openai_provider.py` / `anthropic_provider.py` / `local_provider.py`
- [ ] 55 测试全通过

### 阶段 3: Agent 结构化输出（≤8 文件/批，分 2 批）
- [ ] 批 1（红队 4 Agent）：`recon` / `vuln_correlator` / `exploit_planner` / `lateral_move`
- [ ] 批 2（蓝队 5 + 紫队 2 Agent）：`detector` / `triage` / `threat_hunt` / `ir_planner` / `forensics` / `critic` / `reviewer`
- [ ] 每个 Agent 的 `json.loads` 替换为 `instructor` 结构化调用
- [ ] 删除 `SYSTEM_PROMPT` 中的 JSON 格式说明（instructor 自动注入）
- [ ] 55 测试全通过

### 阶段 4: LangGraph 编排（≤4 文件）
- [ ] 安装 `langgraph`
- [ ] 新建 `agents/planning/orchestrator/graph.py`（红队攻击链图）
- [ ] 新建 `agents/planning/orchestrator/defense_graph.py`（蓝队防御链图）
- [ ] `MockRuntime` 替换为 `GraphRuntime`（实现 `RuntimeAPI`）
- [ ] `backend/src/composition.py` 注入 `GraphRuntime`
- [ ] 55 测试全通过

### 阶段 5: 事件总线 + 流式（≤2 文件）
- [ ] 新建 `agents/planning/engine/eventbus/impl.py`（基于 `blinker` 或 LangGraph callback）
- [ ] LangGraph `app.stream()` → SSE → 前端 `EventSource`
- [ ] 55 测试全通过

---

## 7. 依赖变更

```toml
# pyproject.toml — 新增
[project]
dependencies = [
    # 现有
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.0",
    "sqlalchemy>=2.0",
    "aiosqlite>=0.20",
    "httpx>=0.27",
    # 新增
    "litellm>=1.40",          # 统一 LLM 调用（替代 4 个手写 Provider）
    "instructor>=1.3",        # 结构化输出（替代 json.loads + try/except）
    "langgraph>=0.2",         # 工作流编排（替代手写 dispatch map）
    "langgraph-checkpoint-sqlite>=2.0",  # checkpoint 持久化
]

# 移除（litellm 内部依赖 httpx，但项目仍需要 httpx 做其他 HTTP 调用）
# httpx 保留
```

---

## 8. 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Pydantic 迁移破坏现有 55 测试 | 中 | 中 | 先跑测试确认基线，逐文件迁移每步验证 |
| litellm 版本兼容性 | 低 | 低 | 锁定版本，CI 验证 |
| instructor 重试导致 token 消耗增加 | 中 | 低 | 配置 `max_retries=1`，MockProvider 不走 instructor |
| LangGraph 学习曲线 | 中 | 中 | 先包装现有 Agent，不改算法 |
| 领域边界被框架侵入 | 低 | 高 | LangGraph 只在 orchestrator 层，不进入 protocol/engine |

---

## 9. 不推荐的替换

| 模块 | 为什么不替换 |
|------|-------------|
| `protocol/` → LangChain Message | LangChain Message 是对话格式，项目 Message 是信封格式（含 trace_id/ttl/优先级），语义不同 |
| `engine/router` → LangGraph 条件边 | router 的 Top-K 选举是项目核心算法，条件边只是调用入口 |
| `engine/scheduler` → litellm router | litellm 无端边云调度能力 |
| `memory/compression` → LangChain memory | LangChain memory 是对话级，项目需要超长程压缩+唤醒 |
| `protocol/cyber.py` 攻防类型 → 任何框架 | 业务领域类型，框架无关 |

---

## 10. 最终架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (React + Vite)                      │
├─────────────────────────────────────────────────────────────┤
│                    后端 (FastAPI)                             │
│  composition.py → 注入 GraphRuntime                          │
├─────────────────────────────────────────────────────────────┤
│  LangGraph 编排层 (新)                                       │
│  ┌─────────────────┐  ┌──────────────────┐                  │
│  │ AttackChainGraph│  │ DefenseChainGraph│                  │
│  │ (红队攻击链)    │  │ (蓝队防御链)      │                  │
│  │ checkpoint ✓   │  │ checkpoint ✓     │                  │
│  │ 流式输出 ✓     │  │ 流式输出 ✓       │                  │
│  │ 神经-符号循环 ✓ │  │ 神经-符号循环 ✓   │                  │
│  └───────┬────────┘  └────────┬─────────┘                  │
│          │                    │                              │
│  ┌───────▼────────────────────▼─────────┐                   │
│  │     Agent 层 (litellm + instructor)   │                   │
│  │  ReconAgent │ DetectorAgent │ ...     │ ← 结构化输出       │
│  │  每个 ~20 行（替代 ~50 行）            │                   │
│  └───────────────────┬──────────────────┘                   │
│                      │                                       │
│  ┌───────────────────▼──────────────────┐                   │
│  │     UnifiedProvider (litellm)         │ ← 1 文件 ~30 行    │
│  │  (替代 4 个手写 Provider ~220 行)     │                   │
│  └───────────────────┬──────────────────┘                   │
│                      │                                       │
│  ┌───────────────────▼──────────────────┐                   │
│  │     ModelRouter + Scheduler (保留)    │ ← 项目特有算法     │
│  │  端边云调度 / Top-K 路由 / 异构选举    │                   │
│  └──────────────────────────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  Protocol (Pydantic) ← 数据契约统一                          │
│  cyber.py │ message.py │ graph.py │ ... (自动序列化/验证)     │
├─────────────────────────────────────────────────────────────┤
│  Memory (保留核心算法 + 增强)                                │
│  compression ✓ │ recall ✓ │ + checkpoint (LangGraph)       │
└─────────────────────────────────────────────────────────────┘
```
