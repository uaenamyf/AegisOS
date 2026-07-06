# CHANGELOG.md

> 所有变更记录于此。格式：`[阶段] 变更描述`。

## [计划] 2026-07-06 计划优先级调整 — 容器化后移，功能优先

- **调整原因**：用户要求「有关容器化部署的都往后靠，前面先把功能实现完」。
- **P1（短期）新增**：R4 SDK 编排深化（8 项）+ R5 旧接口清理+流式+事件总线（5 项）+ AP1 Plan 范式（不依赖容器化）。
- **P2（中期）新增**：H2 数据层 + H5 可观测评测 + AP3 Goal 范式 + AP4 Ask 范式 + 记忆/感知/工具层补全（全部功能实现，不依赖容器化）。
- **P3（长期）后移**：H1 Docker 沙箱靶场 + AP2 ReAct 范式（依赖 H1）+ H7 部署交付 + 工程支撑（CI/CD、多环境、TLS、生产级 ASGI 等）。
- **更新依赖图**：Plan→P1（独立），Goal→P2（依赖 R4.2），Ask→P2（F/G ✅），ReAct→P3（依赖 H1）。

## [F + G] 2026-07-06 攻防后端端点 + 前端视图（32 测试全通过）

### F1-F2 — 靶场管理 + 拓扑端点
- 新增 `backend/routers/range.py` — `POST /api/v1/range/start`（启动靶场）、`GET /api/v1/range/{range_id}`（查询靶场状态）、`GET /api/v1/range/{range_id}/topology`（获取拓扑图）。
- 使用 `Depends(get_cyber_defense_service)` DI 注入，返回 `RangeStartResponse` / `TopologyResponse` schema。

### F3 — 攻击端点
- 新增 `backend/routers/attack.py` — `POST /api/v1/attack`（执行红队攻击链）、`GET /api/v1/attack/chain/{range_id}`（获取攻击链结果）。
- 返回 `RedAttackResponse` schema（含 assets / findings / chain）。

### F4 — 防御 + 紫队评审端点
- 新增 `backend/routers/defense.py` — `POST /api/v1/defense`（执行蓝队防御）、`GET /api/v1/defense/{range_id}`（查询防御结果）、`POST /api/v1/defense/purple-review`（紫队评审）。
- 返回 `BlueDefenseResponse` / `PurpleReviewResponse` schema。

### F5 — ThreatIntel 协议扩展 + 威胁情报端点
- 扩展 `protocol/cyber.py` `ThreatIntel` dataclass：新增 `technique_id` / `sub_technique` / `detection` / `mitigation` / `risk_level` / `asset_ids` 字段。
- 新增 `backend/routers/threat.py` — `GET /api/v1/threat/attack-techniques`（支持 `?tactic=` 过滤）。
- 新增 `backend/schemas/__init__.py` — `ThreatIntelResponse` 等 6 个 Pydantic v2 响应 schema。
- 新增 `backend/services/cyber_defense.py` — `CyberDefenseService` 封装 `CyberOrchestrator`，提供 7 个业务方法。
- 更新 `backend/core/composition.py` — 注入 `CyberDefenseService`。
- 更新 `backend/routers/__init__.py` — 注册 range / attack / defense / threat 路由。

### F6 — 后端集成测试
- 新增 `tests/backend/test_cyber_endpoints.py` — 11 个测试方法：靶场启动/查询/拓扑/404、红队攻击/链查询、蓝队防御/按靶场查询/紫队评审、威胁情报全量/过滤/映射。
- 全部使用 `TestClient` + `X-API-Key: aegis-dev-key` 认证头。

### G1 — 攻击链 DAG 可视化
- 新增 `frontend/src/views/cyber/RedTeamPanel.tsx` — 自定义 SVG 渲染攻击链 DAG：资产节点（蓝色矩形）+ 攻击步骤节点（红色矩形）+ 贝塞尔曲线边 + 箭头标记。漏洞发现表 + CVSS 评分徽章 + 统计栏。

### G2 — 防御看板
- 新增 `frontend/src/views/cyber/BlueTeamPanel.tsx` — 告警列表（严重度排序 + 左边框颜色标识）、响应计划（动作类型徽章 + 置信度 + 回滚信息）、安全假设列表、事件流输入 + 执行防御按钮。

### G3 — 紫队评审 + 时序回放
- 新增 `frontend/src/views/cyber/PurpleTeamPanel.tsx` — Critique/Review 裁决展示、问题/发现列表、攻击链时间轴回放（Play/Pause/Step forward/backward + 进度计数器）。

### G4 — ATT&CK 威胁情报表
- 新增 `frontend/src/views/cyber/ThreatIntelPanel.tsx` — 战术过滤按钮（9 个战术）、统计栏、可展开表格行显示 technique_id / detection / mitigation / refs，自动 fetch。

### G5 — 前端类型映射
- 更新 `frontend/src/protocol/types.ts` — `ThreatIntel` 接口扩展 + 新增 `RangeResponse` / `TopologyResponse` / `RedAttackResponse` / `BlueDefenseResponse` / `PurpleReviewResponse` 接口。

### G6 — 前端测试
- 新增 `frontend/src/services/api/__tests__/cyber.test.ts` — 12 个 cyber API service 单元测试（mock apiClient + 断言调用参数与返回值）。
- 新增 `frontend/src/views/cyber/__tests__/cyber-views.test.tsx` — 9 个组件渲染测试（mock store + 断言 tab/按钮/面板渲染）。
- 新增依赖：`@testing-library/react` + `@testing-library/dom`。

### 前端基础设施
- 新增 `frontend/src/services/api/cyber.ts` — `cyberApi` 对象 9 个方法 + 4 个请求接口。
- 更新 `frontend/src/lib/store/index.ts` — 新增 7 个攻防状态字段 + setter。
- 更新 `frontend/src/protocol/frontend-types.ts` — `ViewName` 新增 `'cyber'`。
- 更新 `frontend/src/controllers/routes.ts` — 新增 cyber 路由。
- 更新 `frontend/src/App.tsx` — VIEWS 映射新增 `cyber: CyberView`。
- 新增 `frontend/src/views/cyber/CyberView.tsx` — 主视图（4 tab 切换 + 靶场启动栏 + 错误显示）。
- 新增 `frontend/src/views/cyber/index.ts` — barrel export。
- 更新 `frontend/src/views/index.ts` — 导出 `CyberView`。
- 更新 `frontend/src/index.css` — 新增 cyber defense 视图全部样式（~100 个 CSS class，使用暗色主题变量）。

### 质量门禁
- TypeScript 零错误（8 个新文件全部通过 `get_errors` 验证）。
- 后端 11 测试 + 前端 21 测试全通过（共 32 新增测试）。
- 项目总计 **151 测试全通过**。

## [P1] 2026-07-06 编排器实现（P5 收尾，5 子任务全完成）

### P1.1 — EventBus 事件总线
- 新增 `aegisos_agents/planning/engine/eventbus/impl.py` — `EventBus` 类：基于 `EventType` 8 topic 的发布/订阅，FIFO 顺序保证、handler 异常隔离（死信队列）、历史记录（供回放）、`subscribe` 返回取消订阅闭包。
- 新增 `aegisos_agents/planning/engine/eventbus/__init__.py` — 导出 `EventBus` + `HISTORY_LIMIT`。
- 新增 `tests/aegisos_agents/planning/test_eventbus.py` — 8 个测试：订阅接收/多订阅顺序/主题过滤/取消订阅/异常隔离死信/历史过滤/历史截断/clear 重置。

