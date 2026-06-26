# DIRECTORY_GUIDE.md — 仓库目录导航

> AegisOS 采用「同域聚合 + 域内分类 + API 解耦」：每个域通过 `api/` 子包暴露公共接口，其他模块只通过 `from {domain}.api import ...` 调用，不直接访问内部实现。agent 相关归入 agents/（认知架构五层），后端归 backend/（Controller-Service-Mapper），前端归 frontend/（Controller-Service-Mapper + Views），其余各按职责独立成域。

## 顶层分层
| 目录 | 角色 | 内部分类 | 公共 API |
|------|------|----------|----------|
| developer/ | 规范层 | `*.md` + `roadmap/` | — |
| protocol/ | 契约层 | 扁平（数据类） | 本身即全局契约 |
| frontend/ | 表现层 | controllers · services · mappers · views | `frontend/api/` |
| backend/ | 应用层 | controllers · services · mappers · gateway | `backend/api/` |
| agents/ | 智能体域 | perception · planning · action · memory · tools | `agents/api/` |
| infrastructure/ | 基础设施层 | transport · nodes · delivery | `infrastructure/api/` |
| observability/ | 可观测与评估层 | inspect · measure · present | `observability/api/` |
| data/ | 数据层 | datasets · models | `data/api/` |
| tooling/ | 工程支撑层 | configs · scripts | `tooling/api/` |
| docs/ | 文档资产层 | api · architecture · guides · assets · examples | — |
| tests/ | 测试 | unit · integration · e2e · fixtures · benchmarks | — |

> **解耦规则**：每个域的 `api/` 子包是唯一对外入口。其他模块 `from {domain}.api import XxxAPI` 调用，禁止 `from {domain}.internal_pkg import ...`。

## agents/（智能体域 — 感知-规划-行动-记忆-工具）
### agents/perception/ 感知
- `context/` 上下文管理（Token 预算、裁剪、会话隔离）
- `reasoning/` 推理（CoT/ToT/ReAct 链/树/策略）
- `reflection/` 反思评估（批判、反馈评分。注意：区别于 `agents/memory/reflection/` 反思记忆存储）

### agents/planning/ 规划
- `planner/` 规划角色 Agent（目标分解为 DAG）
- `orchestrator/` 编排角色 Agent（多 Agent 协作流程）
- `engine/` 编排引擎：`planner/`(系统级规划) · `scheduler/`(调度) · `router/`(动态图低熵路由) · `workflow/`(DAG工作流) · `eventbus/`(事件总线) · `topology/`(动态异构拓扑)

### agents/action/ 行动
- 角色 Agent：`coder/` · `executor/`(执行角色) · `tester/` · `debugger/` · `critic/` · `reviewer/` · `researcher/` · `docwriter/`
- `execution/` 执行能力：`executor/`(沙箱执行器，区别于角色 `executor/`) · `tools/`(工具注册/包装/规格)

### agents/memory/ 记忆
- 12 子模块：working · episodic · semantic(知识库) · vector · archive · compression · retrieval · reflection(反思记忆) · checkpoint · cache · snapshot · sync

### agents/tools/ 工具
- `llms/` 模型调用（LLM 适配/路由/限流/回退）
- `prompts/` 提示词（模板库/版本管理，含 `roles/` 各角色模板）
- `runtime/` 运行时（生命周期托管、上下文注入、心跳、挂起/恢复）

## backend/（Controller-Service-Mapper + Gateway）
- **backend/controllers/** 控制器：`api/`(REST) · `ws/`(WebSocket) · `sse/`(SSE) · `schemas/`(请求响应 Schema) · `middleware/`(中间件)
- **backend/services/** 服务：`session/`(会话) · `task/`(任务) · `agent/`(Agent 编排) · `memory/`(记忆桥接) · `graph/`(动态图桥接)
- **backend/mappers/** 映射器：`entities/`(DB 实体) · `dto/`(数据传输对象) · `repositories/`(仓储实现) · `converters/`(类型转换器)
- **backend/gateway/** 网关：`routes/` · `auth/` · `middleware/` · `adapters/`(协议适配)

## frontend/（Controller-Service-Mapper + Views）
- **frontend/controllers/** 控制器：`interaction/`(用户交互) · `events/`(后端事件) · `routes/`(前端路由)
- **frontend/services/** 服务：`api/`(API 调用) · `realtime/`(WS/SSE 管理) · `session/`(会话状态) · `graph/`(图数据订阅)
- **frontend/mappers/** 映射器：`viewmodels/`(视图模型) · `apimappers/`(API 映射) · `store/`(全局状态) · `utils/`(工具) · `styles/`(样式) · `assets/`(资产)
- **frontend/views/** 视图：`canvas/`(任务画布) · `graph/`(动态图可视化) · `monitor/`(Agent 监控) · `replay/`(回放时间线)

## infrastructure/（传输-节点-交付）
- `transport/communication/` 低熵稀疏通信
- `nodes/edge/` 端侧 · `nodes/cloud/` 云侧
- `delivery/deployment/` Docker/K8s/CI/CD

## observability/（观测-度量-呈现）
- `inspect/monitor/` 监控/告警 · `inspect/replay/` 确定性回放
- `measure/benchmark/` 基准测试 · `measure/evaluation/` 评估评分
- `present/visualization/` 图表/图谱/面板

## data/
- `datasets/` 数据集加载/预处理/版本
- `models/` 数据模型/Schema 注册/迁移

## tooling/
- `configs/` 配置（environments/agents/models/prompts/各模块 yaml）
- `scripts/` 脚本（setup/build/test/deploy）

## docs/
- `api/` · `architecture/` · `guides/` · `assets/` 文档内容
- `examples/` 可运行示例/Demo/教程/Notebook

## 规范文件位置
- 最高规范：`developer/*.md`
- 阶段计划：`developer/roadmap/P*/README.md`
- 模块边界：各目录 `AGENT.md`（含域根 + 分类 + 叶模块三级）
- 数据契约：`protocol/*.py`
