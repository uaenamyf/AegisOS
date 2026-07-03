# 04_PROTOCOL_SPEC.md — 通信协议规范

> 上游：`00_PROJECT_SPEC.md`。本文件是 `protocol/` 的规范来源与权威定义。
> 所有字段以 `protocol/*.py` 现有实现为基线（v1），目标向 Pydantic 演进（见 `06_SCHEMA_SPEC.md`）。
> AegisOS 不使用裸 JSON 跨模块通信，一律走 `Message` 信封 + 强类型 Payload。

---

## 1. Message（消息信封）

分层结构：`Header → Session → Task → Node → Route → Payload → Metadata → Signature`

| 字段 | 类型 | 说明 |
|------|------|------|
| `message_id` | str | 全局唯一（uuid4 hex，自动生成） |
| `parent_id` | str? | 关联父消息 |
| `task_id` | str? | 关联任务 |
| `workflow_id` | str? | 关联工作流 |
| `sender` | `NodeRef` | 发送节点 |
| `receiver` | `NodeRef` | 接收节点 |
| `priority` | int | 优先级（0 默认，越大越优先） |
| `ttl` | int | 存活跳数（默认 64，防环路） |
| `compression` | str? | 压缩算法标识 |
| `timestamp` | float | 时间戳（time.time，自动） |
| `payload` | `Any`（须为 `protocol` 类型） | 强类型载荷 |
| `header` | `Header` | 见下 |

### Header
| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | str | 协议版本（默认 `"1.0"`） |
| `trace_id` | str | 链路追踪 ID（uuid4 hex，自动） |
| `session_id` | str | 会话 ID |
| `compress` | str | 压缩算法 |

### NodeRef
| 字段 | 类型 | 说明 |
|------|------|------|
| `node_id` | str | 节点 ID |
| `node_type` | str | 节点类型（agent/task/memory/tool/edge/cloud…） |
| `name` | str | 显示名 |

序列化：`Message.to_dict()` / `Message.from_dict()`；跨网传输须走此信封。

---

## 2. Event（事件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `event_id` | str | 唯一（uuid4 hex，自动） |
| `event_type` | `EventType` | 事件类型枚举 |
| `task_id` | str | 关联任务 |
| `source` | `NodeRef` | 事件源 |
| `payload` | dict | 载荷 |
| `timestamp` | float | 时间戳（自动） |
| `topic` | str (property) | = `event_type.value`，如 `agent.start` |

### EventType（8 类）
| 枚举 | 值 | 触发 | 载荷 |
|------|----|------|------|
| `AgentStart` | `agent.start` | Agent 开始执行 | agent_id, task_id |
| `AgentFinish` | `agent.finish` | Agent 完成 | agent_id, task_id, result |
| `ToolCall` | `tool.call` | 工具调用 | tool_name, args |
| `ToolFinish` | `tool.finish` | 工具完成 | tool_name, result |
| `Retry` | `task.retry` | 重试 | task_id, attempt |
| `Rollback` | `task.rollback` | 回滚 | task_id, reason |
| `MemoryUpdate` | `memory.update` | 记忆变更 | memory_packet |
| `GraphUpdate` | `graph.update` | 拓扑图变更 | graph_diff |

> 事件封装于 `Message` 信封投递；详见 `07_EVENT_SPEC.md`。

---

## 3. Task（任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | str | 唯一（uuid4 hex，自动） |
| `goal` | str | 目标 |
| `plan` | dict | 计划（DAG 表示） |
| `status` | `TaskStatus` | 状态枚举 |
| `retry` | `RetryPolicy` | 重试策略 |
| `rollback` | `RollbackPlan` | 回滚策略 |
| `dependency` | list | 依赖任务 ID 列表 |
| `priority` | int | 优先级 |

### TaskStatus
`Pending` · `Running` · `Succeeded` · `Failed` · `RolledBack` · `Cancelled`

### RetryPolicy
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `max_attempts` | int | 3 | 最大重试次数 |
| `backoff` | float | 1.5 | 指数退避基数 |

### RollbackPlan
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | bool | False | 是否启用回滚 |
| `steps` | list | [] | 回滚步骤 |

---

## 4. Workflow（工作流）

基于 `Plan` 的 DAG 模型：

### Plan
| 字段 | 类型 | 说明 |
|------|------|------|
| `plan_id` | str | 唯一（自动） |
| `goal` | str | 目标 |
| `dag` | dict | DAG 结构（节点=Task，边=dependency） |
| `tasks` | list | 任务列表 |

### Schedule
| 字段 | 类型 | 说明 |
|------|------|------|
| `schedule_id` | str | 唯一（自动） |
| `task_id` | str | 关联任务 |
| `assigned_to` | str | 分配给的节点/Agent |
| `queued_at` | float | 入队时间 |
| `priority` | int | 优先级 |

生命周期：`Created → Planned(DAG) → Routed → Scheduled → Running → Checkpointed → (Retry|Rollback) → Succeeded|Failed|Cancelled`

