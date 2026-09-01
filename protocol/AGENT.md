# Protocol 契约层 — AGENT.md

> 本文件是 `protocol/` 模块的开发规范与实现详解。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
全系统通信协议的定义与序列化：Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync。系统唯一数据契约。

## 读取目录（允许读）
- developer/specs/04_PROTOCOL_SPEC.md
- developer/specs/07_EVENT_SPEC.md
- tooling/configs/

## 禁止修改目录
- frontend/
- backend/
- aegisos_agents/
- aegisos_agents/planning/engine/ 业务逻辑

## 输出
- protocol/*.py 数据类
- 序列化/反序列化
- schema 校验

## 依赖
- tooling/configs/

## 接口
Message 信封 + 强类型 Payload；详见 developer/specs/04_PROTOCOL_SPEC.md。

## 测试方式
`pytest tests/protocol/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/protocol/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/protocol/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/protocol.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/04_PROTOCOL_SPEC.md + 06_SCHEMA_SPEC.md
- **数据契约**：本层即契约（无 api/，被各域复用）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（A1 cyber 类型）

---

## 📋 模块实现详解

> 原 `protocol/MODULE.md` 内容，已合并至此。

### 已实现文件（10 个 .py）

#### `message.py` — 消息信封
| 类型 | 字段 | 说明 |
|------|------|------|
| `Message` | `message_id` · `parent_id` · `task_id` · `sender` · `receiver` · `priority` · `ttl` · `timestamp` · `payload` | 跨模块通信统一载体 |
| `NodeRef` | `node_id` · `node_type` | 节点引用（路由目标） |

**用途**：所有跨域调用都以 Message 为信封，payload 携带强类型数据。

---

#### `event.py` — 事件总线
| 类型 | 字段 | 说明 |
|------|------|------|
| `EventType` (Enum) | 8 种事件 | `agent.start` · `agent.finish` · `tool.call` · `tool.finish` · `task.retry` · `task.rollback` · `memory.update` · `graph.update` |
| `Event` | `event_id` · `event_type` · `task_id` · `source` · `payload` · `timestamp` | 事件总线消息 |

---

#### `agent.py` — 智能体注册
| 类型 | 字段 |
|------|------|
| `AgentStatus` (Enum) | `idle` · `running` · `waiting` · `failed` · `offline` |
| `Agent` | `agent_id` · `name` · `role` · `ref` · `capabilities` · `status` · `trust_score` · `success_rate` |

---

#### `scheduler.py` — 任务调度
| 类型 | 字段 | 说明 |
|------|------|------|
| `TaskStatus` (Enum) | `pending` · `running` · `succeeded` · `failed` · `rolled_back` · `cancelled` | |
| `Task` | `task_id` · `goal` · `privacy` · `latency_budget` · `status` | ⚠️ **缺 payload 字段**，MockRuntime 用 getattr fallback |
| `RetryPolicy` | `max_retries` · `backoff` · `timeout` | |

---

#### `memory.py` — 记忆包
| 类型 | 字段 |
|------|------|
| `MemoryPacket` | `task_id` · `kind` · `summary` · `working` · `episodic` · `compression` · `recent` |

`kind` 取值：`decision` · `digest` · `observation` · ...

---

#### `graph.py` — 动态异构图
| 类型 | 字段 |
|------|------|
| `NodeKind` (Enum) | `agent` · `task` · `memory` · `tool` |
| `GraphNode` | `node_id` · `kind` · `capabilities` · `status` · `success_rate` · `latency` |
| `Graph` | `nodes` (dict) · `edges` (list) · `add_node()` · `add_edge()` |
| `GraphEdge` | `src` · `dst` · `relation` · `weight` |
| `GraphDiff` | `added_nodes` · `removed_nodes` · `added_edges` · `removed_edges` · `updated_edges` |

---

#### `tool.py` — 工具调用
| 类型 | 字段 |
|------|------|
| `ToolCall` | `tool_id` · `name` · `args` |
| `ToolResult` | `tool_id` · `output` · `error` · `success` |
| `ToolSpec` | `name` · `description` · `parameters` |

---

#### `heartbeat.py` — 心跳
| 类型 | 字段 |
|------|------|
| `Heartbeat` | `agent_id` · `status` · `timestamp` · `load` |

---

#### `sync.py` — 端边云同步
| 类型 | 字段 |
|------|------|
| `SyncStatus` (Enum) | `pending` · `in_flight` · `applied` · `conflict` · `failed` |
| `SyncOp` | `op_id` · `source` · `target` · `payload` · `status` |

---

#### `cyber.py` — 攻防协议类型（8 个 dataclass）

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

### 测试覆盖

| 文件 | 测试数 | 覆盖内容 |
|------|--------|---------|
| [`tests/protocol/test_cyber.py`](../tests/protocol/test_cyber.py) | 6 | 8 个攻防类型字段验证 + AttackChain 序列化/反序列化 |

---

### 未实现 / 待补

- `ThreatIntel` 仅有基础结构，缺 ATT&CK 技战术编号映射
- `Task.payload` 已正式纳入协议，并贯通后端请求、持久化和运行时
- `protocol/` 核心类型已迁移为 Pydantic `BaseModel`；当前待补为 `Task.payload` 正式契约化
