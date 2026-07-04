# protocol/ 模块实现文档

> 契约层 — 全系统唯一数据契约。所有跨模块通信的参数/返回值必须使用 `protocol/` 类型。

📁 规范：[`developer/specs/04_PROTOCOL_SPEC.md`](../developer/specs/04_PROTOCOL_SPEC.md) · 模块规范：[`AGENT.md`](AGENT.md)

---

## 已实现文件（10 个 .py）

### `message.py` — 消息信封
| 类型 | 字段 | 说明 |
|------|------|------|
| `Message` | `message_id` · `parent_id` · `task_id` · `sender` · `receiver` · `priority` · `ttl` · `timestamp` · `payload` | 跨模块通信统一载体 |
| `NodeRef` | `node_id` · `node_type` | 节点引用（路由目标） |

**用途**：所有跨域调用都以 Message 为信封，payload 携带强类型数据。

---

### `event.py` — 事件总线
| 类型 | 字段 | 说明 |
|------|------|------|
| `EventType` (Enum) | 8 种事件 | `agent.start` · `agent.finish` · `tool.call` · `tool.finish` · `task.retry` · `task.rollback` · `memory.update` · `graph.update` |
| `Event` | `event_id` · `event_type` · `task_id` · `source` · `payload` · `timestamp` | 事件总线消息 |

---

### `agent.py` — 智能体注册
| 类型 | 字段 |
|------|------|
| `AgentStatus` (Enum) | `idle` · `running` · `waiting` · `failed` · `offline` |
| `Agent` | `agent_id` · `name` · `role` · `ref` · `capabilities` · `status` · `trust_score` · `success_rate` |

---

### `scheduler.py` — 任务调度
| 类型 | 字段 | 说明 |
|------|------|------|
| `TaskStatus` (Enum) | `pending` · `running` · `succeeded` · `failed` · `rolled_back` · `cancelled` | |
| `Task` | `task_id` · `goal` · `privacy` · `latency_budget` · `status` | ⚠️ **缺 payload 字段**，MockRuntime 用 getattr fallback |
| `RetryPolicy` | `max_retries` · `backoff` · `timeout` | |

---

### `memory.py` — 记忆包
| 类型 | 字段 |
|------|------|
| `MemoryPacket` | `task_id` · `kind` · `summary` · `working` · `episodic` · `compression` · `recent` |

`kind` 取值：`decision` · `digest` · `observation` · ...

---

### `graph.py` — 动态异构图
| 类型 | 字段 |
|------|------|
| `NodeKind` (Enum) | `agent` · `task` · `memory` · `tool` |
| `GraphNode` | `node_id` · `kind` · `capabilities` · `status` · `success_rate` · `latency` |
| `Graph` | `nodes` (dict) · `edges` (list) · `add_node()` · `add_edge()` |
| `GraphEdge` | `src` · `dst` · `relation` · `weight` |
| `GraphDiff` | `added_nodes` · `removed_nodes` · `added_edges` · `removed_edges` · `updated_edges` |

---

### `tool.py` — 工具调用
| 类型 | 字段 |
|------|------|
| `ToolCall` | `tool_id` · `name` · `args` |
| `ToolResult` | `tool_id` · `output` · `error` · `success` |
| `ToolSpec` | `name` · `description` · `parameters` |

---

### `heartbeat.py` — 心跳
| 类型 | 字段 |
|------|------|
| `Heartbeat` | `agent_id` · `status` · `timestamp` · `load` |

---

### `sync.py` — 端边云同步
| 类型 | 字段 |
|------|------|
| `SyncStatus` (Enum) | `pending` · `in_flight` · `applied` · `conflict` · `failed` |
| `SyncOp` | `op_id` · `source` · `target` · `payload` · `status` |

---

### `cyber.py` — 攻防协议类型（8 个 dataclass）

| 类型 | 字段 | 说明 |
|------|------|------|
| `Asset` | `asset_id` · `host` · `services` · `os` · `exposure`(external/internal/isolated) | 网络资产 |
| `VulnFinding` | `finding_id` · `cve_id` · `asset_id` · `cvss` · `attack_surface` | 漏洞发现 |
| `AttackStep` | `step_id` · `technique` · `from_asset` · `to_asset` · `success` | 攻击步骤 |
| `AttackChain` | `chain_id` · `target` · `steps` (list) · `status`(planned/executing/success/failed) | 攻击链 DAG |
| `Alert` | `alert_id` · `severity` · `src` · `dst` · `technique` · `raw` | 安全告警 |
| `DefenseAction` | `action_id` · `kind`(monitor/isolate/patch/block) · `target` · `rationale` | 防御动作 |
| `ResponsePlan` | `plan_id` · `actions` (list) · `confidence` · `rollback` (dict) | 响应计划（含回滚） |
| `ThreatIntel` | `technique` · `tactic` · `refs` | 威胁情报（⚠️ 基础结构，无 ATT&CK 映射） |

**AttackChain 特殊方法**：`to_dict()` / `from_dict(data)` — 支持序列化往返

---

## 测试覆盖

| 文件 | 测试数 | 覆盖内容 |
|------|--------|---------|
| [`tests/protocol/test_cyber.py`](../tests/protocol/test_cyber.py) | 6 | 8 个攻防类型字段验证 + AttackChain 序列化/反序列化 |

---

## 未实现 / 待补

- `ThreatIntel` 仅有基础结构，缺 ATT&CK 技战术编号映射
- `Task` 缺 `payload` 字段（当前 MockRuntime.run() 用 getattr 从 goal 解析）
- 规范 `06 §12` 计划将所有 `@dataclass` 迁移为 Pydantic `BaseModel`（尚未执行）