### P1.2 — Workflow DAG 工作流引擎
- 新增 `aegisos_agents/planning/engine/workflow/engine.py` — `WorkflowEngine` + `WorkflowNode` + `WorkflowStatus` + `WorkflowResult`：
  - Kahn 拓扑排序（分层 + 循环检测抛 ValueError）
  - `ThreadPoolExecutor` 同层并行执行
  - 条件分支（`condition` 谓词返回 False → Skipped）
  - 失败传播（Failed 节点的下游标记 Skipped）
  - 可选注入 `EventBus`，节点执行前后发布 `AgentStart`/`AgentFinish` 事件
- 新增 `aegisos_agents/planning/engine/workflow/__init__.py` — 导出 4 个类型。
- 新增 `tests/aegisos_agents/planning/test_workflow.py` — 8 个测试：线性链/并行汇聚/条件跳过/失败传播/循环检测/context 合并/事件发布/失败事件。

### P1.3 — Planner 任务规划器
- 新增 `aegisos_agents/planning/planner/planner.py` — `Planner` 类：4 场景模板（`cyber_red` 红队链 / `cyber_blue` 蓝队链 / `cyber_purple` 紫队并行 / `generic` 通用），纯算法分解不调 LLM，输出 `protocol.Plan`（dag + tasks）。
- 新增 `aegisos_agents/planning/planner/__init__.py` — 导出 `Planner`。
- 新增 `tests/aegisos_agents/planning/test_planner.py` — 7 个测试：红/蓝/紫场景分解 + 默认 generic + 未知场景报错 + task_id 唯一 + 场景列表。

### P1.4 — Orchestrator 通用编排器
- 新增 `aegisos_agents/planning/orchestrator/orchestrator.py` — `Orchestrator` 类：整合 Planner + WorkflowEngine + EventBus。`execute(goal, runtime, scenario)` 一站式编排；`execute_plan(plan, runtime)` 执行已构造 Plan；内部将 `Plan.dag` 转 `WorkflowNode`，executor 调用 `runtime.run(node_id, task)`，上游产出注入 `task.plan["upstream"]`。
- 新增 `tests/aegisos_agents/planning/test_orchestrator.py` — 6 个测试：红队链执行/紫队并行/事件发布/上游传递/失败传播/plan 不一致报错。

### P1.5 — CyberRuntime 真实运行时
- 新增 `aegisos_agents/planning/orchestrator/runtime.py` — `CyberRuntime` 类：实现 `RuntimeAPI`（submit/run/stop/heartbeat），内部委托 `CyberOrchestrator` 红蓝紫三条链，替代 `MockRuntime` 的 85 行 `_cyber_dispatch_map()`。`run("red_chain", task)` → `run_red_chain()`，`run("blue_chain", task)` → `run_blue_chain()`，`run("purple_review", task)` → `run_purple_review()`。
- 新增 `tests/aegisos_agents/planning/test_cyber_runtime.py` — 7 个测试：红蓝紫链调用 + submit/stop/heartbeat + 未知 agent_id 兜底。
- `MockRuntime` 保留作为向后兼容层（94 既有测试依赖），`CyberRuntime` 作为 R4.6 替代实现。

### 质量门禁
- 本机 Windows Python 3.14.6 + openai-agents 0.17.7 验证：**130 passed**（94 既有 + 36 新增），0 failed，3.56s。
- 修复 2 个 bug：workflow context 未合并到 upstream（已修）；planner cyber_purple 误链式依赖（已修，模板改为显式 deps 三元组）。
- ruff format / mypy 未运行（本机未装 ruff/mypy，待 macOS/容器验证）。

## [修复] 2026-07-06 真实 API 模式断链修复（11 Agent + CyberOrchestrator + CyberRuntime）

### 问题
- 11 个攻防 Agent（recon/detector/vuln_correlator/exploit_planner/lateral_move/triage/threat_hunt/ir_planner/forensics/critic/reviewer）的 `__init__` 重写时丢失了父类的 `model=` 参数，只接受 `provider=`（旧 MockProvider）。
- `CyberOrchestrator.__init__` 同样只接受 `mock=`，无法注入 SDK `Model`。
- 导致真实 API 模式下 SDK `Model` 无法注入到任何 Agent，`.env` 配置 `AEGIS_USE_MOCK=false` 后虽能创建 `AsyncOpenAI` 客户端，但 Agent 实例化时断链。

### 修复
- 11 个 Agent 的 `__init__` 统一加回 `model: Model | None = None` 参数，传递给 `super().__init__(model=model, mock=mock)`。
- `CyberOrchestrator.__init__` 加 `model=None` 参数，9 个 SDK Agent 共享同一 Model。
- `CyberRuntime.__init__` 加 `model=None` 参数，透传给 CyberOrchestrator。

### 验证
- 本机起 mock OpenAI HTTP 服务器（返回标准 ChatCompletions 响应），端到端验证：
  - `SDKProvider.get_sdk_model()` → `ReconAgent(model=model)` → `agent.scan()` → SDK Runner → HTTP POST → 解析 ReconResult → 返回 2 个 Asset ✅
  - `CyberRuntime(model=model)` → `run("red_chain", task)` → CyberOrchestrator 9 个 SDK Agent → 红队链执行 ✅
- 130 测试全通过无破坏（3.18s）。

### 影响
- `.env` 配 `AEGIS_USE_MOCK=false` + `OPENAI_API_KEY` 后，可真实调用 OpenAI / 火山引擎 ARK API。
- Mock 模式（默认）完全不受影响，`provider=mock` 旧接口签名保持兼容。

## [S1-S4] 2026-07-06 OpenAI Agents SDK 集成迁移（90 测试全通过）

### S1 — Provider 层：SDK 适配器 + Mock 开关 + 火山引擎 Chat Completions
- 新增 `aegisos_agents/tools/llms/sdk_provider.py` — `SDKProvider` 桥接项目 `ModelProvider` 与 SDK，支持 `AEGIS_USE_MOCK` 开关 + 火山引擎 ARK（Chat Completions API）+ 无 Key 自动降级 Mock。
- 新增 `aegisos_agents/tools/llms/mock_sdk_model.py` — `MockSDKModel` 将项目 `MockProvider` 适配为 SDK `Model` 接口，让 SDK `Runner` 在测试/评委演示场景走预置响应。
- 新增 `create_provider()` 工厂函数，供 composition.py 按运行模式选择 Provider。
- 保留 `MockProvider`（测试依赖）+ `LLMRequest/LLMResponse`（接口契约不变）。

### S2 — Agent 层：11 个攻防 Agent 迁移到 SDK 结构化输出
- 新增 `aegisos_agents/action/structured_agent.py` — `StructuredAgent[T]` 基类，封装 SDK `Agent(output_type=...)` + `Runner.run_sync()`，提供 sync `_run(prompt) -> T` 接口。
- 新增 `aegisos_agents/action/output_types.py` — 19 个 Pydantic `BaseModel`（对应 protocol/cyber.py 的 dataclass），供 SDK `output_type` 结构化输出。
- 迁移 11 个攻防 Agent（recon/detector/vuln_correlator/exploit_planner/lateral_move/triage/threat_hunt/ir_planner/forensics/critic/reviewer）：删除全部 `json.loads + try/except`（12 处），改用 SDK `output_type` 自动结构化输出 + Pydantic 验证 + 自动重试。
- 每个 Agent 保持原方法签名（`scan/correlate/plan/detect/triage/hunt/plan_response/investigate/critique/review`），兼容现有测试（`Agent(provider=mock)` 签名保留）。
- 用 `AgentOutputSchema(strict_json_schema=False)` 包装含 `dict` 字段的类型（AlertModel.raw / IRPlannerResult.rollback / ForensicsResult.timeline）。

