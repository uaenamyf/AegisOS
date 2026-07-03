# Tooling/Configs 配置 — AGENT.md

> 本文件是 `tooling/configs/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `tooling/AGENT.md` 与 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
全项目配置中心：环境覆盖（dev/staging/prod）、各模块配置、Agent/模型/Prompt 配置。是单一配置源，隶属 tooling/ 工程支撑层。

## 读取目录（允许读）
- developer/
- protocol/

## 禁止修改目录
- 所有业务子系统源码
- frontend/

## 输出
- tooling/configs/environments/
- tooling/configs/agents/
- tooling/configs/models/
- tooling/configs/prompts/

## 依赖
- developer/ 规范

## 接口
load(env) -> Config；单一配置源。

## 测试方式
`pytest tests/tooling/configs/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/configs/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/configs/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/`（自身即配置源；环境差异通过 `tooling/configs/environments/` 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。
