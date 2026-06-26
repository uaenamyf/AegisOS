# Obs/Inspect 观测层 — AGENT.md

> 本文件是 `observability/inspect/` 分类的开发规范，隶属 `observability/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 分类范式
可观测·观测（Inspect）

## 职责
监控与回放：指标采集、tracing、告警、确定性回放。

## 读取目录（允许读）
- protocol/
- agents/planning/engine/eventbus/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子系统实现逻辑

## 输出
- observability/inspect/monitor/ 监控
- observability/inspect/replay/ 回放

## 依赖
- agents/planning/engine/eventbus/ 事件
- protocol/ Heartbeat/Event

## 接口
collect/alert(metric)；replay(session) -> Timeline。

## 测试方式
`pytest tests/observability/inspect/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/observability/inspect/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/inspect/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/inspect.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。

## 下辖子模块
- observability/inspect/monitor/ — 监控（指标/tracing/告警/面板）
- observability/inspect/replay/ — 回放（事件流确定性回放/时间线/存储）
