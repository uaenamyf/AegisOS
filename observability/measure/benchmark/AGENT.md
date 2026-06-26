# Obs/Benchmark 基准 — AGENT.md

> 本文件是 `observability/measure/benchmark/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
基准测试套件与用例：性能、质量、通信熵等多维基准。

## 读取目录（允许读）
- protocol/
- observability/measure/evaluation/
- data/datasets/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 生产业务逻辑

## 输出
- observability/measure/benchmark/suites/
- observability/measure/benchmark/runners/
- observability/measure/benchmark/cases/
- observability/measure/benchmark/results/

## 依赖
- observability/measure/evaluation/ 指标
- data/datasets/ 数据

## 接口
run(suite) -> BenchmarkReport；可复现基准。

## 测试方式
`pytest tests/observability/measure/benchmark/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/observability/measure/benchmark/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/benchmark/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/benchmark.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
