# Observability 可观测与评估层（域根） — AGENT.md

> 本文件是 `observability/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
可观测与评估层：监控、回放、基准、评估、可视化，横切关注系统质量。按观测-度量-呈现三子层组织。

## 内部分层
| 分类 | 说明 |
|------|------|
| observability/inspect/ | 观测（监控指标 + 确定性回放） |
| observability/measure/ | 度量（基准测试 + 评估评分） |
| observability/present/ | 呈现（可视化渲染） |

## 读取目录（允许读）
- protocol/
- aegisos_agents/planning/engine/
- aegisos_agents/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 被测业务实现逻辑

## 输出
- observability/inspect/monitor/ 监控
- observability/inspect/replay/ 回放
- observability/measure/benchmark/ 基准
- observability/measure/evaluation/ 评估
- observability/present/visualization/ 可视化

## 依赖
- aegisos_agents/planning/engine/eventbus/ 事件
- protocol/ Heartbeat/Event

## 接口
collect/evaluate/replay；对齐赛题评分维度。

## 测试方式
`pytest tests/observability/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/observability/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/observability/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/observability.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 07_EVENT_SPEC.md
- **API 边界**：observability/api/ — from observability.api import ...
- **数据契约**：protocol/event.py（Event）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H5 评测/回放）

## 下辖子模块（观测-度量-呈现 + 公共 API）
- **observability/api/** 公共接口层：其他模块通过 `from observability.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **观测 observability/inspect/**：`monitor/` 指标/tracing/告警、`replay/` 确定性回放
- **度量 observability/measure/**：`benchmark/` 基准测试、`evaluation/` 评估评分
- **呈现 observability/present/**：`visualization/` 图表/图谱/面板渲染

---

## 📋 模块实现详解

> 原 `observability/MODULE.md` 内容，已合并至此。

### 目录结构

```
observability/
├── api/
│   └── __init__.py        ✅ 6 个 Protocol 接口定义
├── inspect/
│   ├── monitor/           🔲 仅 AGENT.md
│   └── replay/            🔲 仅 AGENT.md
├── measure/
│   ├── benchmark/         🔲 仅 AGENT.md
│   └── evaluation/        🔲 仅 AGENT.md
└── present/
    └── visualization/     🔲 仅 AGENT.md
```

### 已实现

#### `api/__init__.py` — 6 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `MonitorAPI` | `health()` · `metrics()` · `agents_status()` | 系统监控 |
| `TraceAPI` | `trace(task_id)` · `spans(task_id)` | 链路追踪 |
| `ReplayAPI` | `replay(session_id)` · `timeline(session_id)` | 时序回放 |
| `BenchmarkAPI` | `run(spec)` · `result(benchmark_id)` | 性能基准 |
| `EvaluationAPI` | `evaluate(spec)` · `report(evaluation_id)` | 质量评测 |
| `VisualizationAPI` | `render(graph)` · `export(format)` | 可视化导出 |

### 未实现（全空，仅 AGENT.md）

#### `inspect/` — 观测层

| 子模块 | 计划功能 |
|--------|---------|
| `monitor/` | 实时监控面板：Agent 状态 · 资源使用 · 事件流 |
| `replay/` | 时序回放：按时间轴重放 Agent 决策与通信 |

#### `measure/` — 度量层

| 子模块 | 计划功能 |
|--------|---------|
| `benchmark/` | 性能基准：延迟 · 吞吐量 · 资源开销 |
| `evaluation/` | 5 维度评测：准确率 · 覆盖率 · 响应时间 · 资源效率 · 协同质量 |

#### `present/` — 呈现层

| 子模块 | 计划功能 |
|--------|---------|
| `visualization/` | 可视化：拓扑图渲染 · 攻击链 DAG · 事件时间线 |

### 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H5 | Benchmark + 5 维度评测体系 | 🔲 未开始 |
| — | 回放系统（赛事演示用） | 🔲 未开始 |
