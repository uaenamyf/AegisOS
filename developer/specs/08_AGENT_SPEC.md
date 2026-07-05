# 08_AGENT_SPEC.md — 智能体规范（Agent Runtime）

> 上游：`00_PROJECT_SPEC.md`、`04_PROTOCOL_SPEC.md`、`05_API_SPEC.md`。本文件定义 Agent Runtime（`aegisos_agents/tools/runtime/`）。
> Agent 数据契约：`protocol/agent.py`（`Agent`/`AgentStatus`）。Agent 角色：planner · orchestrator · coder · executor · tester · debugger · critic · reviewer · researcher · docwriter。

---

## 1. Agent 生命周期

```
Initialize → Load Config → Load Prompt → Load Skills → Receive Task
→ Reasoning → Memory Read → Tool Call → Reflection → Return Result
→ Log → Heartbeat → Finish
```

| 阶段 | 动作 | 产物 |
|------|------|------|
| Initialize | 创建 Agent 实例，注册到 `AgentRegistryAPI` | `Agent(status=Idle)` |
| Load Config | 从 `tooling/configs/agents/*.yaml` 读取配置 | config |
| Load Prompt | 从 `aegisos_agents/tools/prompts/roles/` 加载角色模板 | prompt |
| Load Skills | 加载能力声明（`Agent.capabilities`） | skills |
| Receive Task | `receive(task)` 接收并校验 Task | `Agent(status=Running)` + `AgentStart` 事件 |
| Reasoning | `think()` 推理（CoT/ToT/ReAct） | 推理结果 |
| Memory Read | 读 `MemoryAPI.read(query)` | `MemoryPacket` |
| Tool Call | `tool()` 调用工具（`ExecutionAPI`） | `ToolCall`→`ToolResult` + `ToolCall`/`ToolFinish` 事件 |
| Reflection | `reflect()` 自评（`aegisos_agents/perception/reflection/`） | 反思评分 → 写 `memory/reflection` |
| Return Result | `respond()` 返回结构化结果 | result + `AgentFinish` 事件 |
| Log | 写日志（脱敏） | log |
| Heartbeat | 周期发 `Heartbeat` | `Agent(status=Idle/Waiting)` |
| Finish | 释放资源，转 Idle/Offline | `Agent(status=Idle)` |

状态机：`Idle → Running → (Waiting → Running)* → Idle | Failed | Offline`（`AgentStatus`）。

---

## 2. Agent API（统一接口）

每个角色 Agent 须实现统一接口（由 `aegisos_agents/api/RuntimeAPI` 托管）：

| 方法 | 签名 | 说明 |
|------|------|------|
| `receive` | `receive(task: Task) -> None` | 接收并校验任务 |
| `think` | `think() -> dict` | 推理与计划 |
| `tool` | `tool() -> ToolResult` | 调用工具执行 |
| `reflect` | `reflect() -> dict` | 反思与自评 |
| `respond` | `respond() -> dict` | 返回结构化结果 |

公共 API（`aegisos_agents.api`，仅暴露外部域需要调用的 5 个接口）：
- `AgentRegistryAPI`：register/get/list_agents（**不含 invoke**，执行统一走 RuntimeAPI）
- `RuntimeAPI`：run/stop/heartbeat（**核心入口**：后端调 run 触发执行）
- `MemoryAPI`：read/write/retrieve
- `ExecutionAPI`：execute（直接工具调用）
- `EventBusAPI`：publish/subscribe

> **规划与感知已内聚**：`PlanningAPI`（plan/route/schedule）和 `PerceptionAPI`（reason/reflect）是 aegisos_agents 域内部能力，不对外暴露。后端只调 `RuntimeAPI.run(task)`，agents 域内部自行编排 plan→route→schedule→execute→reflect。

---

## 3. Agent Prompt（提示词）

- 位置：`aegisos_agents/tools/prompts/`（模板库 + 版本管理 + `roles/` 各角色模板）。
- 版本化：每个 prompt 有版本号；变更走 `tooling/configs/prompts/` 登记。
- 注入：由 Runtime 在 `Load Prompt` 阶段注入 `ContextSchema`（含 history/skills/tools）。
- 规范详见本文件 §3（原 `PROMPT_GUIDE.md` 已并入）。
- 禁止在 prompt 中硬编码密钥或敏感数据。

---

## 4. Agent Memory（记忆）

