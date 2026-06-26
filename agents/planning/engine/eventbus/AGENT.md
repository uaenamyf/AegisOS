# Engine/EventBus 事件总线 — AGENT.md

> 本文件是 `agents/planning/engine/eventbus/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
发布订阅事件总线：解耦子系统，支持 topic 路由、顺序保证、死信处理。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/EVENT_SPEC.md

## 禁止修改目录
- frontend/
- 业务子系统实现逻辑
- protocol/ 类型定义

## 输出
- agents/planning/engine/eventbus/handlers/
- agents/planning/engine/eventbus/topics/

## 依赖
- protocol/ Event

## 接口
publish(event)/subscribe(topic)；详见 developer/EVENT_SPEC.md。

## 测试方式
`pytest tests/agents/planning/engine/eventbus/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/agents/planning/engine/eventbus/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/eventbus/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/eventbus.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
