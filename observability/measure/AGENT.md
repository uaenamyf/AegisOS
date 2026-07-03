# Obs/Measure 度量层 — AGENT.md

> 本文件是 `observability/measure/` 分类的开发规范，隶属 `observability/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
可观测·度量（Measure）

## 职责
基准与评估：性能/质量/通信熵基准测试，任务成功率/群体智能指标评估。

## 读取目录（允许读）
- protocol/
- agents/memory/
- data/datasets/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 生产业务逻辑

## 输出
- observability/measure/benchmark/ 基准
- observability/measure/evaluation/ 评估

## 依赖
- data/datasets/ 数据
- agents/memory/ 反思
- protocol/ Event

## 接口
run(suite) -> BenchmarkReport；evaluate(run) -> Report。

## 测试方式
`pytest tests/observability/measure/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/observability/measure/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/measure/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/measure.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 下辖子模块
- observability/measure/benchmark/ — 基准测试（性能/质量/通信熵多维基准）
- observability/measure/evaluation/ — 评估（任务成功率/通信熵/记忆质量/群体智能指标）
