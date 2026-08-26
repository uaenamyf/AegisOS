# Infra/Delivery 交付层 — AGENT.md

> 本文件是 `infrastructure/delivery/` 分类的开发规范，隶属 `infrastructure/` 域。AI 开发本分类下模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 分类范式
基础设施·交付（Delivery）

## 职责
部署交付：Docker 镜像、K8s 编排、CI/CD 流水线、环境管理。

## 读取目录（允许读）
- tooling/configs/
- tooling/scripts/
- infrastructure/nodes/cloud/
- developer/specs/09_DEVELOPMENT_SPEC.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子系统逻辑

## 输出
- infrastructure/delivery/deployment/ 部署

## 依赖
- tooling/configs/ 环境
- infrastructure/nodes/cloud/ 云侧

## 接口
build/deploy(env)；开箱可部署。

## 测试方式
`pytest tests/infrastructure/delivery/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/delivery/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/delivery/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/delivery.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本分类在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 12_TECH_STACK_SPEC.md
- **API 边界**：infrastructure/api/ — from infrastructure.api import ...
- **数据契约**：protocol/message.py / protocol/sync.py
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）

## 下辖子模块
- infrastructure/delivery/deployment/ — Docker/K8s/CI/CD 部署（镜像/编排/流水线/环境管理）
