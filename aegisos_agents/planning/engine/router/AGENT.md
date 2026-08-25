# Engine/Router 动态图路由 — AGENT.md

> 本文件是 `aegisos_agents/planning/engine/router/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
动态异构拓扑路由：维护 Agent/Task/Memory/Tool 节点与边，计算低熵通信路径，自适应更新图。赛题核心亮点。

## 读取目录（允许读）
- protocol/
- aegisos_agents/planning/engine/topology/
- aegisos_agents/memory/
- aegisos_agents/
- tooling/configs/
- developer/specs/04_PROTOCOL_SPEC.md

## 禁止修改目录
- frontend/
- aegisos_agents/planning/engine/planner/ 规划逻辑
- protocol/ 类型定义

## 输出
- aegisos_agents/planning/engine/router/graph/ 动态图
- aegisos_agents/planning/engine/router/policies/ 路由策略
- aegisos_agents/planning/engine/router/scoring/ 评分

## 依赖
- aegisos_agents/planning/engine/topology/ 拓扑
- aegisos_agents/ 能力注册
- protocol/ Graph/Route

## 接口
route(task) -> Route；动态计算 Agent->Planner->Memory->Coder->Reviewer->Executor 链；详见 developer/specs/04_PROTOCOL_SPEC.md。

## 测试方式
`pytest tests/aegisos_agents/planning/engine/router/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/aegisos_agents/planning/engine/router/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/router/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/router.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md
- **本模块规范补充**：04_PROTOCOL_SPEC.md §16 低熵稀疏路由（赛事核心）
- **API 边界**：aegisos_agents/api/ — from aegisos_agents.api import ...
- **数据契约**：protocol/message.py（Message）/ protocol/scheduler.py（Task）
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）

## 📋 模块实现详解

### 核心函数（router.py）
- `route(message, topology, required_capability) -> list[NodeRef]`：基于 `active_subgraph()` 取在线候选，按 `success_rate - latency` 亲和度打分，降序后截 Top-K=3。
- `TOP_K = 3`：单次最多向 3 个节点分发，绝不广播。

### P3.2 业务接入（2026-08-25）
- `route()` 历史仅在 test 内被引用（业务零调用）— P3.1 静态检测发现该漏洞。
- **修复**：`CyberOrchestrator` 实现 `RouterAPI` Protocol（`select_targets` / `get_topology`），并新增 `assert_target_routable()` 作为防御性守卫。
- `_create_red/blue_agent_executor`（AP3 Goal 模式）执行前调用守卫，目标 Agent 不在 Top-K 则抛 `ValueError`，阻断"绕过路由直接调用"。
- 编排器构造时把 11 个攻防 Agent（红 4 + 蓝 5 + 紫 2）映射为 GraphNode，capability 标签 = agent_name。
- 测试 `tests/aegisos_agents/planning/test_cyber_router_integration.py`（9 用例）覆盖：RouterAPI 签名、Top-K 截取、未知 capability 空返回、11 节点拓扑、已知/未知 target 守卫、红蓝 executor 路由守卫。
- 配套静态守卫 `tooling/scripts/check_no_broadcast.py`（P3.1）持续监控业务域零全广播。
