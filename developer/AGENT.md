# Developer 开发规范层 — AGENT.md

> 本文件是 `developer/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
整个仓库的最高规范层（Developer Operating System）：架构、路线图、协议、编码规范、各指南。是项目的大脑。下辖 `developer/roadmap/`（系统级开发计划 P0..P7）。

## 读取目录（允许读）
- developer/specs/
- developer/roadmap/
- protocol/

## 禁止修改目录
- 所有业务子系统源码实现（仅维护规范文档）
- frontend/
- backend/

## 输出
- developer/*.md 规范文档
- developer/roadmap/ 阶段计划

## 依赖
- protocol/ 契约
- developer/roadmap/ 阶段

## 接口
read(spec) -> Guideline；所有 Agent 开发前第一步读取本目录。

## 测试方式
`pytest tests/developer/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/developer/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/developer/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/developer.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 下辖子模块
- `developer/specs/` 编号规范 SSOT（`00`–`13`）
- `developer/roadmap/` 系统级开发计划：`README.md`（总览）+ `P0..P7/`（各阶段目标/输入/输出/接口/测试/风险/完成标准）
