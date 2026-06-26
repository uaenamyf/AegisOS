# Infra/Nodes 节点层 — AGENT.md

> 本文件是 `infrastructure/nodes/` 分类的开发规范，隶属 `infrastructure/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 分类范式
基础设施·节点（Nodes）

## 职责
端边云节点：端侧本地推理、云侧全局编排，断连续传与一致性协商。

## 读取目录（允许读）
- protocol/
- infrastructure/transport/
- agents/tools/runtime/
- tooling/configs/

## 禁止修改目录
- frontend/
- protocol/ 类型定义

## 输出
- infrastructure/nodes/edge/ 端侧
- infrastructure/nodes/cloud/ 云侧

## 依赖
- infrastructure/transport/ 通道
- agents/tools/runtime/ 执行
- protocol/ Sync

## 接口
端边云协同；离线优先，按需上报。

## 测试方式
`pytest tests/infrastructure/nodes/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/nodes/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/nodes/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/nodes.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。

## 下辖子模块
- infrastructure/nodes/edge/ — 端侧节点（本地推理、资源受限调度、断连续传）
- infrastructure/nodes/cloud/ — 云侧节点（全局编排、模型服务、注册发现）