### S3 — 编排层：SDK CyberOrchestrator 实现红蓝紫链
- 新增 `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` — `CyberOrchestrator` 用 SDK Agent 实现红蓝紫攻防链编排，替代 `MockRuntime._cyber_dispatch_map`（85 行手写路由表）。
  - `run_red_chain(target_range)` — recon → vuln_correlator → exploit_planner
  - `run_blue_chain(event_stream)` — detector → triage → threat_hunt → ir_planner
  - `run_purple_review(chain, plan, alerts)` — critic + reviewer 跨产出校验
- `MockRuntime` 保留作为 backend DI 兼容层（后续切换到 `CyberOrchestrator`）。

### S4 — 配置 + 开关
- 新增 `tooling/configs/agents_sdk.yaml` — SDK 开发配置 SSOT：模型/Provider/编排/输出类型/记忆/流式/Tracing + `use_mock` 开关 + 评委 Docker 启动说明。
- 更新 `.env` — 新增 `AEGIS_USE_MOCK` 开关 + `OPENAI_*` 环境变量（火山引擎 ARK 适配）。

### 质量门禁
- ruff format ✅ · ruff check ✅（新文件全通过）· mypy ✅（新文件 0 错误）· **pytest 94 passed**。

### 代码量变化
- 新增：SDK 适配器 ~200 行 + StructuredAgent ~130 行 + output_types ~170 行 + CyberOrchestrator ~280 行 + e2e 测试 4 新 = ~780 行新基础设施
- 删除：11 处 `json.loads+try/except` ~420 行 + 3 个旧 Provider ~360 行 = ~780 行已删除
- 净效果：基础设施层由手写 → SDK 原生，获得结构化输出/handoff/tracing/流式/多模型兼容；94 测试全通过

## [e2e] 2026-07-06 S3 编排器 e2e 测试补充（90 → 94 测试）
- 在 `tests/e2e/test_scenario1.py` 新增 4 个 CyberOrchestrator 编排层 e2e 测试：
  - `test_scenario1_orchestrator_red_chain` — 编排器红队全链路
  - `test_scenario1_orchestrator_blue_chain` — 编排器蓝队全链路
  - `test_scenario1_orchestrator_purple_review` — 编排器紫队校验
  - `test_scenario1_orchestrator_full_flow_with_memory` — 编排器 + B3 记忆闭环
- 4 测试均通过，0.69s；全量 94 passed。

## [R2] 2026-07-06 删除旧 Provider（SDK 迁移后清理）
- 删除 `openai_provider.py`（219行）/ `anthropic_provider.py`（119行）/ `local_provider.py`（22行），合计 360 行。
- SDK 迁移后这三个 Provider 已无任何引用，删除后 `tools/llms/` 目录保留：`sdk_provider.py`（桥接）+ `mock_provider.py`（测试）+ `mock_sdk_model.py`（SDK 适配）+ `model_router.py`（多模型路由）。
- 90 测试全通过无影响。

## [infra] 2026-07-06 项目目录 aegisos_agents/ → aegisos_agents/（解决 SDK 包名冲突）

### 变更内容
- **背景**：安装 `openai-agents` SDK 后，SDK 包名 `agents` 与项目目录 `aegisos_agents/` 同名冲突，`import agents` 被项目目录遮蔽导致 SDK 不可用，且 pytest collection 崩溃（25 errors）。
- **执行 A 方案**：`git mv agents aegisos_agents` + `git mv tests/agents tests/aegisos_agents`。
- **import 替换**：46 个 `.py` 文件中 86 处 `from agents.` → `from aegisos_agents.`（sed 全仓替换）。
- **配置更新**：`pyproject.toml` 的 `ruff.lint.isort.known-first-party` + `setuptools.packages.find.include` 从 `agents*` → `aegisos_agents*`。
- **editable 重装**：`pip install -e . --no-deps` 重新扫描包发现。
- **验证**：`import agents` 现解析到 SDK（site-packages）；`from aegisos_agents.xxx import` 正常；pytest 90 passed；ruff 我方文件全通过；mypy 实现文件 0 错误。
- **待办**：120 个 `.md` 文档含 `aegisos_agents/` 路径引用，多数为语义描述，关键规范文档（03_IMPORT_SPEC / 02_DIRECTORY_SPEC / 根 AGENT.md）路径更新待后续批量处理。

### 影响范围
- 46 个 `.py` 文件（aegisos_agents/ 30 + tests/aegisos_agents/ 15 + backend/ 5）
- pyproject.toml
- 目录：aegisos_agents/ → aegisos_agents/，tests/aegisos_agents/ → tests/aegisos_agents/

## [docs] 2026-07-06 框架替换方案文档核实修正

### 变更内容
- 基于 2026-07-06 对 `aegisos_agents/` 全目录 56 个 `.py` 文件（3133 行）的逐文件审查，修正 `docs/RESEARCH_AGENT_FRAMEWORK_REFACTOR.md` 4 处诊断差异 + 补入 3 处新发现：
  - **§1.1**：4 Provider 行数 ~220 → 实测 368（未计 docstring 的低估）
  - **§1.2**：11 Agent 行数 ~550 → 实测 882；补入第 12 处 `neuro_symbolic.py` L146-168（原文遗漏）
  - **§1.4**：MockRuntime 位置 `composition.py` → `backend/mocks/runtime.py`（2026-07-05 拆出）；dispatch 85 行
  - **§1.5**：memory 现状 2 实现 → 7 实现（B3 新增 5 文件 700 行）；新增 13 子模块实现状态表
  - **§1.8 新增**：`_CyberMockProvider` 硬编码 JSON 220 行 / `model_router.py` 前缀路由可由 litellm 替代 / `memory_store.py` write 分发（保留）
  - **§4**：替换前后对比表更新为实测行数（~1020 → ~1628 行可替换，-69%）
  - **§5**：保留模块表补入 B3 五层存储 + neuro_symbolic 符号验证逻辑 + model_router tier 部分
  - **§6**：迁移路线测试基线 59 → 90；阶段 3 从 2 批改 3 批（补入 neuro_symbolic + cyber_provider mock 简化）

## [P5] 2026-07-06 B3 记忆接入 runtime 认知循环 + E13 场景 1 端到端

### B3 — 记忆接入 runtime 认知循环（aegisos_agents/memory/ 域）
- 新增 `aegisos_agents/memory/working/store.py` — WorkingMemory 工作记忆：按 session_id 隔离的上下文栈，add/get/clear/sessions。
- 新增 `aegisos_agents/memory/episodic/store.py` — EpisodicMemory 情景记忆：跨会话历史经验累积，add/all/by_task。
- 新增 `aegisos_agents/memory/semantic/store.py` — SemanticMemory 语义记忆：ATT&CK/CVE 知识库，预置 8 个种子技战术（T1595/T1592/T1210/T1059/T1078/T1046/T1021/T1053），add/get/search/seed_attack_knowledge。
- 新增 `aegisos_agents/memory/vector/store.py` — VectorMemory 向量记忆：余弦相似度 Top-K 检索（Qdrant 接入预留位），add/search。
- 新增 `aegisos_agents/memory/memory_store.py` — MemoryStore 集成层：聚合四层存储 + compactor + recaller，实现 `agents.api.MemoryAPI`（read/write/retrieve），提供 recall/search_knowledge/compress/end_session 形成认知循环闭环（write → recall → compress → 压缩后情景记忆仍可唤醒）。
- 修复 `compress` 重填工作记忆时 digest 包 session_id 缺失问题：重填时给每个包盖上目标 session_id。
- 新增测试 26 个：test_working(4) + test_episodic(3) + test_semantic(4) + test_vector(5) + test_memory_store(10)。

