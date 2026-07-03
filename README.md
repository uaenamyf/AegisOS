# AegisOS

> **Agent Operating System (AOS) + AI Native IDE** — 面向「挑战杯揭榜挂帅 + 荣耀群体智能赛题」，方向为**面向超长程网络攻击防御的动态异构群体智能协同推理引擎**，的可由 Agent 自主开发与运行的群体智能系统。

## 核心特性
- **动态异构群体智能**（Dynamic Heterogeneous Topology）
- **长期记忆**（Long-term Memory，含知识库）
- **低熵通信**（Low Entropy Communication，稀疏链式路由）
- **端边云协同**（Edge-Cloud Collaboration）
- **可运行系统**（Runnable System，开箱可部署）
- **AI 可自主开发**（Developer Operating System + 全仓库 AGENT.md 规范体系）

## 架构总览
```
┌──────────────────────────────────────────────────┐
│  frontend/  表现层（Controller-Service-Mapper + Views）│
├──────────────────────────────────────────────────┤
│  backend/   应用层（Controller-Service-Mapper + Gateway）│
├──────────────────────────────────────────────────┤
│  agents/    智能体域（感知-规划-行动-记忆-工具 五层）   │
├──────────────────────────────────────────────────┤
│  protocol/  契约层（唯一数据契约）                    │
├──────────────────────────────────────────────────┤
│  infrastructure/  基础设施层（传输-节点-交付）         │
└──────────────────────────────────────────────────┘
  observability/  可观测与评估（观测-度量-呈现）
  data/  tooling/  docs/  tests/  developer/  支撑与规范
```

## 顶层目录
| 目录 | 角色 | 内部分类 | 公共 API |
|------|------|----------|----------|
| `developer/` | 规范层（项目大脑） | `*.md` + `roadmap/`(P0..P7) | — |
| `protocol/` | 契约层 | 数据类（Message/Event/Task/...） | 本身即全局契约 |
| `frontend/` | 表现层 | src/(controllers · services · mappers · views · protocol) | — |
| `backend/` | 应用层 | src/(controllers · services · mappers · gateway) | `backend/src/api/` |
| `agents/` | 智能体域 | perception · planning · action · memory · tools | `agents/api/` |
| `infrastructure/` | 基础设施层 | transport · nodes · delivery | `infrastructure/api/` |
| `observability/` | 可观测与评估层 | inspect · measure · present | `observability/api/` |
| `data/` | 数据层 | datasets · models | `data/api/` |
| `tooling/` | 工程支撑层 | configs · scripts | `tooling/api/` |
| `docs/` | 文档资产层 | api · architecture · guides · assets · examples | — |
| `tests/` | 测试 | unit · integration · e2e · fixtures · benchmarks | — |

### agents/ — 认知架构五层（感知-规划-行动-记忆-工具）
| 分类 | 内容 |
|------|------|
| `agents/perception/` 感知 | context(上下文) · reasoning(推理) · reflection(反思评估) |
| `agents/planning/` 规划 | planner(角色) · orchestrator(角色) · engine/(planner·scheduler·router·workflow·eventbus·topology) |
| `agents/action/` 行动 | coder·executor·tester·debugger·critic·reviewer·researcher·docwriter(角色) + execution/(executor沙箱·tools) |
| `agents/memory/` 记忆 | 12 子模块（含 semantic 知识库） |
| `agents/tools/` 工具 | llms(模型调用) · prompts(提示词) · runtime(运行时) |

### backend/ — Controller-Service-Mapper + Gateway
`gateway/`(入口) -> `controllers/`(参数校验/响应封装) -> `services/`(业务逻辑) -> `mappers/`(数据转换/持久化)

### frontend/ — Controller-Service-Mapper + Views
`controllers/`(交互/事件) -> `services/`(API/实时/状态) -> `mappers/`(数据转换/共享) -> `views/`(canvas·graph·monitor·replay)

## 模块间 API 解耦
每个域通过 `api/` 子包暴露公共接口，其他模块只通过 `from {domain}.api import ...` 调用，不直接访问内部实现。

| 域 | api 包 | 公共接口数 | 接口 |
|----|--------|-----------|------|
| agents/ | `agents.api` | 5 | AgentRegistryAPI · MemoryAPI · ExecutionAPI · EventBusAPI · RuntimeAPI |
| backend/ | `backend.src.api` | 5 | SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI |
| frontend/ | — (纯 SPA) | — | 纯前端应用，不暴露 Python API |
| infrastructure/ | `infrastructure.api` | 4 | CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI |
| observability/ | `observability.api` | 6 | MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI |
| data/ | `data.api` | 2 | DatasetAPI · ModelSchemaAPI |
| tooling/ | `tooling.api` | 2 | ConfigAPI · ScriptAPI |

> 共 **27** 个公共接口。接口参数/返回值一律使用 `protocol/` 契约类型。`api/` 签名变更属破坏性变更。

