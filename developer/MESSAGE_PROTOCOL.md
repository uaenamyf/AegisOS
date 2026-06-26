# MESSAGE_PROTOCOL.md — 通信协议规范

> AegisOS 不直接使用裸 JSON，而是自研分层协议。本文件是 `protocol/` 的规范来源。

## 1. 设计目标
- 强类型、可演进、可校验
- 低熵稀疏通信：按需链式，非广播
- 支持动态异构路由与端边云同步

## 2. Message 信封（分层结构）
```
Header
  -> Session
  -> Task
  -> Node
  -> Route
  -> Payload
  -> Metadata
  -> Signature
```

### Message 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| message_id | str | 全局唯一 |
| parent_id | str? | 关联父消息 |
| task_id | str? | 关联任务 |
| workflow_id | str? | 关联工作流 |
| sender | NodeRef | 发送节点 |
| receiver | NodeRef | 接收节点 |
| priority | int | 优先级 |
| ttl | int | 存活时间/跳数 |
| compression | str? | 压缩算法 |
| timestamp | float | 时间戳 |
| payload | Payload | 强类型载荷 |

## 3. Task
| 字段 | 说明 |
|------|------|
| goal | 目标 |
| plan | 计划 (DAG) |
| status | 状态 |
| retry | 重试策略 |
| rollback | 回滚策略 |
| dependency | 依赖 |

## 4. MemoryPacket
| 字段 | 说明 |
|------|------|
| working | 工作记忆 |
| semantic | 语义记忆 |
| episodic | 情景记忆 |
| archive | 归档 |
| embedding | 向量嵌入 |
| summary | 摘要 |
| compression | 压缩信息 |

## 5. Event 类型
- AgentStart / AgentFinish
- ToolCall / ToolFinish
- Retry / Rollback
- MemoryUpdate / GraphUpdate

## 6. Heartbeat
| 字段 | 说明 |
|------|------|
| Node | 节点标识 |
| CPU / GPU | 资源占用 |
| Latency | 延迟 |
| Memory | 内存 |
| Token | Token 用量 |
| Status | 健康状态 |

## 7. 动态路由协议（比赛亮点）
流程：
```
Task -> Semantic Graph -> Agent Graph -> Dynamic Routing
  -> Sparse Communication -> Adaptive Graph -> Graph Update
```
Router 维护节点与边属性：
Agent Node / Task Node / Memory Node / Tool Node / Edge / Weight / Entropy / Latency / Trust Score / Success Rate

动态计算链路（非全广播）：
```
AgentA -> Planner -> Memory -> Coder -> Reviewer -> Executor
```
对齐赛题：Dynamic Heterogeneous Topology + Low Entropy Communication。

## 8. Agent 生命周期与接口
生命周期：
```
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task
  -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result
  -> Log -> Heartbeat -> Finish
```
统一接口：`receive()` -> `think()` -> `tool()` -> `reflect()` -> `respond()`

## 9. 序列化与兼容
- 默认 JSON + schema 校验；可选 MessagePack/protobuf 用于高性能通道。
- 字段新增必须可选；字段废弃先标记 deprecated。
- 所有数据类定义在 `protocol/*.py`，禁止业务层自造并行结构。