### E13 — 场景 1 端到端测试（tests/e2e/ 域）
- 新增 `tests/e2e/test_scenario1.py` — 红→蓝→紫完整链路 5 个测试：
  - 红队链路（recon→vuln_correlator→exploit_planner→AttackChain）
  - 蓝队链路（detector→triage→threat_hunt→ir_planner→ResponsePlan）
  - 紫队链路（critic 校验攻击链 + reviewer 跨产出一致性审查）
  - 全链路数据流集成（Asset→VulnFinding→AttackChain→Alert→ResponsePlan→Critique + B3 记忆闭环验证）
  - 记忆唤醒辅助推理（recall 唤醒历史经验 + 语义知识库查询 ATT&CK 横向移动）
- 使用 `_CyberMockProvider` 驱动 11 个真实 Agent 实例，无需真实 LLM API。

### 质量门禁
- ruff format ✅ · ruff check ✅（新增文件全通过）· mypy ✅（实现文件 0 错误，protocol/ 既有 39 错误未触碰）· pytest 90 passed（59→90，+31）。

## [P6] 2026-07-04 文档整合：MODULE.md → AGENT.md

### 变更内容
- 将根 `MODULE.md` 内容合并到根 `AGENT.md` 末尾「📋 模块实现总览」段。
- 将 9 个域 `MODULE.md`（protocol/aegisos_agents/backend/frontend/infrastructure/observability/data/tooling/developer）内容合并到对应 `AGENT.md` 末尾「📋 模块实现详解」段。
- 删除全部 10 个 `MODULE.md` 文件（根 + 9 域）。
- 更新全局引用：`docs/ARCHITECTURE.md`（总览仪表盘 + 9 处详细文档链接）、`README.md`（项目结构 + 模块文档索引表）、`CLAUDE.md`（根 + `.claude/`，L0 在哪找 + 维护段）、`developer/plan.md`（文档体系记录 + 维护提醒）。
- 各 `AGENT.md` 合并段均以 `> 原 {domain}/MODULE.md 内容，已合并至此。` 标注来源。

### 动机
- 消除 `MODULE.md` 作为独立文件类型，统一到 `AGENT.md`（开发规范 + 实现详情同文档）。
- 减少文件数量，降低维护成本；新「📋 模块实现详解」段与原 AGENT.md 内容在同一文件内更易交叉引用。

## [P6] 2026-07-04 前后端打通：Agent 注册 + Chat 联调 + 文档同步

### 后端（composition.py）
- 新增 11 个攻防 Agent 注册（recon/detector/vuln_correlator/exploit_planner/lateral_move/triage/threat_hunt/ir_planner/forensics/critic/reviewer），总计 14 个 Agent（3 通用 + 11 攻防）。
- `MockRuntime` 接入真实调用：`_cyber_dispatch_map()` 分发 11 个 handler，各 handler 解析 payload/goal 并调用对应 Agent。
- `_CyberMockProvider` 封装 MockProvider，支持前缀匹配（exact match 优先，fallback prefix）。
- `_build_cyber_mock_responses()` 预置攻防场景 JSON 响应。
- 修复：`_handle_recon` 添加 CIDR/IP 检测，避免 prompt 前缀不匹配导致空资产。

### 前端
- `App.tsx`：启动时拉取 Agent 列表（`agentApi.list()` → `setAgents`）。
- `services/api/agents.ts`：`list()` 兼容后端裸数组返回（`Array.isArray(r) ? r : (r.agents ?? [])`）。
- `views/chat/ChatView.tsx`：修复 output 对象渲染崩溃（`typeof output === "string" ? output : JSON.stringify(...)`）。

### 文档同步
- `developer/roadmap/README.md`：更新进度勾选（P1-P5 已完成，P6 部分完成）。
- `CLAUDE.md`（根 + `.claude/`）：更新本机环境约束（macOS .venv Python 3.12.13）+ plans 段当前状态。
- `README.md`：更新 aegisos_agents/action 角色列表（红蓝紫 11 Agent）+ 快速开始命令 + 当前进度段。
- `aegisos_agents/action/AGENT.md`：更新输出段为红蓝紫角色列表。
- `developer/specs/04_PROTOCOL_SPEC.md`：登记 MemoryPacket.kind/recent（B1）+ GraphNode.status（C1）+ §18 Cyber 攻防类型 + §16 低熵路由/异构选举/端边云调度。
- `developer/specs/06_SCHEMA_SPEC.md`：登记 MemoryPacketSchema.kind/recent + GraphNodeSchema.status + §14 CyberSchema 类型表 + §12 映射表更新。

### 验证
- `pytest tests/ -v`：59 passed。
- GET /agents 返回 14 个 Agent；POST /aegisos_agents/recon/invoke 返回 2 资产；POST /aegisos_agents/detector/invoke 返回 1 告警。
- 前端 Chat 下拉框显示 14 个 Agent；Swagger UI 可访问。

## [P1-P5] 2026-07-04 Phase A-E：攻防核心引擎 TDD 实现

> 按 `docs/superpowers/plans/2026-07-04-agents-phase-ae.md` 计划，以 TDD 方式实现攻防群体智能核心引擎（12 任务，59 测试全通过）。

### Phase A — protocol 攻防类型 (A1)
- 新增 `protocol/cyber.py`：8 个 `@dataclass`（Asset / VulnFinding / AttackStep / AttackChain(含 to_dict/from_dict) / Alert / DefenseAction / ResponsePlan / ThreatIntel）。
- 扩展 `protocol/__init__.py`：导入 cyber 模块并登记 `__all__`。
- 测试：6 个（`tests/protocol/test_cyber.py`）。

### Phase B — 超长程记忆压缩 + 唤醒 (B1+B2)
- 扩展 `protocol/memory.py`：`MemoryPacket` 新增 `kind: str = "normal"` 和 `recent: bool = False`。
- 新增 `aegisos_agents/memory/compression/compactor.py`：`compress(context, budget)` 按 budget 压缩（decision 保留、recent 保留、其余折叠为 digest）。
- 新增 `aegisos_agents/memory/recall/recaller.py`：`recall(trigger, episodic, vector)` 按相关性 + kind 优先级唤醒 TOP_K=5 条记忆。
- 测试：7 个（4 compactor + 3 recaller）。

### Phase C — 拓扑 + 低熵路由 + 异构选举 (C1+C2+C3)
- 扩展 `protocol/graph.py`：`GraphNode` 新增 `status: str = "active"`（active | idle | degraded）。
- 新增 `aegisos_agents/planning/engine/topology/topology.py`：`active_subgraph(graph, required_capability)` 过滤活跃+能力匹配节点。
- 新增 `aegisos_agents/planning/engine/router/router.py`：`route(message, topology, required_capability) -> list[NodeRef]`，Top-K=3 稀疏路由（非全广播），按 success_rate - latency 排序。
- 新增 `aegisos_agents/planning/engine/router/election.py`：`elect(task_features, instances, capability_vectors) -> NodeRef`，任务特征向量与能力向量点积最大者当选。
- 测试：10 个（3 topology + 4 router + 3 election）。
### Phase D — 端边云三层调度 + 多模型兼容层 (D1+D2)
- 扩展 `protocol/scheduler.py`：`Task` 新增 `privacy: str = "standard"` 和 `latency_budget: float = 10.0`。
- 新增 `aegisos_agents/planning/engine/scheduler/scheduler.py`：`schedule(task, models, required_capability) -> Model`，端边云三层卸载（device/edge/cloud），四规则 + 降级：privacy=local→device，latency<1s→device，latency<5s→edge，默认→cloud；缺失时逐级降级。
- 新增 `aegisos_agents/tools/llms/` 多模型兼容层：
  - `base.py`：`ModelProvider` Protocol + `LLMRequest` / `LLMResponse` dataclass。
  - `mock_provider.py`：确定性 Mock（测试/离线开发用）。
  - `openai_provider.py`：OpenAI API 兼容（httpx）。
  - `anthropic_provider.py`：Anthropic Claude API（httpx）。
  - `local_provider.py`：Ollama / vLLM / LM Studio 本地模型。
  - `model_router.py`：`ModelRouter` 按模型前缀 / tier 路由到对应 provider。
  - `scheduler_adapter.py`：薄适配层，避免 tools 直接依赖 planning。
