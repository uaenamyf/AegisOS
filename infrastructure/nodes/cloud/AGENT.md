# Infra/Cloud 云侧 — AGENT.md

> 本文件是 `infrastructure/nodes/cloud/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
云侧服务、注册中心与部署：全局编排、模型服务、注册发现。

## 读取目录（允许读）
- protocol/
- infrastructure/transport/communication/
- infrastructure/delivery/deployment/
- tooling/configs/
- developer/

## 禁止修改目录
- infrastructure/nodes/edge/ 端侧实现
- frontend/
- protocol/ 类型定义

## 输出
- infrastructure/nodes/cloud/services/
- infrastructure/nodes/cloud/deploy/
- infrastructure/nodes/cloud/registry/

## 依赖
- infrastructure/delivery/deployment/ 部署
- protocol/ Sync

## 接口
register/discover/orchestrate；云侧全局视图。

## 测试方式
`pytest tests/infrastructure/nodes/cloud/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/nodes/cloud/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/cloud/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/cloud.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 12_TECH_STACK_SPEC.md
- **API 边界**：infrastructure/api/ — from infrastructure.api import ...
- **数据契约**：protocol/message.py / protocol/sync.py
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）