---

## 5. Memory（记忆）

### MemoryPacket
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `working` | dict | {} | 工作记忆 |
| `semantic` | dict | {} | 语义记忆（知识库） |
| `episodic` | dict | {} | 情景记忆 |
| `archive` | dict | {} | 归档 |
| `embedding` | list | [] | 向量嵌入 |
| `summary` | str | "" | 摘要 |
| `compression` | dict | {} | 压缩信息 |
| `session_id` | str | "" | 会话 ID |
| `task_id` | str | "" | 任务 ID |
| `kind` | str | "normal" | 记忆类型：normal \| decision \| digest（B1 扩展） |
| `recent` | bool | False | 是否最近步（压缩时保留）（B1 扩展） |

接口：`read(query)→MemoryPacket`、`write(packet)→bool`、`retrieve(query)→list`。幂等写入（packet id 去重）。

---

## 6. Tool（工具）

### ToolCall
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `call_id` | str | 自动 | 调用 ID |
| `name` | str | "" | 工具名 |
| `args` | dict | {} | 参数 |
| `timeout` | float | 30.0 | 超时（秒） |
| `permission` | str | "" | 权限标识 |

### ToolResult
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `call_id` | str | "" | 关联调用 |
| `ok` | bool | True | 是否成功 |
| `output` | object | None | 输出 |
| `error` | str | "" | 错误信息 |
| `meta` | dict | {} | 元信息 |

### ToolSpec
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | str | — | 工具名（必填） |
| `description` | str | "" | 描述 |
| `args_schema` | dict | {} | 参数 Schema |
| `output_schema` | dict | {} | 输出 Schema |
| `permission` | str | "default" | 权限等级 |
| `resource_limit` | dict | {} | 资源限制 |

工具经 `agents/action/execution/executor/` 沙箱执行；每次调用发 `ToolCall`/`ToolFinish` 事件。

---

## 7. Graph（动态图）

### NodeKind
`Agent` · `Task` · `Memory` · `Tool`

### GraphNode
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `node_id` | str | — | 节点 ID |
| `kind` | `NodeKind` | — | 节点类型 |
| `name` | str | "" | 显示名 |
| `capabilities` | list | [] | 能力 |
| `trust_score` | float | 1.0 | 信任度（0–1） |
| `success_rate` | float | 1.0 | 成功率 |
| `latency` | float | 0.0 | 延迟 |
| `status` | str | "active" | 节点状态：active \| idle \| degraded（C1 扩展） |

### GraphEdge
| 字段 | 类型 | 说明 |
|------|------|------|
| `src` | str | 源节点 |
| `dst` | str | 目标节点 |
| `weight` | float | 权重 |
| `entropy` | float | 通信熵（赛事核心） |
| `latency` | float | 延迟 |
| `trust_score` | float | 信任度 |
| `success_rate` | float | 成功率 |

### Graph
`nodes: dict[node_id→GraphNode]`、`edges: list[GraphEdge]`；`add_node`/`add_edge`。

### Route
| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | str | 关联任务 |
| `path` | list | 节点链路 |
| `cost` | float | 总成本 |
| `entropy` | float | 总熵 |

### GraphDiff
`added_nodes` · `removed_nodes` · `added_edges` · `removed_edges` · `updated_edges`（驱动 `GraphUpdate` 事件）。

---

## 8. Agent（智能体）

### AgentStatus
`Idle` · `Running` · `Waiting` · `Failed` · `Offline`

### Agent
| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | str | 唯一（必填） |
| `name` | str | 名称（必填） |
| `role` | str | 角色（必填） |
| `ref` | `NodeRef` | 节点引用（默认 node_type="agent"） |
| `capabilities` | list | 能力 |
| `status` | `AgentStatus` | 状态（默认 Idle） |
| `trust_score` | float | 信任度（默认 1.0） |
| `success_rate` | float | 成功率（默认 1.0） |

---

## 9. Scheduler（调度协议）

- 调度单元 = `Schedule`；调度对象 = `Task`。
- 策略：多级优先级队列 + DAG 拓扑序 + 资源 + 信任度；抢占；指数退避重试（`RetryPolicy.backoff`）；超时熔断；死锁检测；老化反饥饿。
- 调度结果以 `Schedule` 表示并经事件流广播。

---

## 10. Heartbeat（心跳）

| 字段 | 类型 | 说明 |
|------|------|------|
| `node` | `NodeRef` | 节点 |
| `cpu` | float | CPU 占用 |
| `gpu` | float | GPU 占用 |
| `latency` | float | 延迟 |
| `memory` | float | 内存占用 |
| `token` | int | Token 用量 |
| `status` | str | 健康状态（默认 "healthy"） |
| `timestamp` | float | 时间戳（自动） |

节点定期发心跳；超时判定失联，触发离线优先 + 同步。

---