- 测试：13 个（8 scheduler + 5 model_router）。

### Phase E — 红蓝紫 Agent 角色 + 神经符号闭环 (E1-E12)
- **红队 (E1-E4)**：
  - `aegisos_agents/action/recon/`：`ReconAgent.scan(target_range) -> list[Asset]`
  - `aegisos_agents/action/vuln_correlator/`：`VulnCorrelatorAgent.correlate(assets) -> list[VulnFinding]`
  - `aegisos_agents/action/exploit_planner/`：`ExploitPlannerAgent.plan(findings) -> AttackChain`
  - `aegisos_agents/action/lateral_move/`：`LateralMoveAgent.plan_moves(chain, topology) -> list[AttackStep]`
- **蓝队 (E5-E9)**：
  - `aegisos_agents/action/detector/`：`DetectorAgent.detect(event_stream) -> list[Alert]`
  - `aegisos_agents/action/triage/`：`TriageAgent.triage(alerts) -> list[Alert]`（去噪 + 严重度排序）
  - `aegisos_agents/action/threat_hunt/`：`ThreatHuntAgent.hunt(alerts) -> list[dict]`（狩猎假设）
  - `aegisos_agents/action/ir_planner/`：`IRPlannerAgent.plan_response(hypotheses) -> ResponsePlan`
  - `aegisos_agents/action/forensics/`：`ForensicsAgent.investigate(plan) -> dict`（取证报告）
- **紫队 (E10-E11)**：
  - `aegisos_agents/action/critic/`：`CriticAgent.critique(target, side) -> dict`（对抗性校验）
  - `aegisos_agents/action/reviewer/`：`ReviewerAgent.review(artifacts) -> dict`（一致性审查）
- **神经符号闭环 (E12)**：
  - `aegisos_agents/perception/reasoning/neuro_symbolic.py`：`validate_chain(chain, rules)` 符号校验 + `NeuroSymbolicLoop.validate_and_fix(chain, rules, max_iterations)` LLM 生成→符号校验→反馈→修正循环。
- 测试：23 个（6 red + 8 blue + 4 purple + 4 neuro-symbolic + 1 forensics）。

### 质量门禁
- `ruff format`：43 文件已格式化。
- `ruff check --fix`：51 个问题自动修复，剩余 8 个为既有代码（StrEnum 建议 + 已有模块类型注解）。
- `pytest tests/ -v`：**59 passed in 0.05s**。
- 所有 AI 生成代码含 `@aegis-gen` 注释头（date/dev/change）。

## [P0] 2026-06-26
- 初始化 AegisOS 仓库骨架（37 顶层模块 + memory 12 子模块 + agents 10 子模块）。
- 建立 AI 开发规范层 `developer/`（架构/路线图/协议/各指南）。
- 建立全仓库 AGENT.md 体系（root + 37 模块 + 10 agents，共 48 个）。
- 建立系统级开发计划 `developer/roadmap/P0..P7`。
- 建立通信协议契约 `protocol/`（Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync）。
- 建立 memory 子系统各子模块 README 与 ROADMAP 各阶段文档。

## [P0] 2026-06-26 重构：同域聚合分层
- 将 37 个平铺顶层目录重组为 15 个分层域目录，同属一域的模块归到一起：
  - `backend/` 吸收 `gateway/`（`backend/gateway/`）。
  - `aegisos_agents/` 吸收智能体相关：`memory/`→`aegisos_agents/memory/`、`llms/`→`aegisos_agents/tools/llms/`、`prompts/`→`aegisos_agents/tools/prompts/`、`reasoning/`、`reflection/`、`context/`、`runtime/`（其中 `aegisos_agents/memory/semantic/` 即知识库）。
  - `aegisos_agents/planning/engine/` 聚合编排：`planner/`、`scheduler/`、`router/`、`workflow/`、`eventbus/`、`topology/`。
  - `aegisos_agents/action/execution/` 聚合 `executor/`、`tools/`。
  - `infrastructure/` 聚合 `communication/`、`edge/`、`cloud/`、`deployment/`。
  - `observability/` 聚合 `monitor/`、`replay/`、`benchmark/`、`evaluation/`、`visualization/`。
  - `data/` 聚合 `datasets/`、`models/`。
- 新增 7 个域根 AGENT.md（backend/aegisos_agents/planning/engine/execution/infrastructure/observability/data）。
- 重写全部 AGENT.md（路径引用更新为新分层路径）、memory 12 子模块 README、ROADMAP P0..P7。
- 更新 developer/ 规范文档（DIRECTORY_GUIDE/ARCHITECTURE/ROADMAP 等）以反映分层。
- AGENT.md 体系扩充至 55 个（含域根）。

## [P0] 2026-06-26 重构：进一步同域聚合
- 顶层目录从 15 进一步收敛到 13：
  - `ROADMAP/`（阶段计划）并入 `developer/roadmap/`（规范层即项目大脑），总览 `developer/ROADMAP.md` → `developer/roadmap/README.md`，P0..P7 → `developer/roadmap/P0..P7/`。
  - `configs/` + `scripts/` 合并为 `tooling/`（`tooling/configs/` + `tooling/scripts/`），新增 `tooling/AGENT.md` 域根。
  - `examples/` 并入 `docs/examples/`（示例属文档资产），更新 `docs/AGENT.md` 域根。
- 批量更新所有 AGENT.md 与 developer 文档的路径引用（ROADMAP→developer/roadmap、configs→tooling/configs、scripts→tooling/scripts、examples→docs/examples）。
- 重写根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 支撑行、developer/docs/tooling 域根 AGENT.md。
- AGENT.md 体系现为 54 个（新增 tooling 域根）。

## [P0] 2026-06-26 重构：agent 相关全部归入 aegisos_agents/
- 将编排引擎与执行能力（均与 agent 相关）移入 aegisos_agents/ 域：
  - `engine/` → `aegisos_agents/planning/engine/`（planner/scheduler/router/workflow/eventbus/topology）
  - `execution/` → `aegisos_agents/action/execution/`（executor/tools）
- 顶层目录从 13 收敛到 11：aegisos_agents/ 现包含一切与 agent 相关的功能（角色 Agent + 认知 + 记忆 + 模型 + 提示词 + 运行时 + 编排引擎 + 执行能力）。
- 批量更新所有 AGENT.md 与 developer 文档的路径引用（engine/→aegisos_agents/planning/engine/、execution/→aegisos_agents/action/execution/）。
- 更新 aegisos_agents/ 域根 AGENT.md（纳入 engine + execution 子模块）、根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与设计原则。
- 与 agent/backend/frontend 三者不相干的模块（protocol/infrastructure/observability/data/tooling/docs/tests/developer）保持不动。

