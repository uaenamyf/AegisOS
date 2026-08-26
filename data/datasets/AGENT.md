# Data/Datasets 数据集 — AGENT.md

> 本文件是 `data/datasets/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
数据集加载与预处理：统一加载器、采样、切分、版本。

## 读取目录（允许读）
- protocol/
- tooling/configs/
- developer/

## 禁止修改目录
- frontend/
- protocol/ 类型定义
- 业务子系统逻辑

## 输出
- data/datasets/loaders/
- data/datasets/preprocess/
- data/datasets/samples/

## 依赖
- protocol/ Payload

## 接口
load(name) -> Dataset；版本化数据集。

## 测试方式
`pytest tests/data/datasets/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/data/datasets/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/datasets/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/datasets.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/06_SCHEMA_SPEC.md
- **API 边界**：data/api/ — from data.api import ...
- **数据契约**：protocol/memory.py（MemoryPacket）/ protocol/graph.py
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H2 Neo4j/Qdrant）
