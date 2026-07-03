# 06_SCHEMA_SPEC.md — 数据 Schema 规范（Pydantic）

> 上游：`00_PROJECT_SPEC.md`、`04_PROTOCOL_SPEC.md`。本文件定义全项目统一数据结构。
> **所有 Schema 使用 Pydantic v2（`pydantic.BaseModel`）**。这是规范层的权威定义。
>
> **现状与目标**：`protocol/*.py` 当前为 `@dataclass` 实现（v1 基线，26 类型）。本规范要求将 `protocol/` 升级为 Pydantic `BaseModel`，作为唯一契约实现。迁移在 P1（Protocol 阶段）完成：以 Pydantic 模型替换 dataclass，保持字段名与语义一致，并补 `model_validate`/`model_dump` 往返。在迁移完成前，业务层须通过 `protocol/` 导入，不直接依赖本文件的代码示例。

---

## 0. 依赖与约定

- 依赖：`pydantic>=2.0`（须在 P1 加入 `pyproject.toml`）。
- 所有模型继承 `pydantic.BaseModel`；字段用 `Field(default=..., description=...)`。
- 枚举用 `str, Enum`（与 `protocol/` 一致，可 JSON 序列化）。
- ID 自动生成用 `Field(default_factory=lambda: uuid.uuid4().hex)`。
- 时间戳用 `Field(default_factory=time.time)`。
- `model_config = ConfigDict(extra="ignore")`（前向容忍未知字段）。
- 命名与 `protocol/` 字段名严格一致（snake_case）。

---

## 1. MessageSchema（消息信封）

```python
from pydantic import BaseModel, Field, ConfigDict
import time, uuid
from enum import Enum
from typing import Any

class NodeRefSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    node_id: str
    node_type: str
    name: str = ""

class HeaderSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str = "1.0"
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    compress: str = ""

class MessageSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str = ""
    task_id: str = ""
    workflow_id: str = ""
    sender: NodeRefSchema = Field(default_factory=lambda: NodeRefSchema(node_id="", node_type=""))
    receiver: NodeRefSchema = Field(default_factory=lambda: NodeRefSchema(node_id="", node_type=""))
    priority: int = 0
    ttl: int = 64
    compression: str = ""
    timestamp: float = Field(default_factory=time.time)
    payload: Any = None
    header: HeaderSchema = Field(default_factory=HeaderSchema)
```

---

## 2. EventSchema（事件）

```python
class EventType(str, Enum):
    AgentStart = "agent.start"
    AgentFinish = "agent.finish"
    ToolCall = "tool.call"
    ToolFinish = "tool.finish"
    Retry = "task.retry"
    Rollback = "task.rollback"
    MemoryUpdate = "memory.update"
    GraphUpdate = "graph.update"

class EventSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.AgentStart
    task_id: str = ""
    source: NodeRefSchema = Field(default_factory=lambda: NodeRefSchema(node_id="", node_type=""))
    payload: dict = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    @property
    def topic(self) -> str:
        return self.event_type.value
```

---

## 3. TaskSchema（任务）

```python
class TaskStatus(str, Enum):
    Pending = "pending"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"
    RolledBack = "rolled_back"
    Cancelled = "cancelled"

class RetryPolicySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_attempts: int = 3
    backoff: float = 1.5

class RollbackPlanSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    steps: list = Field(default_factory=list)

class TaskSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    plan: dict = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.Pending
    retry: RetryPolicySchema = Field(default_factory=RetryPolicySchema)
    rollback: RollbackPlanSchema = Field(default_factory=RollbackPlanSchema)
    dependency: list = Field(default_factory=list)
    priority: int = 0
```

---

## 4. WorkflowSchema（工作流）

