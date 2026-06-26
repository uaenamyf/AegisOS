# Tooling/Scripts 脚本 — AGENT.md

> 本文件是 `tooling/scripts/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `tooling/AGENT.md` 与 `developer/ARCHITECTURE.md` 相关章节。

## 职责
构建/测试/部署自动化脚本：环境初始化、一键构建、测试运行、部署。隶属 tooling/ 工程支撑层。

## 读取目录（允许读）
- tooling/configs/
- developer/

## 禁止修改目录
- 所有业务子系统源码
- frontend/

## 输出
- tooling/scripts/setup/
- tooling/scripts/build/
- tooling/scripts/test/
- tooling/scripts/deploy/

## 依赖
- tooling/configs/

## 接口
make setup/build/test/deploy；详见 developer/DEPLOY_GUIDE.md。

## 测试方式
`pytest tests/tooling/scripts/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/scripts/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/scripts/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/scripts.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
