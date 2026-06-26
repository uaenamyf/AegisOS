# ARCHITECTURE.md — AegisOS 系统总体架构

> 本文件是 AegisOS 的总体架构规范，是项目大脑的一部分。所有 Agent 开发前必读。

## 1. 项目定位
AegisOS = **Agent Operating System (AOS) + AI Native IDE**。目标：挑战杯揭榜挂帅 + 荣耀群体智能赛题。不是单个 Agent，而是让整个项目可由 Agent 自主开发与运行的系统。

核心评分对齐：
- 动态异构群体智能（Dynamic Heterogeneous Topology）
- 长期记忆（Long-term Memory）
- 低熵通信（Low Entropy Communication）
- 端边云协同（Edge-Cloud Collaboration）
- 可运行系统（Runnable System）

## 2. 分层架构（同域聚合 + 域内分类）
```
┌──────────────────────────────────────────────────┐
│  frontend/  表现层（Controller-Service-Mapper + Views）│
│   controllers │ services │ mappers │ views         │
│    (canvas/graph/monitor/replay)                  │
├──────────────────────────────────────────────────┤
│  backend/  应用层（Controller-Service-Mapper + Gateway）│
│   gateway -> controllers -> services -> mappers   │
├──────────────────────────────────────────────────┤
│  agents/  智能体域（认知架构：感知-规划-行动-记忆-工具）│
│   ┌────────────────────────────────────────────┐ │
│   │ agents/perception/  感知                    │ │
│   │  context │ reasoning │ reflection          │ │
│   ├────────────────────────────────────────────┤ │
│   │ agents/planning/  规划                      │ │
│   │  planner │ orchestrator │ engine/          │ │
│   │   (planner│scheduler│router│workflow       │ │
│   │    eventbus│topology)                      │ │
│   ├────────────────────────────────────────────┤ │
│   │ agents/action/  行动                       │ │
│   │  {coder,executor,tester,debugger,critic,   │ │
│   │   reviewer,researcher,docwriter}           │ │
│   │  + execution/ (executor│tools)             │ │
│   ├────────────────────────────────────────────┤ │
│   │ agents/memory/  记忆（12 子模块，含知识库）   │ │
│   ├────────────────────────────────────────────┤ │
│   │ agents/tools/  工具                        │ │
│   │  llms │ prompts │ runtime                 │ │
│   └────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│  protocol/  契约层（唯一数据契约）                  │
├──────────────────────────────────────────────────┤
│  infrastructure/  基础设施层（传输-节点-交付）       │
│   transport │ nodes(edge│cloud) │ delivery      │
└──────────────────────────────────────────────────┘
  observability/  可观测与评估（观测-度量-呈现）
   inspect(monitor│replay) │ measure(benchmark│evaluation) │ present(visualization)
  data/ │ tooling/ │ docs/ │ tests/  支撑
  developer/ (含 roadmap/)  规范层（项目大脑，纵切所有层）
```

## 3. 数据流（控制流）
```
User Goal
  -> backend/gateway -> backend/controllers
  -> backend/services -> agents/planning/engine/planner: 分解为 Plan(DAG)
  -> agents/planning/engine/topology: 构建动态异构图
  -> agents/planning/engine/router: 低熵路由选择 Agent 链
  -> agents/planning/engine/scheduler: 调度执行
  -> agents/tools/runtime: 托管 Agent 生命周期
  -> agents/action/{role}: receive->think->tool->reflect->respond
     ├─ agents/memory: 读写 MemoryPacket
     ├─ agents/action/execution/tools + agents/action/execution/executor: 执行工具
     ├─ agents/tools/llms: 推理
     └─ agents/perception/reflection: 自评并写入 agents/memory/reflection
  -> agents/planning/engine/eventbus: 广播事件 (AgentStart/Finish/ToolCall/MemoryUpdate/GraphUpdate)
  -> observability/inspect/monitor + observability/inspect/replay: 观测与记录
  -> observability/measure/evaluation: 评估
  -> frontend: 实时可视化
```

## 4. 子系统职责（简表）
| 子系统 | 职责 | 详见 |
|--------|------|------|
| protocol/ | 全系统唯一数据契约 | MESSAGE_PROTOCOL.md |
| agents/planning/engine/planner/ | 任务分解为 DAG 计划 | agents/planning/engine/planner/AGENT.md |
| agents/planning/engine/scheduler/ | 调度执行单元 | agents/planning/engine/scheduler/AGENT.md |
| agents/planning/engine/router/ | 动态图低熵路由 | ROUTER_GUIDE.md |
| agents/tools/runtime/ | Agent 生命周期托管 | AGENT_GUIDE.md |
| agents/action/execution/executor/ | 沙箱执行工具 | agents/action/execution/executor/AGENT.md |
| agents/planning/engine/workflow/ | DAG 工作流引擎 | agents/planning/engine/workflow/AGENT.md |
| agents/planning/engine/eventbus/ | 发布订阅事件 | EVENT_SPEC.md |
| agents/memory/ | 多层长期记忆（含知识库） | MEMORY_GUIDE.md |
| agents/{roles}/ | 各角色 Agent | AGENT_GUIDE.md |
| agents/planning/engine/topology/ | 动态异构拓扑 | agents/planning/engine/topology/AGENT.md |
| infrastructure/transport/communication/ | 低熵稀疏通信 | MESSAGE_PROTOCOL.md |
| infrastructure/nodes/edge·cloud/ | 端边云协同 | infrastructure/nodes/AGENT.md |
| observability/* | 可观测/回放/评估 | 各 AGENT.md |

## 5. 关键设计原则
1. **契约先行**：protocol/ 是唯一数据契约，所有跨模块通信走 Message 信封。
2. **同域聚合 + 域内分类**：一切与 agent 相关的功能归入 agents/（按认知架构五层：感知-规划-行动-记忆-工具），后端归 backend/（按 Controller-Service-Mapper 三层 + Gateway），前端归 frontend/（按 Controller-Service-Mapper + Views），基础设施/可观测等按职责子分类。
3. **模块间 API 解耦**：每个域通过 `api/` 子包暴露公共接口（Protocol 类型），其他模块只通过 `from {domain}.api import ...` 调用，禁止直接导入内部实现子包。内部可自由重构，只要 api/ 签名不变，依赖方不受影响。
4. **模块边界**：每个模块的 AGENT.md 规定「读取目录/禁止修改目录」，Agent 不得越界。
5. **低熵稀疏通信**：路由按需链式（Agent->Planner->Memory->Coder->Reviewer->Executor），禁止全广播。
6. **长期记忆**：多层记忆 + 压缩 + 反思，跨会话沉淀经验。
7. **动态异构拓扑**：图随任务/能力/信任度自适应更新。
8. **端边云协同**：离线优先，按需同步。
9. **可观测可回放**：事件流驱动确定性回放。
10. **AI 可开发**：developer/ + AGENT.md 体系让 Agent 按规范自主开发而不扫描全项目。

## 6. 非功能性目标
- 单任务端到端延迟、Token 成本、通信熵可度量（observability/measure/evaluation/）。
- 容错：检查点 + 回滚 + 重试（agents/memory/checkpoint、protocol Task.rollback）。
- 扩展：新增 Agent/工具仅需在 agents/、agents/action/execution/tools/ 注册并补 AGENT.md。
