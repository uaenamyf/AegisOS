# Tooling 工程支撑层（域根） — AGENT.md

> 本文件是 `tooling/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
工程支撑层：统一管理全项目的配置（configs）与构建/测试/部署脚本（scripts）。为所有模块提供单一配置源与一键化自动化脚本。

## 读取目录（允许读）
- `developer/`（规范，确定配置 schema 与脚本约定）
- `protocol/`（契约，配置中引用的类型）
- `infrastructure/delivery/deployment/`（部署与脚本协同）

## 禁止修改目录
- `frontend/`、`backend/`、`agents/`、`agents/planning/engine/`、`agents/action/execution/`、`infrastructure/`、`observability/`、`data/` 的业务源码
- `protocol/` 类型定义
- `developer/` 规范文档

## 输出
- `tooling/configs/` 环境与各模块配置（environments/agents/models/prompts/各模块 yaml）
- `tooling/scripts/` setup/build/test/deploy 等自动化脚本

## 依赖
- `developer/` 规范
- `infrastructure/delivery/deployment/` 部署目标

## 接口
`load(env) -> Config`；`make setup/build/test/deploy`；详见 `developer/specs/09_DEVELOPMENT_SPEC.md`。

## 测试方式
`pytest tests/tooling/`，校验配置加载与脚本可执行性，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/tooling/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/`（自身即配置源；环境差异通过 `tooling/configs/environments/` 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 下辖子模块
- **tooling/api/** 公共接口层：其他模块通过 `from tooling.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- `tooling/configs/` 配置：环境覆盖、模块配置、Agent/模型/Prompt 配置（单一配置源）
- `tooling/scripts/` 脚本：环境初始化、一键构建、测试运行、部署
