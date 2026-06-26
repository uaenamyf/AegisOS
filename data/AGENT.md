# Data 数据层（域根） — AGENT.md

> 本文件是 `data/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
数据层：数据集与数据模型/Schema。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子系统逻辑

## 输出
- data/datasets/ 数据集
- data/models/ 数据模型

## 依赖
- protocol/ 复用基础类型

## 接口
load/register；单一可信数据源。

## 测试方式
`pytest tests/data/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/data/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/data/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/data.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/PYTHON_STYLE.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/API_SPEC.md` 与 `developer/EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。

## 下辖子模块
- **data/api/** 公共接口层：其他模块通过 `from data.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- `data/datasets/` 数据集加载/预处理/版本
- `data/models/` 数据模型/Schema 注册/迁移
