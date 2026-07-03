# Tests 测试 — AGENT.md

> 本文件是 `tests/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
单元/集成/端到端测试与 fixtures：保障各模块质量与回归。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/specs/09_DEVELOPMENT_SPEC.md

## 禁止修改目录
- 被测源码实现逻辑（仅写测试）
- frontend/

## 输出
- tests/unit/
- tests/integration/
- tests/e2e/
- tests/fixtures/
- tests/benchmarks/

## 依赖
- protocol/ 契约
- tooling/configs/

## 接口
pytest tests/；镜像分层结构 tests/{domain}/{module}/；详见 developer/specs/09_DEVELOPMENT_SPEC.md。

## 测试方式
`pytest tests/tests/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/tests/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/tests/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/tests.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/09_DEVELOPMENT_SPEC.md
