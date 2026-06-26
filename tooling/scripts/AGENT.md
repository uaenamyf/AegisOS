# Tooling/Scripts 脚本 — AGENT.md

> 本文件是 `tooling/scripts/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `tooling/AGENT.md` 与 `developer/ARCHITECTURE.md` 相关章节。

## 职责
构建/测试/部署自动化脚本：环境初始化、一键构建、测试运行、部署，以及文档动态维护脚本（如 gen_readme.py）。隶属 tooling/ 工程支撑层。

## 读取目录（允许读）
- tooling/configs/
- developer/

## 禁止修改目录
- 所有业务子系统源码
- frontend/

## 输出
- tooling/scripts/setup/ 环境初始化
- tooling/scripts/build/ 构建
- tooling/scripts/test/ 测试运行
- tooling/scripts/deploy/ 部署
- tooling/scripts/gen_readme.py README.md 动态生成脚本（扫描仓库实际结构 + api 接口，产出根 README.md）

## 动态维护 README
`gen_readme.py` 扫描仓库实际目录、AGENT.md 数量、api 公共接口、文件统计，自动生成/刷新根 `README.md`。
- **何时运行**：目录结构变动、新增 api 接口、新增 AGENT.md 后，运行 `python3 tooling/scripts/gen_readme.py` 刷新。
- 产出的「实际目录结构」与「仓库统计」段为自动生成，勿手改；其余介绍段为模板。
- 详见 `developer/DEVELOPER_GUIDE.md` 维护流程。

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