## 11. Checkpoint（检查点）

- 位置：`agents/memory/checkpoint/`、`agents/memory/snapshot/`。
- 语义：周期性保存任务/记忆快照，失败后从检查点恢复，避免全量重放。
- 协议表现：以 `MemoryPacket.compression` + `session_id`/`task_id` 关联恢复点。

---

## 12. Retry & Rollback（重试与回滚）

- **Retry**：`Task.retry`（RetryPolicy）；失败后 `Retry` 事件；指数退避 `backoff`；超 `max_attempts` 进失败/死信。
- **Rollback**：`Task.rollback`（RollbackPlan）；`enabled=true` 时按 `steps` 回滚；发 `Rollback` 事件；状态转 `RolledBack`。

---

## 13. Compression（压缩）

- `Message.compression` / `Header.compress` 标识压缩算法。
- 记忆侧 `MemoryPacket.compression` 保存压缩信息（摘要/降维）。
- 默认不压缩；大载荷/低带宽通道启用（MessagePack/protobuf 可选）。

---

## 14. Version（版本）

- `Header.version` 默认 `"1.0"`；语义化版本 `MAJOR.MINOR.PATCH`。
- 字段新增必须可选；废弃先 deprecated 一个 minor；移除需 major bump。
- 接收方忽略未知字段（前向容忍）。
- URL 版本 `/api/v1/`。

---

## 15. Signature（签名）

- `Message` 信封预留 `Signature` 层（Header/Metadata 扩展）。
- 用于消息完整性校验与来源鉴权（gateway 侧校验）。
- 密钥不走载荷；签名算法在 `tooling/configs/` 登记。

---

## 16. 动态路由协议（赛事亮点）

```
Task → Semantic Graph → Agent Graph → Dynamic Routing
    → Sparse Communication → Adaptive Graph → Graph Update
```

- Router 维护 `GraphNode`/`GraphEdge`（含 entropy/latency/trust_score/success_rate）。
- 动态计算稀疏链路（非全广播）：`Agent → Planner → Memory → Coder → Reviewer → Executor`。
- **低熵稀疏路由**（C2）：`route(message, topology, required_capability) → list[NodeRef]`，Top-K=3，按 `success_rate - latency` 排序，禁全广播。
- **异构选举**（C3）：`elect(task_features, instances, capability_vectors) → NodeRef`，任务特征向量与能力向量点积最大者当选。
- 拓扑变化经 `GraphDiff` → `GraphUpdate` 事件自适应更新。
- 对齐赛题：Dynamic Heterogeneous Topology + Low Entropy Communication。

---

## 17. 端边云同步协议

### SyncStatus
`Pending` · `InFlight` · `Applied` · `Conflict` · `Failed`

### SyncPacket
| 字段 | 类型 | 说明 |
|------|------|------|
| `sync_id` | str | 唯一（自动） |
| `source` | str | 源节点 |
| `target` | str | 目标节点 |
| `payload` | dict | 同步载荷 |
| `status` | `SyncStatus` | 状态（默认 Pending） |
| `vector_clock` | dict | 向量时钟（因果序） |
| `timestamp` | float | 时间戳（自动） |

离线优先；`Conflict` 状态触发冲突解决策略。

### 端边云调度（D1）
`schedule(task, models, required_capability) → Model`：`task.privacy=local` 或低 `latency_budget` 选 edge 模型，否则选 cloud 模型。

---

## 18. 攻防协议类型（protocol/cyber.py，A1）

> 赛事核心数据类型，定义在 `protocol/cyber.py`，全部为 `@dataclass`。

| 类型 | id 字段 | 关键字段 | 说明 |
|------|---------|---------|------|
| `Asset` | `asset_id` | ip/host/os/services | 网络资产 |
| `VulnFinding` | `finding_id` | cve_id/asset_id/cvss/attack_surface | 漏洞发现 |
| `AttackStep` | `step_id` | technique/from_asset/to_asset/success | 攻击步骤（ATT&CK technique） |
| `AttackChain` | `chain_id` | target/steps/status | 攻击链（含 `to_dict`/`from_dict`） |
| `Alert` | `alert_id` | severity/src/dst/technique/raw | 告警 |
| `DefenseAction` | `action_id` | kind/target/rationale | 防御动作 |
| `ResponsePlan` | `plan_id` | actions/rollback/strategy | 响应计划 |
| `ThreatIntel` | `intel_id` | source/iocs/techniques | 威胁情报 |

id 字段统一 `*_id` 约定（匹配 `node_id`/`message_id`）。`Alert.raw: dict = field(default_factory=dict)`。

---

## 19. 序列化与兼容

- 默认 JSON + schema 校验；可选 MessagePack/protobuf 用于高性能通道。
- 所有数据类定义在 `protocol/*.py`，禁止业务层自造并行结构。
- gRPC `.proto` 由 `protocol/` 类型生成，保持单一可信源（`aegis.protocol.v1`）。
