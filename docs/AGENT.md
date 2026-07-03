# Docs 文档资产层（域根） — AGENT.md

> 本文件是 `docs/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
项目文档资产层：用户文档、架构说明、指南、图表资产，以及可运行示例与教程（docs/examples/）。以 `developer/` 为单一可信源。

## 读取目录（允许读）
- `developer/`
- `protocol/`
- `tooling/configs/`

## 禁止修改目录
- 所有源码实现逻辑（以 developer/ 规范为准）

## 输出
- `docs/api/`、`docs/architecture/`、`docs/guides/`、`docs/assets/`
- `docs/examples/` 可运行示例、Demo、教程、Notebook

## 依赖
- `developer/` 规范
- `protocol/` 契约

## 接口
`render(docs)`；`run_example(name)`；以 developer/ 为单一可信源。

## 测试方式
`pytest tests/docs/`；示例通过 `run_example(name)` 验证可运行性，覆盖率目标 >= 80%。

## 日志位置
`logs/docs/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/docs/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/docs.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/02_DIRECTORY_SPEC.md

## 下辖子模块
- `docs/api/`、`docs/architecture/`、`docs/guides/`、`docs/assets/` 文档内容
- `docs/examples/` 可运行示例、Demo、教程、Notebook（原顶层 examples/ 并入）
