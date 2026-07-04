# observability/ 模块实现文档

> 可观测层 — inspect(监控·回放) · measure(基准·评测) · present(可视化)。

📁 模块规范：[`AGENT.md`](AGENT.md) · 架构规范：[`01_ARCHITECTURE_SPEC.md`](../developer/specs/01_ARCHITECTURE_SPEC.md)

---

## 目录结构

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

---

## 已实现

### `api/__init__.py` — 6 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `MonitorAPI` | `health()` · `metrics()` · `agents_status()` | 系统监控 |
| `TraceAPI` | `trace(task_id)` · `spans(task_id)` | 链路追踪 |
| `ReplayAPI` | `replay(session_id)` · `timeline(session_id)` | 时序回放 |
| `BenchmarkAPI` | `run(spec)` · `result(benchmark_id)` | 性能基准 |
| `EvaluationAPI` | `evaluate(spec)` · `report(evaluation_id)` | 质量评测 |
| `VisualizationAPI` | `render(graph)` · `export(format)` | 可视化导出 |

---

## 未实现（全空，仅 AGENT.md）

### `inspect/` — 观测层

| 子模块 | 计划功能 |
|--------|---------|
| `monitor/` | 实时监控面板：Agent 状态 · 资源使用 · 事件流 |
| `replay/` | 时序回放：按时间轴重放 Agent 决策与通信 |

### `measure/` — 度量层

| 子模块 | 计划功能 |
|--------|---------|
| `benchmark/` | 性能基准：延迟 · 吞吐量 · 资源开销 |
| `evaluation/` | 5 维度评测：准确率 · 覆盖率 · 响应时间 · 资源效率 · 协同质量 |

### `present/` — 呈现层

| 子模块 | 计划功能 |
|--------|---------|
| `visualization/` | 可视化：拓扑图渲染 · 攻击链 DAG · 事件时间线 |

---

## 赛事需求（来自 plans/14 · 15）

| 任务 | 说明 | 状态 |
|------|------|------|
| H5 | Benchmark + 5 维度评测体系 | 🔲 未开始 |
| — | 回放系统（赛事演示用） | 🔲 未开始 |