```python
class PlanSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    plan_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    dag: dict = Field(default_factory=dict)
    tasks: list = Field(default_factory=list)

class ScheduleSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schedule_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    assigned_to: str = ""
    queued_at: float = 0.0
    priority: int = 0

class WorkflowSchema(PlanSchema):
    """Workflow = Plan(DAG) + 执行状态。"""
    status: TaskStatus = TaskStatus.Pending
    current_node: str = ""
    checkpoint: dict = Field(default_factory=dict)
```

---

## 5. AgentSchema（智能体）

```python
class AgentStatus(str, Enum):
    Idle = "idle"
    Running = "running"
    Waiting = "waiting"
    Failed = "failed"
    Offline = "offline"

class AgentSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_id: str
    name: str
    role: str
    ref: NodeRefSchema = Field(default_factory=lambda: NodeRefSchema(node_id="", node_type="agent"))
    capabilities: list = Field(default_factory=list)
    status: AgentStatus = AgentStatus.Idle
    trust_score: float = 1.0
    success_rate: float = 1.0
```

---

## 6. MemorySchema（记忆）

```python
class MemoryPacketSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    working: dict = Field(default_factory=dict)
    semantic: dict = Field(default_factory=dict)
    episodic: dict = Field(default_factory=dict)
    archive: dict = Field(default_factory=dict)
    embedding: list = Field(default_factory=list)
    summary: str = ""
    compression: dict = Field(default_factory=dict)
    session_id: str = ""
    task_id: str = ""
    kind: str = "normal"       # B1: normal | decision | digest
    recent: bool = False        # B1: 是否最近步
```

---

## 7. ToolSchema（工具）

```python
class ToolCallSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    call_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    args: dict = Field(default_factory=dict)
    timeout: float = 30.0
    permission: str = ""

class ToolResultSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    call_id: str = ""
    ok: bool = True
    output: object = None
    error: str = ""
    meta: dict = Field(default_factory=dict)

class ToolSpecSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: str = ""
    args_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    permission: str = "default"
    resource_limit: dict = Field(default_factory=dict)
```

---

## 8. GraphSchema（动态图）

```python
class NodeKind(str, Enum):
    Agent = "agent"
    Task = "task"
    Memory = "memory"
    Tool = "tool"

class GraphNodeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    node_id: str
    kind: NodeKind
    name: str = ""
    capabilities: list = Field(default_factory=list)
    trust_score: float = 1.0
    success_rate: float = 1.0
    latency: float = 0.0
    status: str = "active"   # C1: active | idle | degraded

class GraphEdgeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    src: str
    dst: str
    weight: float = 1.0
    entropy: float = 0.0
    latency: float = 0.0
    trust_score: float = 1.0
    success_rate: float = 1.0

class GraphSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nodes: dict = Field(default_factory=dict)
    edges: list = Field(default_factory=list)

class RouteSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    task_id: str
    path: list = Field(default_factory=list)
    cost: float = 0.0
    entropy: float = 0.0

class GraphDiffSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    added_nodes: list = Field(default_factory=list)
    removed_nodes: list = Field(default_factory=list)
    added_edges: list = Field(default_factory=list)
    removed_edges: list = Field(default_factory=list)
    updated_edges: list = Field(default_factory=list)
```

---

## 9. StateSchema（状态快照）— 新增

> 用于检查点/快照/回放，聚合某一时刻的系统运行态。

```python
class StateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    state_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    task_id: str = ""
    task_status: TaskStatus = TaskStatus.Pending
    workflow: WorkflowSchema | None = None
    graph: GraphSchema | None = None
    agents: list[AgentSchema] = Field(default_factory=list)
    memory: MemoryPacketSchema | None = None
    timestamp: float = Field(default_factory=time.time)
    checkpoint_ref: str = ""
```

---

## 10. ContextSchema（上下文）— 新增

> Agent 运行上下文，由 `agents/perception/context/` 管理（Token 预算/裁剪/会话隔离）。

```python
class ContextSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    context_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    token_budget: int = 8192
    token_used: int = 0
    history: list[MessageSchema] = Field(default_factory=list)
    working_memory: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    trace_id: str = ""

    @property
    def token_remaining(self) -> int:
        return max(0, self.token_budget - self.token_used)
```