## 数据流
```
User Goal
  -> backend/gateway -> backend/controllers -> backend/services
  -> agents/planning/engine/planner: 分解为 Plan(DAG)
  -> agents/planning/engine/topology: 构建动态异构图
  -> agents/planning/engine/router: 低熵路由选择 Agent 链
  -> agents/planning/engine/scheduler: 调度执行
  -> agents/tools/runtime: 托管 Agent 生命周期
  -> agents/action/{role}: receive->think->tool->reflect->respond
     ├─ agents/memory: 读写 MemoryPacket
     ├─ agents/action/execution/(tools+executor): 执行工具
     ├─ agents/tools/llms: 推理
     └─ agents/perception/reflection: 自评并写入 agents/memory/reflection
  -> agents/planning/engine/eventbus: 广播事件
  -> observability/inspect/(monitor+replay): 观测与记录
  -> observability/measure/evaluation: 评估
  -> frontend: 实时可视化
```

## 通信协议
自研分层协议（非裸 JSON）：`protocol/` 定义 Message 信封 + 强类型 Payload。
- Message: message_id/parent_id/task_id/workflow_id/sender/receiver/priority/ttl/timestamp/payload
- Event: AgentStart/AgentFinish/ToolCall/ToolFinish/Retry/Rollback/MemoryUpdate/GraphUpdate
- 动态路由: Task -> Semantic Graph -> Agent Graph -> Dynamic Routing -> Sparse Communication -> Adaptive Graph -> Graph Update

详见 `developer/specs/04_PROTOCOL_SPEC.md`。

## 开发流程（AI 自主开发）
```
Developer Agent
  -> 读取 developer/specs/（00_PROJECT_SPEC 等）+ roadmap/ 定位阶段
  -> 读取目标模块 AGENT.md（职责/边界/接口）
  -> 读取 protocol/ 契约 + tooling/configs/ 配置
  -> 生成代码 -> 运行 tests/ -> 更新文档与 CHANGELOG -> commit
```
Agent 永不扫描整个项目；按模块边界精准读写。

## 快速开始
```bash
make setup        # 初始化环境
make test         # 运行测试
make build        # 构建产物/镜像
make deploy ENV=dev
```

## 实际目录结构（自动生成）
```
agents/
  action/
    coder/
    critic/
    debugger/
    docwriter/
    execution/
    executor/
    researcher/
    reviewer/
    tester/
  api/
  memory/
    archive/
    cache/
    checkpoint/
    compression/
    episodic/
    reflection/
    retrieval/
    semantic/
    snapshot/
    sync/
    vector/
    working/
  perception/
    context/
    reasoning/
    reflection/
  planning/
    engine/
    orchestrator/
    planner/
  tools/
    llms/
    prompts/
    runtime/
backend/
  api/
  controllers/
  gateway/
  mappers/
  services/
data/
  api/
  datasets/
  models/
developer/
  roadmap/
    P0/
    P1/
    P2/
    P3/
    P4/
    P5/
    P6/
    P7/
  specs/
    plans/
docs/
  examples/
frontend/
  api/
  controllers/
    events/
    interaction/
    routes/
  mappers/
    apimappers/
    components/
    store/
    styles/
    utils/
    viewmodels/
  public/
  services/
    api/
    graph/
    realtime/
    session/
  src/
    protocol/
  views/
    agents/
    canvas/
    dashboard/
    graph/
    layout/
    monitor/
    replay/
infrastructure/
  api/
  delivery/
    deployment/
  nodes/
    cloud/
    edge/
  transport/
    communication/
observability/
  api/
  inspect/
    monitor/
    replay/
  measure/
    benchmark/
    evaluation/
  present/
    visualization/
protocol/
tests/
tooling/
  api/
  configs/
  scripts/
```

## 仓库统计（自动生成，2026-07-03）
| 指标 | 数量 |
|------|------|
| 顶层域 | 11 |
| 总目录 | 123 |
| 总文件 | 232 |
| AGENT.md | 78 |
| Python 文件 | 56 |
| Markdown 文件 | 116 |
| 公共 API 接口 | 27 |
| protocol 契约类型 | 26 |

## 关键文档
- `AGENT.md` — 仓库总规范（最高优先级）
- `developer/specs/README.md` — 规范体系索引（SSOT）
- `developer/specs/00_PROJECT_SPEC.md` — 项目 SSOT（目标/边界/生命周期）
- `developer/specs/01_ARCHITECTURE_SPEC.md` — 系统总体架构
- `developer/specs/04_PROTOCOL_SPEC.md` — 通信协议规范
- `developer/specs/02_DIRECTORY_SPEC.md` — 仓库目录导航
- `developer/specs/05_API_SPEC.md` — API 接口规范
- `developer/specs/11_AI_CODING_SPEC.md` — AI 编码规范
- `developer/roadmap/README.md` — 系统级开发计划 P0..P7
- 各目录 `AGENT.md` — 模块边界与开发规范

## 许可
（待定）
