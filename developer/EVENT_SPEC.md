# EVENT_SPEC.md — 事件规范

> 事件总线（agents/planning/engine/eventbus/）的事件类型、topic、顺序与可靠性约定。

## 1. 事件类型
| 事件 | 触发 | 载荷 |
|------|------|------|
| AgentStart | Agent 开始执行 | agent_id, task_id |
| AgentFinish | Agent 完成 | agent_id, task_id, result |
| ToolCall | 工具调用 | tool_name, args |
| ToolFinish | 工具完成 | tool_name, result |
| Retry | 重试 | task_id, attempt |
| Rollback | 回滚 | task_id, reason |
| MemoryUpdate | 记忆变更 | memory_packet |
| GraphUpdate | 拓扑图变更 | graph_diff |

## 2. Topic 命名
`{domain}.{type}`，例如 `agent.start`、`tool.call`、`memory.update`、`graph.update`。

## 3. 顺序与可靠性
- 同 task_id 内事件保序（partition by task_id）。
- 至少一次投递；消费者幂等（基于 event_id 去重）。
- 死信队列：处理失败 N 次后进入 DLQ，告警。

## 4. 事件信封
复用 `protocol/event.py` 的 Event 数据类，封装于 Message 信封投递。

## 5. 订阅约束
- 订阅者不得在事件处理中同步阻塞超过阈值；重活下沉到对应子系统。
- 新增事件类型需在本文件登记并更新 CHANGELOG。