- 接口：`MemoryAPI`（read/write/retrieve）。
- 写入流：`data → compression → split(working/semantic/episodic/archive) → vector → reflection → cache → sync`。
- 读取流：`query → retrieval(vector+keyword+graph) → rerank → MemoryPacket`。
- 反思结果写入 `aegisos_agents/memory/reflection/`（区别于 `aegisos_agents/perception/reflection/` 评估）。
- 幂等写入（packet id 去重）；checkpoint/snapshot 恢复。

---

## 5. Agent Tool（工具）

- 调用：`tool()` → `ExecutionAPI.run(task)` → `aegisos_agents/action/execution/executor/` 沙箱执行。
- 声明：工具以 `ToolSpec`（args_schema/output_schema/permission/resource_limit）注册于 `aegisos_agents/action/execution/tools/`。
- 权限：每角色 Agent 有工具白名单；危险操作须显式 `permission`；资源受 `resource_limit` 约束。
- 事件：每次调用发 `ToolCall`/`ToolFinish` 事件。
- 详见本文件 §5（原 `TOOL_SPEC.md` 已并入）。

---

## 6. Agent Reflection（反思）

- 位置：`aegisos_agents/perception/reflection/`（评估），结果存 `aegisos_agents/memory/reflection/`（记忆）。
- 流程：`respond()` 后 `reflect()` 自评 → 评分（质量/成本/合规）→ 写记忆 → 更新 `Agent.success_rate`/`trust_score`。
- 反思驱动 `GraphUpdate`（信任度变化触发拓扑自适应）。

---

## 7. Agent Skill（技能）

- 声明：`Agent.capabilities`（list[str]）。
- 注册：Agent 在 Initialize 时声明能力；Router 据能力+信任度+延迟做低熵路由。
- 扩展：新增技能 = 新增角色 Agent 或扩展现有角色 capabilities + 补 `AGENT.md`。

---

## 8. Agent Context（上下文）

- 由 `aegisos_agents/perception/context/` 管理：Token 预算、裁剪、会话隔离。
- 数据结构：`ContextSchema`（见 `06_SCHEMA_SPEC.md` §10）：token_budget/used、history、working_memory、skills、tools、trace_id。
- 注入：Runtime 在 `Receive Task` 后注入 Context；超预算时裁剪 history。

---

## 9. Agent Config（配置）

- 位置：`tooling/configs/agents/*.yaml`（角色配置：模型、温度、工具白名单、资源限制、重试策略）。
- 加载：`Load Config` 阶段读取；运行时只读。
- 密钥走环境变量，不入配置文件。

---

## 10. Agent Logger（日志）

- 位置：按模块 `AGENT.md` 的「日志位置」字段（通常 `logs/{domain}/{module}/`）。
- 内容：生命周期各阶段、ToolCall/Result、Memory 读写、错误。
- 脱敏：不记录密钥/敏感载荷。
- 关联：每条日志带 `trace_id`/`session_id`/`task_id`/`agent_id`。
- 事件：关键阶段同步发 Event（AgentStart/Finish/ToolCall/...）供 observability。

---

## 11. Agent Metrics（指标）

- 由 `observability/measure/` 采集，经 `MonitorAPI` 暴露。
| 指标 | 说明 |
|------|------|
| `agent.success_rate` | 成功率（`Agent.success_rate`） |
| `agent.trust_score` | 信任度（`Agent.trust_score`） |
| `agent.latency` | 端到端延迟 |
| `agent.token_used` | Token 用量（`Heartbeat.token`） |
| `tool.call_count` / `tool.error_rate` | 工具调用/错误率 |
| `task.retry_count` / `task.rollback_count` | 重试/回滚次数 |
| `route.entropy` | 通信熵（`Route.entropy`） |

- 评估对齐赛题评分（`observability/measure/evaluation/`）。

---

## 12. 角色 Agent 清单

| 角色 | 目录 | 职责 |
|------|------|------|
| planner | `aegisos_agents/planning/planner/` | 目标分解为 DAG |
| orchestrator | `aegisos_agents/planning/orchestrator/` | 多 Agent 协作编排 |
| coder | `aegisos_agents/action/coder/` | 编写代码 |
| executor（角色） | `aegisos_agents/action/executor/` | 执行任务 |
| tester | `aegisos_agents/action/tester/` | 测试 |
| debugger | `aegisos_agents/action/debugger/` | 调试 |
| critic | `aegisos_agents/action/critic/` | 批判 |
| reviewer | `aegisos_agents/action/reviewer/` | 评审 |
| researcher | `aegisos_agents/action/researcher/` | 研究 |
| docwriter | `aegisos_agents/action/docwriter/` | 文档 |

> 注意：`aegisos_agents/action/executor/`（角色）≠ `aegisos_agents/action/execution/executor/`（沙箱执行器）。
