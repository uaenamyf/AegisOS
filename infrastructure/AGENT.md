# Infrastructure 基础设施层（域根） — AGENT.md

> 本文件是 `infrastructure/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
基础设施层：节点间通信、端边云协同、部署交付。按传输-节点-交付三子层组织。

## 内部分层
| 分类 | 说明 |
|------|------|
| infrastructure/transport/ | 传输（通信通道与编解码，低熵稀疏通信） |
| infrastructure/nodes/ | 节点（端侧 + 云侧，端边云协同） |
| infrastructure/delivery/ | 交付（Docker/K8s/CI/CD 部署） |

## 读取目录（允许读）
- protocol/
- agents/planning/engine/
- tooling/configs/
- developer/DEPLOY_GUIDE.md

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- agents/ 业务逻辑

## 输出
- infrastructure/transport/communication/ 通信
- infrastructure/nodes/edge/ 端侧
- infrastructure/nodes/cloud/ 云侧
- infrastructure/delivery/deployment/ 部署

## 依赖
- agents/planning/engine/ 拓扑/事件
- protocol/ Message/Sync

## 接口
端边云协同与部署；详见各子模块 AGENT.md。

## 测试方式
`pytest tests/infrastructure/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/infrastructure/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/infrastructure.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。

## 下辖子模块（传输-节点-交付 + 公共 API）
- **infrastructure/api/** 公共接口层：其他模块通过 `from infrastructure.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- **传输 infrastructure/transport/**：`communication/` 低熵稀疏通信（通道/传输/编解码）
- **节点 infrastructure/nodes/**：`edge/` 端侧节点（本地推理/断连续传）、`cloud/` 云侧节点（全局编排/注册发现）
- **交付 infrastructure/delivery/**：`deployment/` Docker/K8s/CI/CD 部署
