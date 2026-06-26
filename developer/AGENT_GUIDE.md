# AGENT_GUIDE.md — Agent 开发规范

> Agent 实现位于 `agents/`，生命周期由 `agents/tools/runtime/` 托管。每个 Agent 子目录有独立 `AGENT.md`。

## 角色（agents/）
planner / coder / critic / researcher / reviewer / executor / orchestrator / tester / debugger / docwriter

## 统一生命周期
```
Initialize -> Load Config -> Load Prompt -> Load Skills -> Receive Task
  -> Reasoning -> Memory Read -> Tool Call -> Reflection -> Return Result
  -> Log -> Heartbeat -> Finish
```

## 统一接口
- `receive(task)` 接收任务并校验
- `think()` 推理与计划
- `tool()` 调用工具执行
- `reflect()` 反思与自评
- `respond()` 返回结构化结果

## 边界
- Agent 只读其 AGENT.md 声明的目录；禁止修改声明外的目录。
- 通信走 Message 信封；工具调用走 agents/action/execution/tools/ + agents/action/execution/executor/。
- 记忆读写走 agents/memory/ + MemoryPacket。

## 注册与托管
- `agents/registry/` 注册能力；`agents/tools/runtime/` 托管生命周期、注入上下文、心跳。
- 编排由 orchestrator + router + scheduler 协同。

## 反思闭环
- reflect() 结果写入 agents/memory/reflection；反馈更新 router 信任度/成功率。

## 测试
- 每个 Agent 端到端用例（receive->...->respond）+ 边界用例。
