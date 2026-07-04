# Infra/Edge 边侧 — AGENT.md

> 本文件是 `infrastructure/nodes/edge/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
**边侧节点（Edge）**：区域级推理与数据汇聚。介于端侧（Device）与云侧（Cloud）之间，提供中等算力的本地模型推理、区域告警聚合、流量分析、攻击链分段规划。

### 边侧 vs 端侧 vs 云侧

| 维度 | 端侧 (device/) | 边侧 (edge/) | 云侧 (cloud/) |
|------|---------------|-------------|--------------|
| 物理形态 | PC / 手机 / IoT / 防火墙盒子 | 边缘网关 / 机架服务器 / 区县汇聚节点 | GPU 集群 / 厂家 API |
| 算力 | 极弱（规则引擎/1-3B） | 中等（7-14B 模型，Jetson/L4/RTX 4090） | 强（70B+/GPT-4o/Claude） |
| 延迟 | <100ms | <1s | 1-5s |
| 隐私 | 完全本地 | 区域隔离 | 可脱敏 |
| 攻防场景 | 本地告警分诊、轻量 IDS | 区域威胁聚合、ATT&CK 初筛、流量分析 | 全局攻击链推理、威胁狩猎假设 |

## 读取目录（允许读）
- protocol/
- infrastructure/transport/communication/
- agents/tools/runtime/
- tooling/configs/
- developer/

## 禁止修改目录
- infrastructure/nodes/device/ 端侧实现
- infrastructure/nodes/cloud/ 云侧部署
- frontend/
- protocol/ 类型定义

## 输出
- infrastructure/nodes/edge/runtime/ — 边侧推理运行时（Ollama/vLLM 中型模型）
- infrastructure/nodes/edge/aggregation/ — 区域告警聚合与流量分析
- infrastructure/nodes/edge/sync/ — 端↔边↔云数据同步

## 依赖
- infrastructure/transport/communication/ 通道
- agents/tools/runtime/ 执行
- protocol/ Sync

## 接口
端边云协同；区域级推理 + 数据汇聚，向上对接云侧，向下管理端侧。

## 测试方式
`pytest tests/infrastructure/nodes/edge/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/nodes/edge/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/edge/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/edge.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

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
- **调度算法**：agents/planning/engine/scheduler/ — tier="edge" 对应本层
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）