---

## 11. 辅助 Schema

### HeartbeatSchema
```python
class HeartbeatSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    node: NodeRefSchema = Field(default_factory=lambda: NodeRefSchema(node_id="", node_type=""))
    cpu: float = 0.0
    gpu: float = 0.0
    latency: float = 0.0
    memory: float = 0.0
    token: int = 0
    status: str = "healthy"
    timestamp: float = Field(default_factory=time.time)
```

### SyncSchema（端边云同步）
```python
class SyncStatus(str, Enum):
    Pending = "pending"
    InFlight = "in_flight"
    Applied = "applied"
    Conflict = "conflict"
    Failed = "failed"

class SyncPacketSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sync_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: str = ""
    target: str = ""
    payload: dict = Field(default_factory=dict)
    status: SyncStatus = SyncStatus.Pending
    vector_clock: dict = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
```

---

## 12. Schema 与 protocol/ 的关系

| 本规范 Schema | 对应 `protocol/` 类型 | 状态 |
|---------------|----------------------|------|
| MessageSchema | Message/NodeRef/Header | 待迁移（dataclass→Pydantic） |
| EventSchema | Event/EventType | 待迁移 |
| TaskSchema | Task/TaskStatus/RetryPolicy/RollbackPlan | 待迁移 |
| WorkflowSchema | Plan/Schedule（扩展） | 待迁移 + 扩展 |
| AgentSchema | Agent/AgentStatus | 待迁移 |
| MemorySchema | MemoryPacket | 待迁移 |
| ToolSchema | ToolCall/ToolResult/ToolSpec | 待迁移 |
| GraphSchema | Graph/GraphNode/GraphEdge/Route/GraphDiff/NodeKind | 待迁移（GraphNode 已扩 status） |
| StateSchema | （新增） | 新增（P2 检查点阶段） |
| ContextSchema | （新增） | 新增（P5 感知阶段） |
| HeartbeatSchema | Heartbeat | 待迁移 |
| SyncSchema | SyncPacket/SyncStatus | 待迁移 |
| CyberSchema（§14） | Asset/VulnFinding/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel | dataclass（A1 新增） |

> 迁移原则：字段名/语义/默认值不变；序列化方法由 `to_dict`/`from_dict` 改为 `model_dump()`/`model_validate()`；`__all__` 导出不变；下游 `from {domain}.api import` 不受影响。

---

## 14. CyberSchema（攻防类型，A1）

> 对应 `protocol/cyber.py`，当前为 `@dataclass`（非 Pydantic）。

| Schema | id 字段 | 关键字段 | 说明 |
|--------|---------|---------|------|
| AssetSchema | asset_id | ip/host/os/services | 网络资产 |
| VulnFindingSchema | finding_id | cve_id/asset_id/cvss/attack_surface | 漏洞发现 |
| AttackStepSchema | step_id | technique/from_asset/to_asset/success | 攻击步骤 |
| AttackChainSchema | chain_id | target/steps/status | 攻击链（含 to_dict/from_dict） |
| AlertSchema | alert_id | severity/src/dst/technique/raw | 告警 |
| DefenseActionSchema | action_id | kind/target/rationale | 防御动作 |
| ResponsePlanSchema | plan_id | actions/rollback/strategy | 响应计划 |
| ThreatIntelSchema | intel_id | source/iocs/techniques | 威胁情报 |

id 字段统一 `*_id` 约定。迁移时统一转为 Pydantic（同 §12 原则）。

---

## 13. 校验与生命周期

- 所有跨模块数据须经 Schema 校验（`model_validate`）后再使用。
- 字段新增必须可选；废弃先 deprecated；移除需 major bump。
- 接收方 `extra="ignore"` 忽略未知字段（前向容忍）。
- 测试：`tests/unit/protocol/` 覆盖每个 Schema 的 `model_validate`↔`model_dump` 往返 + 边界值。
