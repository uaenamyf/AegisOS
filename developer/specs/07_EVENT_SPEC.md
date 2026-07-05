# 07_EVENT_SPEC.md — 事件总线规范

> 上游：`00_PROJECT_SPEC.md`、`04_PROTOCOL_SPEC.md`。本文件定义 EventBus（`aegisos_agents/planning/engine/eventbus/`）。
> 事件类型定义在 `protocol/event.py`（`EventType` 8 类）。事件封装于 `Message` 信封投递。

---

## 1. 全部 Event（事件清单）

| 事件 | topic | 触发 | Source | Target | Payload | Version |
|------|-------|------|--------|--------|---------|---------|
| `AgentStart` | `agent.start` | Agent 开始执行 | Agent 节点 | EventBus / 订阅者 | `{agent_id, task_id}` | v1 |
| `AgentFinish` | `agent.finish` | Agent 完成 | Agent 节点 | EventBus / 订阅者 | `{agent_id, task_id, result}` | v1 |
| `ToolCall` | `tool.call` | 工具调用 | Agent / Executor | EventBus / 订阅者 | `{tool_name, args, call_id}` | v1 |
| `ToolFinish` | `tool.finish` | 工具完成 | Executor | EventBus / 订阅者 | `{tool_name, call_id, result, ok}` | v1 |
| `Retry` | `task.retry` | 任务重试 | Scheduler | EventBus / 订阅者 | `{task_id, attempt}` | v1 |
| `Rollback` | `task.rollback` | 任务回滚 | Scheduler / Workflow | EventBus / 订阅者 | `{task_id, reason}` | v1 |
| `MemoryUpdate` | `memory.update` | 记忆变更 | Memory 子系统 | EventBus / 订阅者 | `{memory_packet, session_id}` | v1 |
| `GraphUpdate` | `graph.update` | 拓扑图变更 | Router / Topology | EventBus / 订阅者 | `{graph_diff}` | v1 |

---

## 2. Event 生命周期

```
Draft → Proposed（本文件登记 + protocol/event.py 登记）
   → Emitted（生产者实现 publish）
   → Delivered（EventBus 至少一次投递）
   → Consumed（消费者幂等处理，event_id 去重）
   → Acked / DLQ（失败 N 次进死信队列）
   → Stable → Deprecated → Removed
```

- 新增事件须在 `protocol/event.py` 的 `EventType` + 本文件 **双登记** + CHANGELOG。
- 废弃事件先标记 deprecated 一个版本，再移除。

---

## 3. Event 流程（Flow）

```
生产者(Event) → 封装于 Message 信封 → EventBus.publish
   → 按 task_id 分区保序 → 路由到订阅者 topic {domain}.{type}
   → 消费者 handler(event) → 幂等处理(event_id 去重)
   → 成功 Ack / 失败重试 → N 次失败进 DLQ + 告警
   → observability/inspect/(monitor+replay) 记录 → 确定性回放
```

---

## 4. Event Payload（载荷规范）

- Payload 为 `dict`，键名见 §1 各事件 Payload 列。
- 复杂对象（`memory_packet`/`graph_diff`/`result`）须为 `protocol/` 类型序列化结果（`MemoryPacket`/`GraphDiff`/`ToolResult`）。
- 禁止在 Payload 放敏感凭据（脱敏）。

---

## 5. Event Source & Target

- **Source**：`Event.source`（`NodeRef`），标识产生事件的节点（agent/executor/scheduler/router/topology/memory）。
- **Target**：EventBus 路由到订阅 topic 的所有订阅者；无显式单点 target（发布订阅模型）。
- 跨网传输时封装于 `Message`（`sender`=source，`receiver`=EventBus 或订阅者节点）。

---

## 6. Event Version（版本）

- `EventType` 枚举值为稳定 topic 字符串（`agent.start` 等），**不随版本变**。
- Payload 字段新增必须可选；接收方 `extra="ignore"` 忽略未知字段。
- Payload 结构破坏性变更 → 新增事件类型（如 `agent.start.v2`）而非改旧值，旧事件 deprecated。

---

## 7. Event Retry（重试与可靠性）

- **至少一次投递**（at-least-once）。
- **消费者幂等**：基于 `event_id` 去重；处理前检查是否已处理。
- **保序**：同一 `task_id` 内事件按序投递（partition by task_id）。
- **重试**：处理失败按退避重试；超阈值 N 次（默认 5）进**死信队列（DLQ）**并告警。
- **回放**：所有事件持久化供 `observability/inspect/replay/` 确定性回放。

---

## 8. Event Trace（追踪）

- 每个事件携带 `event_id`（唯一）+ 关联 `task_id`。
- 封装于 `Message` 时透传 `header.trace_id`，形成链路追踪。
- `observability/api/TraceAPI.trace(trace_id)` 可查询完整事件链。

---

## 9. 订阅约束

- 订阅者不得在事件处理中**同步阻塞超过阈值**（默认 200ms）；重活下沉到对应子系统异步处理。
- 订阅 handler 异常不应影响 EventBus 投递（失败走重试/DLQ，不抛穿）。
- 订阅/取消订阅经 `EventBusAPI.subscribe`/`unsubscribe`（见 `05_API_SPEC.md` §2.10）。

---

## 10. 与其他模块的协作

| 模块 | 角色 |
|------|------|
| `aegisos_agents/planning/engine/eventbus/` | EventBus 实现 |
| `aegisos_agents/api.EventBusAPI` | 公共接口 |
| `observability/inspect/monitor/` | 订阅事件做监控/告警 |
| `observability/inspect/replay/` | 订阅/读取事件做回放 |
| `observability/measure/evaluation/` | 基于事件做评估评分 |
| `frontend`（经 backend SSE/WS） | 实时可视化事件流 |