## [P0] 2026-06-26 重构：各域内部分类
- 为每个大模块按其领域范式做内部分类，新增 19 个分类层 AGENT.md：
  - **aegisos_agents/ 感知-规划-行动-记忆-工具**（认知架构五层）：
    - `aegisos_agents/perception/`（感知）：context、reasoning、reflection
    - `aegisos_agents/planning/`（规划）：planner(角色)、orchestrator(角色)、engine/(编排引擎)
    - `aegisos_agents/action/`（行动）：coder/executor/tester/debugger/critic/reviewer/researcher/docwriter(角色) + execution/(沙箱+工具)
    - `aegisos_agents/memory/`（记忆）：12 子模块（不变）
    - `aegisos_agents/tools/`（工具）：llms、prompts、runtime
  - **backend/ DDD 四层**：domain/(核心域)、application/(应用层)、infrastructure/(基础设施:gateway)、interfaces/(接口层)
  - **frontend/ 功能特性**：canvas/、graph/、monitor/、replay/、shared/
  - **infrastructure/ 传输-节点-交付**：transport/、nodes/、delivery/
  - **observability/ 观测-度量-呈现**：inspect/、measure/、present/
- 批量更新所有 AGENT.md 与 developer 文档的路径引用。
- 更新全部域根 AGENT.md（aegisos_agents/backend/frontend/infrastructure/observability）含分类表格。
- 重写根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与数据流。
- AGENT.md 体系现为 73 个（域根 + 分类层 + 叶模块三级）。

