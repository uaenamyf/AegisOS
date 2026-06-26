# Infra/Communication 通信 — AGENT.md

> 本文件是 `infrastructure/transport/communication/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
节点间通信通道与传输/编解码：低熵通信、稀疏消息、压缩与可靠性。

## 读取目录（允许读）
- protocol/
- agents/planning/engine/topology/
- tooling/configs/
- developer/MESSAGE_PROTOCOL.md

## 禁止修改目录
- frontend/
- agents/planning/engine/planner/
- protocol/ 类型定义

## 输出
- infrastructure/transport/communication/channels/
- infrastructure/transport/communication/transport/
- infrastructure/transport/communication/codecs/

## 依赖
- protocol/ Message
- agents/planning/engine/topology/ 路径

## 接口
send/recv(message)；低熵稀疏通信协议。

## 测试方式
`pytest tests/infrastructure/transport/communication/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/transport/communication/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/communication/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/communication.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