## [P0] 2026-06-26 重构：后端/前端改为 Controller-Service-Mapper 架构
- **backend/** 由 DDD 四层改为经典三层 + 网关：
  - `controllers/`（控制器：参数校验/响应封装，不含业务逻辑）
  - `services/`（服务：业务逻辑/用例编排/事务）
  - `mappers/`（映射器：数据转换 protocol<->entity<->dto、仓储/持久化）
  - `gateway/`（网关：鉴权/限流/路由分发/协议适配，从 infrastructure/ 提升）
  - 删除 domain/application/interfaces/infrastructure DDD 目录。
- **frontend/** 由功能特性改为与后端对称的三层 + 视图：
  - `controllers/`（控制器：交互/事件处理/路由分发，不含业务逻辑）
  - `services/`（服务：API 调用/WS·SSE 管理/状态编排）
  - `mappers/`（映射器：数据转换/视图模型/全局状态/共享工具/样式/资产）
  - `views/`（视图：canvas/graph/monitor/replay 功能特性 UI）
  - 删除顶层 canvas/graph/monitor/replay/shared 特性目录（views/ 下保留功能特性）。
- 重写 backend/ 与 frontend/ 域根 + 各层 AGENT.md（共 9 个）。
- 更新根 AGENT.md 分层、DIRECTORY_GUIDE、ARCHITECTURE 分层图与数据流、BACKEND_GUIDE、FRONTEND_GUIDE。
- 批量修正路径引用（domain→services、application→services、interfaces→controllers、infrastructure/gateway→gateway、shared→mappers、canvas/graph/monitor/replay→views/下）。

## [P0] 2026-06-26 重构：模块间 API 解耦
- 为每个域新增 `api/` 公共接口子包，其他模块只通过 `from {domain}.api import ...` 调用，不直接访问内部实现，实现解耦：
  - `aegisos_agents/api/` — 7 接口：AgentRegistryAPI · MemoryAPI · PlanningAPI · ExecutionAPI · PerceptionAPI · EventBusAPI · RuntimeAPI
  - `backend/api/` — 5 接口：SessionAPI · TaskAPI · MemoryGatewayAPI · GraphAPI · EventStreamAPI
  - `frontend/api/` — 3 接口：ViewAPI · InteractionAPI · ThemeAPI
  - `infrastructure/api/` — 4 接口：CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI
  - `observability/api/` — 6 接口：MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI
  - `data/api/` — 2 接口：DatasetAPI · ModelSchemaAPI
  - `tooling/api/` — 2 接口：ConfigAPI · ScriptAPI
- 每个 `api/` 含 `__init__.py`（Python Protocol 接口，参数/返回值用 protocol/ 类型）与 AGENT.md（解耦原则 + 接口清单）。
- 更新全部 7 个域根 AGENT.md 下辖子模块加入 api/ 层。
- 更新根 AGENT.md 全局铁律、ARCHITECTURE 设计原则、DIRECTORY_GUIDE 顶层表格、API_SPEC 模块间解耦章节。
- 全部 7 个 api 包可导入，共暴露 29 个公共接口。

## [P0] 2026-06-26 动态 README
- 新增 `tooling/scripts/gen_readme.py`：扫描仓库实际目录树、AGENT.md 计数、api 公共接口（解析各域 `api/__init__.py` 的 `__all__`）、文件统计，自动生成根 `README.md`。
- README 含：项目介绍、核心特性、架构总览、顶层目录表、aegisos_agents/backend/frontend 内部分层、模块间 API 解耦表、数据流、通信协议、开发流程、快速开始、自动生成的目录树与仓库统计、关键文档索引。
- 「实际目录结构」与「仓库统计」段为自动生成，勿手改；结构/api 变动后运行 `python3 tooling/scripts/gen_readme.py` 刷新。
- 更新 tooling/scripts/AGENT.md（登记 gen_readme.py + 动态维护说明）、根 AGENT.md（README 动态维护段）、DEVELOPER_GUIDE（流程加入 README 刷新步骤）。

## [P0] 2026-07-03 规范整体改造：全仓对齐 SSOT + 仓库卫生 + frontend 结构重构

> 触发：根 `AGENT.md` 与 `developer/specs/README.md` 声明 `developer/specs/`（00–13）为唯一真相源（SSOT）并"取代" `developer/` 根旧指南，但 77/78 个模块 `AGENT.md` 与 `README` 仍引用旧文档——本次把全仓对齐到 SSOT。

- **删除旧指南**：删除 `developer/` 根下 20 个被 `developer/specs/` 取代的旧指南（`AGENT_GUIDE`/`API_SPEC`/`ARCHITECTURE`/`BACKEND_GUIDE`/`CODING_RULES`/`DEPLOY_GUIDE`/`DESIGN`/`DEVELOPER_GUIDE`/`DEVELOPMENT_PLAN`/`DIRECTORY_GUIDE`/`EVENT_SPEC`/`FRONTEND_GUIDE`/`MEMORY_GUIDE`/`MESSAGE_PROTOCOL`/`PROJECT_BOOTSTRAP`/`PROMPT_GUIDE`/`PYTHON_STYLE`/`ROUTER_GUIDE`/`TEST_GUIDE`/`TOOL_SPEC`）；保留 `developer/AGENT.md`、`CHANGELOG.md`、`roadmap/`、`specs/`。
- **全量 AGENT.md 引用重定向**：新增 `tooling/scripts/realign_agent_docs.py`（带 `@aegis-gen` 头），把 77 个模块 `AGENT.md` 中 346 处旧文档引用按映射重定向到 `developer/specs/`（ARCHITECTURE→01、DIRECTORY_GUIDE→02、MESSAGE_PROTOCOL→04、API_SPEC→05、EVENT_SPEC→07、CODING_RULES→11、PYTHON_STYLE→12、ROUTER_GUIDE→04 等）；同步修正 12 个 `aegisos_agents/memory/*/README.md`、`roadmap/P1`、`specs/08`（PROMPT_GUIDE/TOOL_SPEC 并入本文件）、`protocol/__init__.py` 的残留引用。
- **根规范更新**：根 `AGENT.md`、`developer/specs/README.md`、`developer/AGENT.md`（删除无效 `补充.md`/`开发.md` 引用、下辖子模块改指 specs/）的"取代/历史参考"表述改为"已删除"。
- **README 重生成**：修正 `gen_readme.py`（关键文档/通信协议/开发流程段改指 specs/、计数排除 `.venv`/`.claude`/`node_modules`/`__pycache__`/`*.egg-info` 等噪声、顶层域排除 egg-info）；手动同步 `README.md`（doc-ref 段 + 统计刷新：78 AGENT.md / 56 py / 116 md / 232 文件 / 123 目录）。
- **frontend 代码结构重构**：删除重复编译配置 `vite.config.js`/`playwright.config.js`（保留 `.ts`）；重构 `gen_ts_types.py` 剥离硬编码前端类型块（生成器只产出 protocol 契约类型，职责分离）；重建 `frontend/src/protocol/frontend-types.ts` 为前端本地类型唯一手维护来源（修正 `ViewName` 缺 `'chat'` 的分叉、统一 `Record<string, unknown>`）；10 处导入重定向（前端本地类型→`@/protocol/frontend-types`，protocol 类型→`@/protocol/types`）。验收：`tsc -b` 与 `vite build` 均通过（69 模块）。
- **仓库卫生**：扩充根 `.gitignore`（`__pycache__`/`*.pyc`/`.venv`/`*.db`/`.DS_Store`/各 cache/frontend 构建产物）；`git rm --cached` 取消跟踪 `.DS_Store`、`data/aegisos.db`、`.venv/`（**7532 文件，macOS venv 误提交**）、`aegisos.egg-info/`。tracked 文件 7861→329。
- 所有 AI 改动加 `@aegis-gen` 注释头（§10）。
- **未执行**：Python 侧质量门禁（ruff/mypy）与 `gen_readme.py`/`gen_ts_types.py` 实际运行——本机无 Python 解释器（仓库原在 macOS 开发，`.venv` 为 macOS 专用；Windows 仅有 node）。realign 经等价 perl 完成（结果已校验：0 残留）；README/types 经手动同步；frontend 经 `tsc`+`build` 验证。待 Python 环境就绪后运行 `python3 tooling/scripts/gen_readme.py` 与 `npm run gen:types` 可刷新自动生成段（`types.ts` 中现已无引用的前端类型导出会在下次 `gen:types` 时自动清除）。

## [P0] 2026-07-03 赛事作品方案固化（XH-202631 荣耀·超长程群体智能）

> 赛事作品「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」以 AegisOS 为底座。本步固化总体方案与可执行任务清单（Spec First）。

- 新增 `developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`：定位与赛事对齐（5 能力维度 / 评分完整性40+应用创新25+技术创新20+性能15 / 截止 2026-09-15）、复用 8 域分层架构、红蓝紫 Agent 角色清单（recon/vuln_correlator/exploit_planner/lateral_move · detector/triage/threat_hunt/ir_planner/forensics · planner/orchestrator/router/critic/reviewer）、攻防协议类型设计（`protocol/cyber.py`：Asset/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel）、动态异构拓扑 + 低熵稀疏路由伪代码（Top-K 非全广播 + 异构选举）、超长程记忆压缩/唤醒伪代码（12 子模块映射 ATT&CK/CVE/向量/情景）、神经-符号协同推理闭环、端边云调度策略、后端/前端/基建扩展、生产级技术栈表、3 场景演示脚本（防御/软工/投研）、roadmap P0-P7 对齐、评分对齐表、风险与里程碑验收。
- 新增 `developer/specs/plans/15_CYBERDEFENSE_TASKS.md`：writing-plans 格式实施任务清单，按 Phase A-H（对应 P1-P7 + 攻防基建）拆解；核心算法任务（B 记忆压缩、C 拓扑/路由）含完整 TDD 测试 + 实现代码；其余任务含确切文件路径 + 接口契约 + 验收命令；含 Self-Review 与 Execution Handoff。
- `developer/specs/README.md` 索引追加 14、15。
- `developer/roadmap/README.md` 追加「赛事作品对齐」段（各阶段→攻防扩展映射 + 截止）。
- 决策记录：场景=攻防对抗仿真靶场；LLM=云+端混合多模型兼容层；技术栈=升级为生产级；演示=3 场景跨领域。
- 约束：攻防工具仅 Docker 沙箱靶场内运行、永不触真实网络；router 禁低熵全广播；AI 代码须 `@aegis-gen` 头。
- **下一步**：按 Phase A→B→C 顺序执行（契约 + 核心算法优先），可选 subagent-driven-development 并行推进。

## [P0] 2026-07-03 AGENT.md 交叉引用改造 + CLAUDE.md 工程总览

> 对齐用户需求：全仓 AGENT.md 复核（职责边界 + 交叉引用，让 agent 快速定位去哪里）+ 生成 `.claude/CLAUDE.md`（渐进式披露工程总览）。

- **根 `AGENT.md`**：规范表补 `plans/14`、`plans/15` 行；「00–12」→「00–15」（2 处 + 表格），与 `specs/README.md` 索引一致。
- **77 个模块 AGENT.md**：新增 `tooling/scripts/add_agent_crossrefs.pl`（带 `@aegis-gen` 头，UTF-8 安全，幂等：已存在则跳过），为每个模块 AGENT.md 追加标准化 `## 交叉引用（去哪里找）` 段——本模块规范（域派生 + 子路径微调：router/topology 补 `04 §16` 低熵、action/execution 补 `11` 沙箱、memory 补 `B1-B3` 压缩/唤醒）、API 边界（有 api/ 的 7 域）、数据契约、相关计划（backend/frontend→13+15；aegisos_agents/protocol/infra/observability/data/tooling→14+15）。域根插入在「下辖子模块」前，叶模块追加末尾。验收：77/77 覆盖（grep 校验）、抽查 router/backend/protocol UTF-8 与插入位置正确。
- **单一职责**：经跨域抽样（根/aegisos_agents/protocol/backend/aegisos_agents/memory + router/frontend-views 等 8 份）核验，各 AGENT.md 仅描述本模块事务、无越界；脚本仅追加未删改原文。
- **`.claude/CLAUDE.md`**：渐进式披露工程总览——L0 30 秒上手（定位+铁律+在哪找）、L1 项目与 8 域分层+工作流+铁律、L2 模块地图（域→职责→规范→计划→api）、L3 深指针（specs 00–15 索引、roadmap P0–P7、22 skills 分组、plans 13–15）+ 本机环境约束（无 Python / protocol dataclass 现状）。
- **注意**：`.claude/` 已被 `.gitignore`（第 2 行）→ `.claude/CLAUDE.md` 不提交、不自动加载；根 `CLAUDE.md` 未被忽略且为 Claude Code 默认自动加载位置——是否复制到根待用户确认。
- **子代理说明**：原计划 7 组并行子代理审计，但本 token 对子代理执行模型 `deepseek-v4-flash` 无访问权（403，model 覆盖无效），子代理整条路不通；改用 perl 脚本一次性完成，结果已校验。

## [P0] 2026-07-04 目录重构：backend 代码移入 src/ + 前端清理废弃顶层目录

> 触发：前端 service/mapper/controller 等代码全部在 `frontend/src/` 下，顶层 `frontend/api/`、`frontend/controllers/`、`frontend/services/`、`frontend/mappers/`、`frontend/views/` 为旧结构残留且无实际引用；后端需与前端对齐，代码移入 `backend/src/`。

- **前端清理**：删除 5 个废弃顶层目录（`frontend/api/`、`frontend/controllers/`、`frontend/services/`、`frontend/mappers/`、`frontend/views/`）；所有前端代码统一在 `frontend/src/` 下。
- **后端重构**：将 `backend/` 下原顶层代码全部移入 `backend/src/`：`main.py`、`composition.py`、`api/`、`controllers/`、`gateway/`、`mappers/`、`services/`；新增 `backend/__init__.py` 作为包标记。
- **批量 import 更新**：20 个后端 `.py` 文件的 `from backend.X` → `from backend.src.X`（42 处匹配）。
- **配置更新**：`pyproject.toml` 加 `where = ["."]`；`Makefile`/`start.sh` 中 `uvicorn backend.main:app` → `uvicorn backend.src.main:app`；`tooling/scripts/gen_readme.py` 适配后端 `src/api` 子路径、前端无 Python API。
- **AGENT.md 更新**（7 个）：`backend/AGENT.md` + `backend/src/api/AGENT.md` + `controllers/AGENT.md` + `services/AGENT.md` + `mappers/AGENT.md` + `gateway/AGENT.md` + `frontend/AGENT.md`。
- **规范文档更新**（10 个文件）：
  - `00_PROJECT_SPEC.md`（入站边界 + 分层表）
  - `01_ARCHITECTURE_SPEC.md`（前端边界 + 插件路径）
  - `02_DIRECTORY_SPEC.md`（frontend 域表格全面重写 + 依赖矩阵行）
  - `03_IMPORT_SPEC.md`（依赖矩阵去 `frontend.api` 列 + `backend.api`→`backend.src.api`）
  - `05_API_SPEC.md`（§2.1 前端无 Python API 重写 + §2.2 `backend.src.api`）
  - `09_DEVELOPMENT_SPEC.md`（前端开发流程引用路径）
  - `10_INTERFACE_BOUNDARY_SPEC.md`（接口矩阵表 + 禁止行 + 前端依赖行）
  - `12_TECH_STACK_SPEC.md`（技术栈路径引用 5 处）
  - `plans/13_FRONTEND_BACKEND_PLAN.md`（前端分层表路径 + B0 里程碑 `uvicorn backend.src.main:app`）
  - `README.md`（API 解耦表：`backend.api`→`backend.src.api`、`frontend.api`→无）
- **后端代码 docstring 更新**（5 个文件）：`backend/src/api/__init__.py` + `services/graph.py` + `memory.py` + `session.py` + `task.py` 中 `backend.api` 引用 → `backend.src.api`（`@aegis-gen` 注释头不动）。
- **CLAUDE.md 更新**：根 `CLAUDE.md` + `.claude/CLAUDE.md` 同步（backend api 列→`backend/src/api/`、前端无 api）。
- **验收待执行**：`tsc --noEmit` + `vite build`（前端）；`uvicorn backend.src.main:app`（后端）

## [P6] 2026-07-05 后端重构：Controller-Service-Mapper → Router-Service-Repository-Model（扁平四层）

### 重构概要
将 `backend/src/{controllers,services,mappers,gateway,api}` 旧嵌套结构重构为经典 Python 扁平四层架构 `backend/{routers,services,repositories,models}` + 辅助层 `core/schemas/mocks`，删除 `backend/src/` 目录。

### 目录变更
- **旧 → 新映射**：
  - `backend/src/main.py` → `backend/main.py`
  - `backend/src/composition.py` → `backend/core/composition.py`（813 行精简至 ~170 行）
  - `backend/src/gateway/{auth,middleware,routes}` → `backend/core/{auth,middleware,routes}.py`
  - `backend/src/controllers/{api,sse,ws,schemas}` → `backend/routers/{*.py}` + `backend/schemas/`
  - `backend/src/controllers/api/` 下 10 个路由 → `backend/routers/{health,sessions,tasks,agents,memory,graph,tools,metrics,replay,sse,ws}.py`
  - `backend/src/services/` → `backend/services/{session,task,agent,memory,graph}_service.py + di_ports.py`
  - `backend/src/mappers/{database,repositories}` → `backend/repositories/{database,repositories}.py`
  - `backend/src/mappers/{entities,converters}` → `backend/models/{entities,converters}.py`
  - `backend/src/api/` → `backend/api.py`
  - `backend/src/controllers/schemas/` → `backend/schemas/__init__.py`
- **新增**：`backend/mocks/` 目录（6 个 mock 文件从 composition.py 拆分：agent_registry/runtime/cyber_provider/memory/execution/event_bus）
- **删除**：`backend/src/` 整个旧目录（含 controllers/services/mappers/gateway/api 子目录及 AGENT.md）

### composition.py 拆分
- 原文 813 行内联全部 Mock 类定义 → 精简至 ~170 行，Mock 类移至 `backend/mocks/` 6 个独立文件。
- `aegisos_agents/tools/llms/mock_provider.py` 新增 `responses` property（修复私有属性 `_responses` 封装泄漏）。
- 新增 `backend/services/di_ports.py`（DI 端口 Protocol 定义，供 core/composition.py 实现）。

### Import 路径映射（48 处 .py 更新）
- `backend.src.composition` → `backend.core.composition`
- `backend.src.controllers.schemas` → `backend.schemas`
- `backend.src.controllers.api` → `backend.routers`
- `backend.src.controllers.{sse.events,ws.stream}` → `backend.routers.{sse,ws}`
- `backend.src.gateway.{auth,middleware,routes}` → `backend.core.{auth,middleware,routes}`
- `backend.src.mappers.{database,repositories}` → `backend.repositories.{database,repositories}`
- `backend.src.mappers.{entities,converters}` → `backend.models.{entities,converters}`
- `backend.src.services.*` → `backend.services.*_service`
- `backend.src.api` → `backend.api`

### 配置文件更新
- `Makefile`：`backend.src.main:app` → `backend.main:app`
- `start.sh`：`backend.src.main:app` → `backend.main:app`
- `tooling/scripts/gen_readme.py`：`backend.src.api` → `backend.api`、`src/api` → `api`
- `README.md` + 根 `MODULE.md`：启动命令更新

### AGENT.md 更新（7 个新建 + 1 个重写）
- **重写**：`backend/AGENT.md`（Controller-Service-Mapper → Router-Service-Repository-Model 全面重写）
- **新建**：`backend/routers/AGENT.md`、`backend/services/AGENT.md`、`backend/repositories/AGENT.md`、`backend/models/AGENT.md`、`backend/core/AGENT.md`、`backend/schemas/AGENT.md`、`backend/mocks/AGENT.md`
- **删除**：旧 `backend/src/{api,controllers,gateway,mappers,services}/AGENT.md`（5 个）
- **重写**：`backend/MODULE.md`（架构图、文件表、端点表全部更新为新路径）

### 规范文档更新（10 个文件）
- `00_PROJECT_SPEC.md`（入站边界 + 分层表）
- `01_ARCHITECTURE_SPEC.md`（前端边界 + 后端结构）
- `02_DIRECTORY_SPEC.md`（3 处 frontend 引用）
- `03_IMPORT_SPEC.md`（依赖矩阵表头）
- `05_API_SPEC.md`（2 处 backend.src.api）
- `09_DEVELOPMENT_SPEC.md`（2 处 backend.src）
- `10_INTERFACE_BOUNDARY_SPEC.md`（接口矩阵表 5 处 + gateway → core + 禁止行 2 处 + 前端契约行）
- `12_TECH_STACK_SPEC.md`（2 处 backend.src）
- `plans/13_FRONTEND_BACKEND_PLAN.md`（B0 里程碑启动命令）
- `developer/plan.md`（动态计划同步）

### 验收
- ✅ `ruff format`：23 files reformatted（通过）
- ✅ `ruff check --fix`：4 errors fixed, 0 remaining（通过）
- ✅ `pytest`：59 passed（通过）
- ⚠️ `mypy`：86 errors（均为预先存在的类型标注问题，非本次重构引入；其中 composition.py:101 的 MockEventBusAPI.subscribe 返回类型不匹配需后续修复）
