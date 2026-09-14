# CHANGELOG.md

> 所有变更记录于此。格式：`[阶段] 变更描述`。

## [R21-TASKMAP] 2026-09-14 Graph+Canvas 合并为「任务图」+ Replay 移除

### 用户诉求
1. 只要验证路由是否正常（不做本地 Ollama）
2. 去掉 Replay（历史回顾统一走「演练历史」+ 任务图回看）
3. Graph / Canvas 对用户不友好 → 合并成一个图，点节点看 Agent 输入/输出（低代码风格）
4. Chat 与 Cyber Defense 在同一页面用切换按钮区分，随不同任务整体刷新（不堆叠）
5. 支持查看历史演练记录供回顾

### 路由验证结论（本轮实测）
- 后端 `real` 模式运行，三节点（device/edge/cloud）全部 online，`/api/v1/drill/{id}` 的
  `phase` 字段真实决策：red→device、blue→edge、purple→cloud（R20 自适应调度生效）
- `pytest tests/infrastructure/nodes/test_node_registry.py tests/backend` → 82 passed
- 本地 Ollama 按用户要求不做配置，路由维持 ARK 单端点 + 执行时调度

### 修改
- **新增** `frontend/src/views/taskmap/TaskMapView.tsx`（R21 合并视图）：
  - 顶部 Chat 对话流 / Cyber Defense 演练流切换按钮（全局 store 记忆，切页不丢）
  - Chat 模式：任务 DAG（含 Chat 发起的演练任务）+ 底部「对话记忆」条，5s 轮询随新问题刷新
  - Cyber 模式：红→蓝→紫轮次图（含端边云落点徽标），4s 跟随 CyberDrillPanel 现场快照，
    新一轮演练整体替换不堆叠；历史下拉可回看任意演练；点节点右侧看输入/输出
- `frontend/src/protocol/frontend-types.ts` / `controllers/routes.ts`：视图收敛为 6 个
  （chat/taskmap/monitor/cyber/drill-history/settings），旧名 graph/canvas/replay 自动迁移
- `frontend/src/lib/store/index.ts`：新增 `taskMapMode` / `taskMapSelectedNode` 与 setter
- 删除 `views/graph/`、`views/canvas/`、`views/replay/` 及 CanvasView 单测
- `views/chat/ChatView.tsx`：演练快照 key `aegis.canvas.drill.*` → `aegis.taskmap.drill.*`，
  超时文案指向任务图
- `views/drill-history/DrillHistoryView.tsx`：新增「↗ 在任务图中查看」跳转（双向打通）
- `e2e/`：modules-smoke/interactions 改为任务图巡检（模式切换 + 节点检视 + 历史选择器）

### 验证
- `npx tsc -b` 0 错误；`npm run build` 成功
- 前端单测 50 passed（e2e/*.spec.ts 6 个文件级失败为 vitest 误扫 Playwright spec 的历史遗留）
- Playwright 任务图相关 5 用例（含导航 6 项）全过

## [DRILL-RESUME-FIX] 2026-09-14 切页状态恢复 + Stop 失效 + 端边云误报离线

## [DRILL-RESUME-FIX] 2026-09-14 切页状态恢复 + Stop 失效 + 端边云误报离线

### 用户症状
1. 点「开始演练」后切到其他模块再回来，UI 不保持原状态
2. Stop 点了没反应
3. CoT 时间线一直显示「等待首个 agent 启动」（任务实际在推进）
4. Monitor 端边云全部显示断联，但演练任务仍在跑

### 根因
- **1/2/3 同一条因果链**：`CyberDrillPanel` 卸载清理把 `drillIdRef.current` 置 null，
  而 React StrictMode（vite dev）卸载重挂不重新初始化 ref → 切页回来后 ref 永远 null：
  `handleStop` 读 null 直接 return（Stop 无反应）；3s 兑底轮询读 null 直接 return
  （CoT 永远空态）；接管 effect 读 null 不订阅 SSE（UI 冻结，而演练仍在跑）。
  叠加因素：快照只存轮次不存 agentTrace/stage/elapsed，切回瞬间也闪回空态。
- **4**：三节点常指向同一云端 API，一次网络抖动同时抬高三者 consecutive_failures，
  后端 fail_threshold=2 + 前端重复阈值 `<2` 并行生效 → 一次抖动约 30s 内全部误判离线；
  演练走独立 LLM 客户端不经节点注册表，所以任务照常推进（表现即"都断联了还在跑"）。

### 修改
- `frontend/src/views/cyber/CyberDrillPanel.tsx`：
  - 卸载清理不再置空 `drillIdRef`（仅关闭 SSE；ref 只由 handleStart 写新值）
  - 快照增加 agentTrace/stage/elapsed/liveMaxRounds，切页回来立即还原进度
  - drill_done/drill_error 复位 stopping，phase 离开 running 时兑底复位（修复
    兑底轮询发现终态后按钮永久卡「停止中…」）
  - 移除接管 effect 中永假/误伤的 stale 启发式：后端报 running 即接管
    （后端重启场景由 404 自愈分支处理）
- `frontend/src/services/api/infra.ts`：isOnline 只信后端 offline 判定，去掉重复阈值
- `frontend/src/components/InfraNodePanel.tsx`：复用统一 isOnline（别名导入防冲突）
- `backend/main.py`：NodeRegistry fail_threshold 2→3（需连续 45s 失败才判离线）
- 新增 `frontend/src/views/cyber/__tests__/CyberDrillPanel.restore.test.tsx`（3 用例：
  切回后 Stop 可用 / 兑底轮询存活 / CoT+阶段从服务端补齐）

### 验证
- `npx tsc --noEmit` 0 错误；前端单测 55 passed（e2e/*.spec.ts 6 个文件级失败为
  Playwright spec 被 vitest 误扫的历史遗留，与本轮无关）
- 新增回归测试 3 passed
- `python -m pytest tests/infrastructure/nodes/test_node_registry.py tests/backend -q`
  → 82 passed
- 端边云探活实测：ARK /models 连发 10 次 10 通（133-738ms），一次抖动不再触发离线

---

## [MEMORY-REFACTOR-4] 2026-09-13 记忆可视化：/memory/stats 端点 + Monitor 记忆面板

### 背景
MEMORY_REFACTOR_REPORT 问题 5/报告的"前端 UI 与后端接口调整"——记忆子系统改完后，
需要让"记忆保持/向量/检查点"在界面可观测、可演示，且对外接口跟上。

### 修改
- **后端 `/api/v1/memory/stats` 端点**：
  - `MemoryStore.stats()`：暴露工作/情景/语义/向量/归档各层条数、检查点/快照数、
    持久化状态、auto_embed 状态与最近决策经验。
  - `CheckpointManager.stats()`：跨会话检查点总数。
  - `MemoryService.stats()` 与 `backend/routers/memory.py` 新增 `GET /api/v1/memory/stats`
    （先于 `/{session_id}` 注册避免路由吞并；沿用网关 X-API-Key 鉴权）。
- **前端**：
  - `frontend/src/services/api/memory.ts`：新增 `MemoryStats` 类型与 `memoryApi.stats()`。
  - `frontend/src/components/MemoryPanel.tsx`：记忆子系统面板——分层计数卡片+
    持久化/向量通道徽标+最近决策经验，5s 轮询。
  - `MonitorView.tsx`：接入 MemoryPanel；`index.css` 新增面板样式。

### 验证
- 新增 `tests/backend/test_memory_endpoints.py`（2 例）：stats 返回各层字段 + 无鉴权 401。
- Python 全量 **686 passed**；`npx tsc --noEmit` 0 错误；前端服务单测 26 passed。
- 端点实测：`GET /api/v1/memory/stats` 200（episodic_total/checkpoint_total/snapshot_total/
  persisted/auto_embed 均正确返回，与演练写入一致）。

### 本轮记忆改造素描（MEMORY-REFACTOR → 4）
- ① 单例统一（组合根一个 MemoryStore 注入 Cyber/Task 服务，消孤岛）✅
- ② 推理前唤醒接通（recall 注入 [memory_recall] prompt）✅
- ③ 持久化（JSON 落盘跨重启恢复）✅
- ④ 检查点/快照接线（每轮可恢复点 + 全局快照）✅
- ⑤ 向量通道激活（轻量确定性 embedding + auto_embed）✅
- ⑥ 前端/后端接口：/memory/stats + Monitor 记忆面板 ✅
- 🔲 后续可选：真实 embedding 模型、SQLite 后端、Replay/Purple 面板联动记忆轨迹

---

## [MEMORY-REFACTOR-3] 2026-09-13 激活向量检索通道（RRF 三通道名实相符）

### 背景
MEMORY_REFACTOR_REPORT 问题 2："向量通道是休眠的"——全项目无生产代码生成 embedding，
三通道 RRF 实际只有关键词+图两通道在工作，削弱"核心算法突破"评分。

### 修改
- **新增 `aegisos_agents/memory/vector/embedding.py`（HashingEmbedder + embed_text）**：
  轻量确定性字符 n-gram 哈希嵌入，纯标准库离线运行（演示/评测零依赖）；L2 单位范数、
  固定维度(默认 256)；接真实 embedding 模型时仅需替换实现、保持同签名。
- **MemoryStore 新增 `auto_embed` 开关（默认 False）**：
  - `write()`：开启时自动为缺失 embedding 的记忆生成文本向量（激活向量索引）；
  - `recall()`：开启时自动为触发词生成查询向量（激活向量召回）。
  - 默认 False 完全保持既有语义（仅显式 embedding 进向量），既有测试零破坏。
- **composition.py**：运行时可启动 `auto_embed=True`，让生产链路 RRF 三通道真正参与召回。

### 验证
- 新增 `tests/aegisos_agents/memory/test_vector_embedding.py`（4 例）：确定性/维度/归一化、
  语义相近更近、默认关闭、开启后向量通道激活并被 recall 召回。
- Python 全量 **684 passed**。
- 单点验证：auto_embed 演练 3 轮产生 6 条向量索引 + 3 条情景记忆；决策 embedding 可被
  向量 recall 命中。

---

## [MEMORY-REFACTOR-2] 2026-09-13 记忆持久化：跨重启恢复决策经验/检查点/快照

### 背景
MEMORY_REFACTOR_REPORT 问题 3："记忆不持久，跨重启全丢"——MemoryStore 全内存，`data/aegisos.db` 只管 session/task 仓储，"分布式记忆架构/跨会话记忆保持"名不副实。

### 修改
- **新增 `aegisos_agents/memory/persistence/`（MemoryPersistence）**：
  - 将情景记忆(长期决策经验)/工作记忆栈/检查点/快照序列化为 JSON 落盘，构造时从同文件恢复，实现跨重启记忆保持。
  - 语义知识库（ATT&CK/CVE）由数据集在启动时重建，不需落盘。
- **CheckpointManager / SnapshotManager 新增公开 dump()/restore_all()**：避免持久化触及私有态，保持封装。
- **MemoryStore 支持 `persistence_file` 参数**：启用时构造自动 `load`；新增 `save_to_disk()/load_from_disk()`；`MemoryStore.persistence` 未启用时为 None、save/load 返回 False（零破坏默认行为）。
- **composition.py**：组合根 MemoryStore 单例默认落盘到 `data/memory_store.json`（可用 `AEGIS_MEMORY_PERSIST_FILE` 覆盖）。
- **cyber_orchestrator.py**：`run_drill` 每轮结束（快照后）调 `memory.save_to_disk()`。

### 验证
- 新增 `tests/aegisos_agents/memory/test_persistence.py`：round-trip 恢复情景记忆/检查点/快照 + 未启用时 save/load 为 noop。
- Python 全量 **680 passed**（+3：2 持久化 + 1 唤醒/检查点回归）。
- 单点验证：3 轮演练落盘（2 决策经验 + 3 检查点 + 3 快照），新实例可完整恢复。

---

## [MEMORY-REFACTOR] 2026-09-13 记忆系统改造：单例统一 + 唤醒接通 + 检查点/快照接线

### 背景
依据 `developer/MEMORY_REFACTOR_REPORT.md` 诊断：记忆系统"压缩做得好，唤醒/持久化/容错/可视化没接成闭环"。本轮修复 P0（记忆孤岛、唤醒半闭环）与 P1（检查点/快照未接线）核心问题。

### 修改
- **统一 MemoryStore 单例（消除记忆孤岛）**：
  - `backend/core/composition.py`：组合根持有唯一的 `MemoryStore`（`self.memory_api`），统一注入 `CyberDefenseService(memory=...)` 与 `TaskService(memory=...)`；REST `/memory` 与演练/普通任务记忆读写同一实例。
  - 原 `CyberDefenseService` 内部 `memory or MemoryStore()` 自建临时实例的孤岛问题解决。
- **普通任务接入记忆（问题 6）**：
  - `backend/services/task_service.py`：`__init__` 新增可选 `memory`；任务成功/失败执行完写入 `MemoryPacket`（成功为 decision → 自动路由到情景记忆，供 recall 唤醒），失败不阻断主流程。
- **接通推理前唤醒（问题 1，recall 生产化）**：
  - `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`：
    - `run_drill` 每周紫队评审前调 `_build_recall_summary(memory, drill_id, target_range, round)`，经 `MemoryStore.recall()` 唤醒长期历史经验；
    - `run_purple_review` 新增可选参数 `memory_recall_summary`，critic prompt 注入 `[memory_recall]` 片段，与 `[prior_rounds_summary]` 并存——"压缩 + 唤醒"完整闭环。
- **接线检查点与快照（问题 5，容错恢复数据源）**：
  - `run_drill` 每轮结束后调 `memory.checkpoint.save(drill_id, {step_index, round, ...}, label=after_round_N)`（直接 save 而非 5 步间隔的 `checkpoint_cycle`，保证短演练也有可恢复点）与 `memory.snapshot_cycle(drill_id, {round, code})`。

### 验证
- 新增回归测试 `test_run_drill_recall_aware_and_checkpointed`（tests/aegisos_agents/planning/test_drill_memory.py）：每轮检查点、快照、recall 唤醒不抛错、决策入长期记忆。
- Python 全量 **677 passed**（含新增记忆/编排/服务测试 24 passed）；单点验证：3 轮演练产生 3 个可恢复检查点 + 3 条全局快照，最新检查点可 restore。

### 后续（报告第 5 步 ②③⑤，待做）
- ② 激活向量通道（embedding 生产源）；③ 记忆持久化（SQLite 落盘）；⑤ 前端记忆可视化（Memory API 新端点 + Monitor/Replay 面板）。

---

## [USABILITY-ROUND-2] 2026-09-12 CoT 时间线 + 真实 Agent 活跃态 + Graph 真图 + SSE 管道修复

### 修改
- **后端 CoT 事件**：`run_drill` 新增 `on_agent` 回调，红 3 / 蓝 4 / 紫 2 共 9 个 agent 调用点发 `drill.agent` 事件（SSE `drill_agent` + 全局总线）；演练开始/结束发 `drill.status`；`EventType` 新增 `DrillAgent`/`DrillStatus`。
- **全局 SSE 管道修复（Monitor/Canvas 无实时数据的共同根因）**：
  1. 后端 `/events` 的 `stream=all` 此前被当具体主题过滤，所有事件被滤光 → 特判 `all` 放行；
  2. 前端全局 SSE 用 `onmessage` 收不到命名事件帧（`event: <topic>`）→ 改为按主题 `addEventListener` 逐一监听并归一化入 store。
- **Monitor 真实活跃状态**：新模块 `agentActivity.ts` 从事件流派生 running/idle（含所属队伍、职责、最近活动时间、12s 衰减），顶部加演练运行状态条；静态注册表列表叠加实时态。
- **Graph 真图化**：SVG 分层有向图（BFS 分层布局、箭头、权重=线宽、熵>0.2=虚线、节点按 kind 着色、图例），点击节点联动详情；保留原列表与落点徽标。
- **Drill 面板 CoT 时间线**：消费 `drill_agent` 事件，显示"第 N 轮 · 红队 · 规划攻击链"滚动时间线 + 已运行时长计时；进度条头部补阶段描述。
- **过期快照自愈**：接管时服务端查无此演练（后端重启内存丢失）或明显僵死 → 快照自动清空回 idle，不再永久转圈。

### 验证
- Python 全量 666 passed；tsc 0 错误；前端单测 52 passed（6 个失败仍为 e2e 误扫 collect-only 历史遗留）；vite build 成功。
- e2e drill-direct：1 passed（11.8s，新代码后端 + mock 模式）。
- 后端已重启加载新代码（16:11 health OK，前端 SSE 已重连 `GET /events?stream=all` 200）。
- git：`84d0014` 基线 → `2c70747` 本轮改动（本地仓库，未推送）。

## [CYBER-DRILL-USABILITY] 2026-09-12 演练进度可见性 + Chat 接管 + 实时轮次

### 修改
- 阶段级 SSE 事件：`run_drill` 新增 `on_stage(stage, round)` 回调（cyber_orchestrator.py 红蓝紫调用点前触发）；路由层 `backend/routers/drill.py` 转 `drill_stage` SSE 事件；`service.drill` 透传。
- 前端 drill 面板（CyberDrillPanel.tsx）：消费 `drill_start`（回填真实 max_rounds）与 `drill_stage`；抽出共享 `handleDrillEvent`/`subscribeDrill` 供开始与接管复用；进度条显示"第 X/N 轮 · 当前阶段"。
- Chat 发起 → Cyber 接管：ChatView startDrill 成功后立刻写 running 快照；drill 面板挂载时 getDrill 查状态，running 补轮次+订阅 SSE，已结束直接展示终态。
- 运行中 get_drill 返回实时轮次：DrillRuntime 内存暂存 rounds（记录落盘前 rounds_executed 可见），修复 Chat 轮询报"演练执行超时"的根因。
- types.ts / cyber.ts：DrillEventName 增加 `drill_stage`。

### 验证
- `tsc -b` 0 错误；vite build 成功（91 modules）。
- 前端单测：8 文件 52 用例全过（e2e spec 被 vitest 误扫为 6 个 collect-only 失败，历史遗留非本次引入）。
- Python 全量：666 passed（旧基线 658，drill 相关 46 条单独复跑亦全过）。
- e2e drill-direct：1 passed（1.9m，mock 模式全链路收敛；此前一次失败为 Playwright worker 偶发崩溃 0xC0000409，复跑通过）。
- SSE 实测序列：drill_start → 3×drill_stage → drill_round → ... → drill_summary → drill_done。

## [CANVAS-OUTPUT-MODAL] 2026-09-10 协作产出按需弹窗展示

### 修改
- 移除任务卡片和最近活动卡片中的 JSON 产出摘要。
- 卡片仅显示任务、Agent、状态和“查看协作详情”入口。
- 点击任务后以模态弹层展示输入目标、Agent、最新产出和事件轨迹。
- 支持关闭按钮、遮罩关闭、Escape 关闭及移动端底部抽屉布局。

### 验证
- 浏览器：打开前 0 个弹窗，点击任务后 1 个弹窗。
- 浏览器：弹窗包含“协作与产出”和任务结果，首屏卡片无 JSON 堆叠。
- Canvas 专项：5 passed
- TypeScript 诊断：无错误
- `git diff --check`：通过

## [CANVAS-STRUCTURED-OUTPUT] 2026-09-10 协作产出结构化弹窗

### 修改
- 弹窗将协作信息拆分为输入目标、执行 Agent、结构化产出和执行轨迹四个区域。
- 结构化结果按键值展示，长数组和对象限制高度并支持滚动，不再把完整 JSON 塞入单个段落。
- 顶部显示事件数量和结果持久化状态，区分实时事件与后端最终产出。

### 验证
- 浏览器：任务详情显示 `target_range`、`assets` 等结构化字段。
- 首屏任务卡片不显示输出，仅保留“查看协作详情”。
- Canvas TypeScript 诊断：无错误；`git diff --check`：通过。

## [REALTIME-CANVAS-DEMO] 2026-09-10 新任务实时 Canvas 验收

### 验证
- Chat 创建任务 `31ea2934166443fbb7ebbdc1124c7976` 后，Canvas 切换到“全部”即可看到同一任务。
- Canvas 节点显示 `红队 · 已完成 · recon`，并显示任务产出摘要。
- REST 详情确认状态 `succeeded`，结果含两个演示资产（`10.0.0.5`、`10.0.0.10`）。
- 任务执行单测：1 passed；Canvas 专项：5 passed；`git diff --check`：通过。

## [CANVAS-DETAIL-MODAL] 2026-09-10 协作产出详情弹层

### 修改
- Canvas 默认不再常驻任务详情，避免协作信息与 DAG 节点堆叠。
- 点击任务节点后打开模态详情弹层，展示输入目标、执行 Agent、最新产出和事件轨迹。
- 支持关闭按钮、点击遮罩关闭和 Escape 关闭，移动端改为底部抽屉式布局。

### 验证
- 弹层交互：默认 0 个，点击任务后 1 个。
- 弹层内容：包含“协作与产出”和任务结果。
- Canvas 专项：5 passed
- TypeScript 诊断：无错误
- `git diff --check`：通过

## [CANVAS-OPERATIONS-DESK] 2026-09-10 Canvas 执行指挥台视觉改造

### 修改
- Canvas 首屏新增 LIVE/STANDBY 状态、任务队列、执行中、已完成和需关注概览。
- 新增最近活动流，优先呈现 Agent、任务目标和最新产出摘要。
- 保留完整任务依赖图作为流程地图，避免 DAG 节点独占首屏注意力。
- 增加桌面/移动端响应式布局、稳定截断和键盘焦点样式。

### 验证
- Canvas 专项：5 passed
- TypeScript 诊断：无错误
- 浏览器：首屏显示执行概览和 Recent Activity，横向无溢出。
- `git diff --check`：通过

## [DRILL-MARKDOWN-EXPORT] 2026-09-10 演练报告 Markdown 导出

### 修改
- 演练历史详情的报告导出改为调用 `/drill/{id}/report` 获取 Markdown 内容。
- 浏览器直接下载 `${drill_id}.md` 文件，移除历史工作区对 PDF/reportlab 的依赖。
- 增加 Markdown Blob 下载、文件名和报告接口调用回归测试。

### 验证
- 历史页专项：1 passed
- 前端全量：47 passed
- Vite 构建：成功
- 浏览器：真实演练详情显示“↓ 导出 Markdown”
- `git diff --check`：通过

## [CLEAN-AND-RERUN-DRILL] 2026-09-10 清理历史并生成完整五轮演练

### 修改
- 清理旧演练 JSON 与 Markdown 报告，仅保留本轮正式结果。
- 真实模型侦察为空时使用固定安全靶场基线资产继续演示，不执行真实网络扫描。
- 新演练完整保留红蓝紫三队每轮 Agent trace、输入和输出。

### 验证
- 正式演练：`drill-cef7887a`，5 / 5 轮，状态 `converged`。
- 每轮 Agent trace：9 个；红队 findings、蓝队 alerts/response actions、紫队判定均存在。
- 历史页：只保留 1 场、5 轮、1 场已收敛演练。
- 编排与报告专项：141 passed；历史页专项：1 passed；Vite 构建：成功。

## [DRILL-AGENT-TRACE] 2026-09-10 演练历史 Agent 产出追踪

### 修改
- 历史演练轮次接入红蓝紫三队已持久化的 `agent_trace` 数据。
- 每轮支持展开查看每个 Agent 的执行顺序、输入 Prompt 和结构化输出。
- 长 JSON 输出使用独立滚动区域，避免详情工作区被单条产出撑破。

### 验证
- 真实演练 `drill-e5447467` 展示 9 个 Agent 的输入输出。
- 历史页专项：1 passed
- 前端全量：47 passed
- Vite 构建：成功
- `git diff --check`：通过

## [DRILL-HISTORY-WORKSPACE] 2026-09-10 演练历史工作区

### 修改
- 左侧菜单新增“演练历史”一级入口。
- 新增演练历史工作区：统计场次/轮次/收敛数，按后端记录浏览演练，并加载红蓝紫轮次证据。
- 支持查看演练状态、目标网段、收敛结论和各队 findings/triage/actions/缺口摘要。
- 支持从历史详情导出演练 PDF 报告；Cyber Defense 原有历史区域保持兼容。

### 验证
- 历史页专项：1 passed
- 前端全量：47 passed
- Vite 构建：成功
- 浏览器：左侧入口、真实历史列表和 `drill-e5447467` 详情加载成功

## [REAL-DRILL-VALIDATION] 2026-09-10 真实模型攻防演练验收

### 修改
- Cyber Drill 真实模式统一使用火山方舟 `ark-code-latest` 编排。
- SSE 断线不再直接显示业务 Error，改为轮询同步；后端完成后自动恢复 `done` 和演练摘要。
- 真实演练结果支持历史记录加载和可视化恢复。

### 验证
- 真实单轮演练：`drill-e5447467`，目标 `10.0.0.0/24`，状态 `done`。
- 红队、蓝队、紫队链路均完成，生成 1 轮记录和紫队一致性审查结果。
- Python 全量：661 passed；前端全量：46 passed；Vite 构建：成功。
- Cyber Drill 专项：7 passed。

## [ARK-MODEL-VALIDATION] 2026-09-10 统一火山模型验收

### 修改
- 端、边、云三层默认模型统一为 `ark-code-latest`。
- 火山方舟三层默认 URL、OpenAI 兼容请求路径和认证方式保持一致，避免热重载恢复旧的 Ollama、Aegis Edge 或其他模型名。

### 验证
- device 场景：火山 device → edge → cloud 均成功，按级联置信度最终使用 cloud。
- edge 场景：火山 edge 成功，模型 `ark-code-latest`。
- cloud 场景：火山 cloud 成功，模型 `ark-code-latest`。
- 三层测试均未调用本地 Ollama 或本地 mock 节点。
- 后端专项：124 passed；前端全量：46 passed；Vite 构建：成功。

## [MULTI-PROVIDER-ROUTING] 2026-09-10 多 Provider 端边云适配

### 修改
- Provider 支持 Ollama、Aegis Edge、OpenAI 兼容、OpenAI、Anthropic 和自定义 JSON 接口。
- 节点支持独立配置推理路径、探活路径、认证 Header 和请求格式。
- OpenAI/Anthropic/自定义 HTTP 适配器可挂载到端、边、云任意层。
- 自定义认证 Header 原样传递 Key，Authorization 使用 Bearer，Anthropic 使用 `x-api-key`。
- 设置页支持 Provider 选择和连接参数配置，后端状态继续区分已保存、探活中、在线和离线。

### 验证
- Provider/Infra 专项：124 passed
- CloudNode OpenAI/Anthropic/custom 回归：48 passed
- 前端全量：46 passed
- Vite 构建：成功
- 当前用户配置实测：火山方舟路径返回 404，调度器按级联策略回退；需填写实际兼容 API 根路径与对应模型 ID。

## [INFRA-CONFIG-VALIDATION] 2026-09-10 端边云 API 配置验收

### 修改
- 设置页保存配置时同步调用 `/infra/configure`，端边云 URL、Provider、模型、能力和启用状态进入后端调度器。
- 后端配置接口复用真实 DeviceNode/CloudNode 工厂，不再把所有配置包装为演示节点。
- 设置页展示后端实际探活状态、模型和连续失败次数，区分“已保存”和“在线可用”。

### 验证
- 后端模式：`real`，Provider：`openai`，API Key：已识别且已持久化。
- Infra 专项：10 passed；前端全量：46 passed；Vite 构建：成功。
- 实测云端 URL 返回 `404 Not Found`，调度器正确回退到边侧 mock；本地隐私任务正确落到 device 层。
- 当前不是三层真实 API 全部成功：需将云侧 URL 配置为服务商实际 OpenAI 兼容根路径，并为端/边配置可访问的本地/边缘推理服务。

## [COLLABORATION-CANVAS] 2026-09-09 协作过程与 Agent 产出可视化

### 修改
- Canvas 任务节点显示执行 Agent 和最新 Agent 产出摘要，并在任务详情中聚合 Chat 消息与 SSE 执行事件。
- Chat 创建任务后将真实 `task_id` 绑定到助手消息，支持从 Canvas 回看对应生成内容。
- 贯通 `Task.result` 从协议、ORM 转换器、后端 REST 响应到前端类型，持久化结果可直接展示。
- 增加 Canvas 回归测试，覆盖 Agent 标识与持久化任务产出。

### 验证
- Canvas 专项：5 passed
- 前端全量：46 passed
- Vite 构建：成功
- 后端任务专项：64 passed
- `git diff --check`：通过

## [TASK-EXECUTION-LOOP] 2026-09-10 任务自动执行闭环

### 修改
- 任务创建持久化后异步调用 MockRuntime，按 payload 或目标语义选择 Agent。
- 发布 `agent.start` / `agent.finish` 事件，事件携带真实 `task_id` 和 Agent 产出。
- 执行成功或失败后分别回写任务 `result` 与终态，Canvas 可在刷新后恢复 Agent 和产出。
- 新增任务服务单元测试，覆盖后台执行、结果持久化和事件顺序。

### 验证
- 任务后台执行单测：1 passed
- 后端专项：64 passed
- 前端全量：46 passed
- Vite 构建：成功

## [DEMO-RECOVERY] 2026-09-08 核心文件恢复与演示兼容收尾

### 修复
- 恢复 `aegisos_agents/action/exploit_planner/agent.py`、`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`、`backend/mocks/cyber_provider.py` 三个核心文件。
- 普通无 round 的红蓝链路恢复旧兼容输出：静态资产、`planned` 攻击链和 `rp-1` 响应计划。
- CyberDrill 显式 `[round=N]` 继续启用多轮资产/批判演进，不影响演示收敛流程。

### 验证
- Python 全量：`654 passed`
- 前端：`44 passed`
- Vite 构建：成功
- Ruff：通过
- 外部 `langsmith/uuid_utils` pytest 插件冲突已通过隔离插件方式规避；项目测试本身通过。

## [DEMO-ENHANCEMENTS] 2026-09-08 比赛演示增强包

### 前端增强
- Canvas：空态一键加载完整红蓝紫演示流程，支持本地持久化、状态编辑和优先级调整。
- Graph：节点搜索、节点选中、关联边和权重详情。
- Monitor：节点状态自动刷新、更新时间和手动刷新入口。
- Replay：播放/暂停、上一步/下一步、进度滑块和当前事件高亮。

### 通信与数据增强
- TCP Message transport：可选共享密钥认证、失败重试和指数退避。
- CVE 数据集扩展到 10 条，覆盖 Linux 提权、F5 管理面、容器运行时和 HTTP/2。
- ATT&CK 数据集补充收集→外传→影响演示链（T1560/T1041/T1486）。

### 验证
- Python 全量：`658 passed`
- 数据/通信专项：`33 passed`
- 前端全量：通过
- Vite 构建：成功
- Ruff：通过

## [REAL-TASK-CANVAS] 2026-09-09 Canvas 接入真实后端任务

### 修改
- Canvas 挂载时按当前 Session 请求后端 `/tasks`，移除 localStorage 演示任务自动回填。
- “创建后端攻防流程”通过后端 Task API 创建五个带 `dependency` 的任务，再刷新当前 Session 任务列表。
- 前端 `taskApi.list()` 按后端实际数组响应解析，同时保留 `ListTasksResponse` 类型兼容导出。
- 后端 SQLite 启动初始化增加旧 `tasks` 表的 `payload/dependency/priority` 字段迁移，保留已有演示数据。

### 浏览器验证
- Chat 创建真实任务：`741052d07e8d4cb099bc0eacab428f91`。
- Canvas 切换后显示同一真实 task ID、目标、`running` 状态和后端任务详情。

### 验证
- Python 全量：`658 passed`
- 前端全量：`45 passed`
- Vite 构建：成功
- Ruff：通过

## [CYBER-DRILL] 2026-09-05 R8-R11 跨轮记忆/事件总线/端边云调度/无人干预演示（收尾）

### R8 · 跨轮记忆与上下文压缩（能力维度 a）
- `CyberOrchestrator.run_drill` 新增 `memory` / `memory_budget` 可选参数；每轮紫队评审后写决策记忆（working+episodic）并按 token 预算压缩（决策保留 + 细节 digest），下一轮紫队注入 `prior_rounds_summary` 摘要。
- `run_purple_review` 新增 `prior_rounds_summary` 可选参数（默认 None 零破坏）。
- `CyberDefenseService.drill` 透传记忆（默认注入服务持有 `_memory`）。
- 前端：轮次卡 🧠 mem 徽标 + 总结报告「Cross-Round Memory」区；`DrillRound.prior_rounds_summary` / `DrillSummaryResponse.memory_trace` 类型。
- 验证：后端 634 passed（+7），前端 tsc+vitest 43 passed；mock 实测 3 轮收敛携带前轮结论摘要，小预算触发 digest 压缩。

### R9 · 演练事件总线化（能力维度 b）
- `protocol.event.EventType` 新增 `DrillRound = "drill.round"`；`DrillRuntime` on_round 发布低熵增量事件（round/new_steps/new_issues/valid/converged/carry_forward_count/prior_summary，不含全量链/计划）。
- `GET /api/v1/events?stream=drill.round` 即可订阅演练心跳（复用既有 EventBus，未新造总线）。
- 验证：后端 638 passed（+4）；API 实测 3 轮事件 + carry 增量 0→1→2 + 跨轮摘要联动。

### R10 · 演练阶段 placement 联动（能力维度 c）
- `run_drill` 每轮为红/蓝/紫三阶段构造任务特征（延迟预算+隐私级别），复用 `scheduler.schedule()` 选定端/边/云层级，写入 `round_data.phase.{red,blue,purple}`（tier/model_id/reason）。
- 前端：轮次卡三阶段 tier 徽标（device 绿/edge 黄/cloud 蓝）+ 卸载理由 title。
- 验证：后端 642 passed（+4），前端 43 passed；实测 red→device、blue→edge、purple→cloud 跨轮稳定。

### R11 · 无人干预演示脚本 + 赛事材料收尾（能力维度 d/e）
- 新增 `tooling/scripts/drill_demo.ps1`：自动启动后端（默认 mock）→ POST /drill/start → 轮询至收敛 → 输出总结/跨轮记忆/落盘路径 → 自动停止自启后端；`-UseRealModel` 可选切真实 LLM。
- README 新增「CyberDrill 攻防演练演示」章节；档案「实测指南」补最终版。
- 验证：脚本实测全流程无人干预跑通（3 轮 converged + memory_trace + 落盘），退出码 0。

## [DOCS-STATUS] 2026-09-01 文档状态统一与演示范围收敛

### 修改
- 同步根总览、开发路线图、架构仪表盘及各域 AGENT 文档与当前实现。
- 统一测试基线：Python 594 passed，前端 24 passed，Vite build 成功。
- 明确演示版已完成的前端视图、端边云配置、节点/通信/Docker 沙箱基础。
- 明确真实 Neo4j/Qdrant、Docker 启动实测及生产端边云/Kubernetes/TLS 为可选或跳过项。

## [P7-DATA-CONTRACT] 2026-09-01 CVE 数据集与任务/拓扑契约补全

### 新增
- `data/datasets/cve/`：6 条可审计离线 CVE 样本及按资产服务/操作系统匹配查询。
- `data.api.query_cves()`：统一 CVE 查询公共边界。
- `tests/data/test_cve_knowledge.py`：CVE 数据集和匹配规则测试。

### 修改
- `protocol.scheduler.Task`：新增正式 `payload` 字段。
- 后端任务请求、响应、ORM 实体、转换器和服务贯通 `Task.payload`。
- `CyberDefenseService`：range 启动时将网络拓扑写入 GraphStore；无外部数据库时默认使用内存实现。
- 增加 range 拓扑持久化回归测试。

### 验证
- 数据、后端攻防和协议切片：`36 passed`

## [P7-H1-H7-BASE] 2026-09-01 Docker 基础交付与沙箱隔离

### 新增
- `infrastructure/delivery/deployment/docker/Dockerfile.backend`：非 root 后端镜像定义与健康检查。
- `infrastructure/delivery/deployment/docker/Dockerfile.frontend`：前端多阶段构建与 Nginx 静态服务镜像。
- `infrastructure/delivery/deployment/docker/docker-compose.yml`：后端/前端 Compose 编排，显式 API Key 注入、健康依赖和容器加固。
- `infrastructure/delivery/deployment/docker/nginx.conf`：SPA 回退、API 反代和 WebSocket 反代。
- `infrastructure/delivery/deployment/docker/sandbox/docker-compose.yml`：无宿主端口、internal 网络、只读根文件系统和 capability drop 的隔离靶场基础。
- `tests/infrastructure/delivery/deployment/test_docker_assets.py`：交付配置与安全约束测试。

### 已完成子项
- H1.1、H1.4、H7.1-H7.4、H7.6-H7.7、前端构建产物校验。

### 验证
- Docker Compose 配置解析成功（主部署和沙箱）。
- Docker 交付测试：`115 passed`（含现有基础设施测试）。
- 镜像构建因当前环境无法访问 Docker Hub 基础镜像仓库，暂未完成实际构建验证。

## [P7-E2-E3] 2026-09-01 场景二三 Mock 端到端验收

### 新增
- `tests/e2e/test_scenarios_2_3.py`：场景 2 长程攻击链（漏洞到横向移动）和场景 3 端边云隐私路由/降级/拓扑存储验收。

### 验证
- 场景二三测试：`2 passed`
- 当前结论：Mock 链路闭环；真实 Docker 靶场、工具容器和端边云网络联调仍待完成。

## [P7-H1-COMM] 2026-09-01 Message TCP 通信基础

### 新增
- `infrastructure/transport/communication/codecs/json.py`：严格 `protocol.Message` JSON Lines 编解码。
- `infrastructure/transport/communication/transport/tcp.py`：异步 TCP 点对点、显式目标广播和接收队列。
- `tests/infrastructure/transport/communication/test_tcp.py`：消息往返、TTL、广播和非法载荷测试。
- 沙箱 Compose：固定命名的 internal 网络，供容器间受控通信。

### 验证
- TCP 通信测试：`5 passed`
- 通信 ruff 检查：通过

## [P7-H1-H7-TOOLS] 2026-09-01 工具容器、HTTPS 站点与沙箱脚本

### 新增
- `infrastructure/delivery/deployment/docker/sandbox/docker-compose.yml`：补充 nmap、Metasploit、Zeek、Splunk tools profile；所有工具无宿主端口并加入 internal 网络。
- `infrastructure/delivery/deployment/docker/conf.d/aegisos.conf`：HTTPS 站点、TLS 1.2/1.3、SPA、API 和 WebSocket 反代配置。
- `tooling/scripts/sandbox.ps1`：沙箱 config/up/down 一键编排脚本。

### 已完成子项
- H1.2 工具容器化基础、H7.5 站点配置定义、H7.9 沙箱编排脚本。

### 验证
- 沙箱配置测试：`4 passed`
- Compose tools profile 解析成功。
- PowerShell 语法检查通过，Python Ruff 检查通过。
- Splunk 因需要运行时写入数据目录保留可写根文件系统，但仍启用 `cap_drop: ALL`、`no-new-privileges`、无宿主端口和 internal 网络。

## [DEMO-SCOPE] 2026-09-01 演示版范围收敛

### 已完成
- Canvas 演示版任务 DAG：依赖分层、状态筛选、选中详情和响应式布局。
- GraphService：graph.update 事件中的节点/边增删改均转换为 protocol 类型。
- 场景 2/3 Mock 端到端验收和 Message TCP 通信基础。

### 演示版跳过
- 真实端边云硬件/服务器联调。
- Kubernetes、TLS 证书实测、Gunicorn 生产部署和线上 Secret 管理。
- 真实 Docker 镜像拉取、容器启动及 Neo4j/Qdrant 服务集成实测。

### 验证
- Python 全量测试：`588 passed`
- 前端测试：`24 passed`
- 前端构建：成功

## [DEMO-CONFIG] 2026-09-01 前端端边云配置入口

### 已完成
- 配置页提供端侧、边侧、云侧的 API / Provider、API URL、Model name、能力标签和启用开关。
- 保存配置写入浏览器本地存储，并调用 `/api/v1/infra/configure` 同步本地演示调度器。
- 侧边栏保留唯一“运行配置”入口。

## [DEMO-FINAL] 2026-09-08 演示版任务收尾与剩余项核对

### 修改
- 活计划与路线图统一为“演示版完成，真实部署跳过”。
- M5 演示里程碑标记完成：场景 1/2/3 Mock 链路、benchmark 和评测能力均可演示。
- 补充 Neo4j/Qdrant 适配器惰性构造测试，验证无外部服务时不会提前联网。

### 当前仅剩外部环境验证
- 真实 Neo4j/Qdrant 在线集成测试。
- Docker 基础镜像拉取、镜像构建和沙箱工具真实启动。

### 演示版跳过
- 真实端边云硬件联调、Kubernetes、TLS 证书实测、Gunicorn 生产部署和线上 Secret 管理。

### 最终验证
- Python 全量：`654 passed`（使用 pytest-asyncio；隔离当前环境损坏的 langsmith/uuid_utils 外部插件）
- Python Ruff：通过
- 前端 Vitest：`44 passed`
- 前端 Vite build：成功
- 已修复普通 Mock 攻防链路与 CyberDrill 多轮演进之间的兼容性回归。

### 验证
- 前端测试：`24 passed`
- 前端构建：成功
- 配置 API：浏览器实测 `200`，保存按钮进入“已保存”状态。

## [P7-BASELINE] 2026-09-01 测试基线恢复与工程状态校准

> 补齐当前 Python 环境缺失的 `openai-agents` 与 `aiosqlite` 依赖，恢复全量回归；同步基础设施、前端、协议、数据和部署文档的实际状态。

### 验证
- Python 全量测试：`572 passed`
- 前端单元测试：`21 passed`
- 前端生产构建：`vite build` 成功
- 基础设施与工具测试：`123 passed`

### 当前未完成主线
- H1 Docker 沙箱靶场与安全隔离
- H7 Docker/Kubernetes/HTTPS 交付与端边云生产联调
- CVE/资产/场景数据补全、真实 Neo4j/Qdrant 集成测试
- 场景 2/3 端到端验收

## [P7-R2] 2026-08-26 端侧节点运行时 + 路由降级链修正

> 端侧(device)节点实体化：本机 Ollama 小模型适配器；同时修复调度器"缺失层取首个候选"的路由随机性。新增 21 个测试（10 DeviceNode + 11 路由桥接），调度器补 4 个降级回归。

### 新增
- `infrastructure/nodes/descriptor.py` — 追加 `InferenceResult` 统一返回契约（ok/text/node_id/tier/model_id/latency_ms/usage/error）+ `failure()` 工厂；失败绝不抛网络异常，为 R6 降级链铺路
- `infrastructure/nodes/base.py` — `BaseHttpNode` 公共底座（urllib JSON 收发 / 异常翻译 / 计时封装），R3 EdgeNode 直接复用
- `infrastructure/nodes/device/{__init__,device_node}.py` — `DeviceNode`：health()=GET /api/tags，infer()=POST /api/generate(stream=false)，含 `__main__` 真机冒烟块
- `tests/infrastructure/nodes/test_device_node.py` — 10 用例（happy path/参数透传/连接拒绝/超时/HTTP500/坏JSON/健康两态/构造校验/工厂）
- `tests/infrastructure/nodes/test_routing_bridge.py` — 11 用例：档案→select_nodes→to_scheduler_model→schedule 全链路，覆盖隐私路由端侧、超低延迟端侧、低延迟边侧、重活云侧、端离线降边、能力过滤绕过端侧、禁用档案排除等
- `tests/aegisos_agents/planning/test_scheduler.py` — 补 4 个缺失层降级回归

### 修改
- `aegisos_agents/planning/engine/scheduler/scheduler.py` — **行为修正**：四规则改为显式层级偏好链（隐私/超低延迟 device→edge→cloud；低延迟 edge→device→cloud；重活 cloud→edge→device），消除原实现"目标层缺失取 candidates[0]"的顺序随机性（重活可能在云缺时落到端侧）
- `docs/P7-端边云-任务切分与执行报告.md` — R2 开工前详细版 + 完工报告

### 验证
- `python -m pytest tests/infrastructure/ tests/aegisos_agents/planning/test_scheduler.py -q` → 48 passed
- 全量回归 → 474 passed / 1 failed（test_graph_store 基线预存，与本轮无关）
- ruff 全绿
- **真机冒烟**：Ollama 在线但 qwen2.5:0.5b 未拉取 → `[health] True` / `[infer] ok=False error=http 404`——精确验证了"节点不可用→失败结果而非异常"的降级契约；模型拉取后重跑冒烟块即可见 happy path

## [P7-R1] 2026-08-26 端边云任务线启动：节点档案与配置契约

> 端边云（赛题答题要求 c）补齐的第一块数据基础：三层节点统一描述类型 + 配置加载。纯数据层，零网络 IO，不影响任何现有模块行为。

### 新增
- `infrastructure/nodes/descriptor.py` — `NodeProfile`（Pydantic）+ `Tier/ProviderKind/PrivacyZone` 枚举；`load_node_profiles()` YAML 工厂（`${ENV_VAR}` 插值、未配置节点跳过并记录原因）；`select_nodes()` 过滤辅助；`to_registry_dict()`（R5 注册载荷投影）；`to_scheduler_model()`（桥接 engine.scheduler.Model）
- `tooling/configs/infrastructure.yaml` — 三节点档案（device_local 本机 Ollama / edge_server_01 服务器 / cloud_api OpenAI 兼容 API）+ 心跳参数段（R5 启用）；兑现 infrastructure/AGENT.md 承诺的配置位置
- `tests/infrastructure/nodes/test_descriptor.py` — 15 用例：构造校验/隐私域按 tier 推导/YAML 加载/环境插值/未解析跳过/注册投影/scheduler.Model 桥接/过滤辅助/真实配置冒烟
- `conftest.py`（仓库根）— pytest 将仓库根加入 sys.path

### 修改
- `pyproject.toml` — dependencies 增加 `pyyaml>=6.0`（infrastructure.yaml 加载为硬依赖）
- `infrastructure/__init__.py` · `infrastructure/nodes/__init__.py` — 新增包初始化（此前全域仅 api/ 有）
- `infrastructure/nodes/AGENT.md` — 修正配置路径冲突（nodes.yaml → tooling/configs/infrastructure.yaml，与域根 AGENT.md 对齐）；输出清单补 device 子模块
- `docs/P7-端边云-任务切分与执行报告.md` — 任务线 SSOT 档案（R0/R1 记录）

### 验证
- `python -m pytest tests/infrastructure/ tests/aegisos_agents/planning/test_scheduler.py tests/protocol -q` → 29 passed
- 全量回归 `python -m pytest -q` → 449 passed, 1 failed（`tests/data/test_graph_store.py::test_neo4j_store_missing_driver_raises` 为基线预存失败，git stash 验证与本轮无关）
- `python -m ruff check infrastructure/ tests/infrastructure/ conftest.py` → All checks passed
- `python -c "from infrastructure.nodes.descriptor import load_node_profiles; print(load_node_profiles())"` → 正常输出档案列表

## [P3.5] 2026-08-26 配置中心补全（environments + agents + models + prompts + deployment）

> 补齐 `tooling/configs/` 规划中的 5 个子目录/文件。零行为变更（settings.py 仅新增 EnvironmentConfig 字段，默认回退 dev，不影响现有模块）。

### 新增
- `tooling/configs/environments/dev.yaml` — 本地开发（关闭 auth/rate_limit，DB echo，DEBUG 日志，进程内存）
- `tooling/configs/environments/staging.yaml` — 预发布/演示（真库 Neo4j+Qdrant，INFO 日志，限流 300 rpm）
- `tooling/configs/environments/prod.yaml` — 生产（HTTPS/反代前置，WARNING 日志，限流 120 rpm）
- `tooling/configs/agents/default.yaml` — 3 通用 Agent + 11 攻防 Agent 元数据（id/role/capabilities/tier/default_model）
- `tooling/configs/models/default.yaml` — 3 provider（openai/azure/ollama）+ 4 model + 路由策略（按 tier）+ fallback
- `tooling/configs/prompts/default.yaml` — 14 个 Prompt 模板注册表（coder/reviewer/researcher + 11 攻防）+ jinja2 渲染器配置
- `tooling/configs/deployment.yaml` — dev/staging/prod 部署拓扑（节点规格/副本数/健康检查）+ 安全基线

### 修改
- `tooling/configs/settings.py` — 新增 `EnvironmentConfig` dataclass + `Settings.environment` 字段 + `AEGIS_ENV` 注入

### 验证
- `python -m ruff check tooling/configs/` → All checks passed
- `python -m pytest tests/tooling/ -q` → 11 passed
- `python -c "from tooling.configs.settings import settings; print(settings.environment.name)"` → `dev`
- `AEGIS_ENV=staging python -c "..."` → `staging`
- 现有所有 pytest（435 passed）无回归

### 设计原则
- 配置 schema 与现有 `defaults.yaml` 字段对齐（backend/cors/auth/database/logging/rate_limit/storage）
- 所有敏感值（DB 密码/API Key）yaml 中留空，由环境变量注入
- 不引入强制加载逻辑——environments/*.yaml 是文档化基线，未来按需 `pyyaml` 加载

## [P3.4.8] 2026-08-25 CI 启用 ruff 严格模式（continue-on-error 移除）

> 配套 P3.4.7x ruff baseline 治理（185→0 错），CI lint job 移除 `continue-on-error: true`，新增 ruff 错误即 fail。守护 P3.4 治理成果，防止回归。

### 修改
- `.github/workflows/ci.yml` — Ruff check step 移除 `continue-on-error: true`，注释更新为 P3.4.7x 完成状态

### 验证
- 本地 `python -m ruff check .` → All checks passed（0 错）
- push 后 CI lint job 应 fail on 任何新增 ruff 错误

## [P3.4.7e] 2026-08-25 ruff baseline 治理（I001+F401 自动修 18 错）

> 15 个 unsorted-imports 自动排序（ruff --fix 安全）+ 3 个 cyber_orchestrator.py 跨 try/except 块未用 SDK import 移除。零行为变更，pytest 全量 435 passed。

### 修改
- 全仓 15 个文件 `import` 块按字母序重排
- `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` 修 3 F401：
  - `OutputGuardrail` 移除（仅在 docstring 提及）
  - `add_trace_processor` 移除（未使用）
  - `SDKFunctionTool` 移除 → 改用 `import agents` 保留 SDK 可用性探测

### 验证
- `python -m ruff check . --select=I001,F401` → All checks passed
- `python -m pytest --tb=line -q` → **435 passed**（无回归）
- 整体 baseline: 61 → 43

## [P3.4.7d] 2026-08-25 ruff baseline 治理（E731 全部清零：tests）

> 1 个测试文件 `_asdict = lambda` 改为 `def _asdict(...)`。零行为变更，pytest 全量 435 passed。

### 修改
- `tests/e2e/test_scenario1.py` — E731

### 验证
- `python -m ruff check tests/ --select=E731` → All checks passed
- `python -m ruff check . --select=E731` → All checks passed（**E731 全清，14→0**）
- `python -m pytest --tb=line -q` → **435 passed**（无回归）

## [P3.4.7c] 2026-08-25 ruff baseline 治理（E731 observability 域 3 文件）

> 3 个 observability 文件 `_asdict = lambda` 改为 `def _asdict(...)` 形式。零行为变更，pytest 全量 435 passed。

### 修改
- `observability/measure/benchmark/runner.py` — E731
- `observability/measure/evaluation/scorers.py` — E731
- `observability/present/visualization/renderer.py` — E731

### 验证
- `python -m ruff check observability/ --select=E731` → All checks passed
- `python -m pytest --tb=line -q` → **435 passed**（无回归）

## [P3.4.7b] 2026-08-25 ruff baseline 治理（E731 aegisos_agents 域 3 文件）

> 3 个 aegisos_agents 文件 `_asdict = lambda` 改为 `def _asdict(...)` 形式。零行为变更，pytest 全量 435 passed。

### 修改
- `aegisos_agents/action/forensics/agent.py` — E731
- `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` — E731
- `aegisos_agents/planning/orchestrator/runtime.py` — E731

### 验证
- `python -m ruff check aegisos_agents/ --select=E731` → All checks passed
- `python -m pytest --tb=line -q` → **435 passed**（无回归）

## [P3.4.7a] 2026-08-25 ruff baseline 治理（E731 backend 域 7 文件）

> 7 个 backend 文件 `_asdict = lambda` 改为 `def _asdict(...)` 形式（消除 E731 lambda-assignment 违规）。零行为变更，pytest 全量 435 passed。

### 修改
- `backend/routers/stream.py` — E731
- `backend/routers/replay.py` — E731
- `backend/routers/ws.py` — E731
- `backend/routers/graph.py` — E731
- `backend/routers/sse.py` — E731
- `backend/mocks/runtime.py` — E731
- `backend/services/cyber_defense_service.py` — E731

### 验证
- `python -m ruff check backend/ --select=E731` → All checks passed
- `python -m pytest --tb=line -q` → **435 passed**（无回归）

## [P3.4.6] 2026-08-25 ruff baseline 治理（E402 全部清零：observability）

> 2 个 observability 文件 import 块中插 lambda 行下移到 import 末尾。同步修复 §10.1 违规（文件头不得有 `# changelog:`）。零行为变更。

### 修改
- `observability/present/visualization/renderer.py` — 修 3 E402（lambda 错位）+ §10.1 头注释修复
- `observability/measure/evaluation/scorers.py` — 修 2 E402（lambda + `json` 错位）+ §10.1 头注释修复

### 验证
- `python -m ruff check observability/ --select=E402` → All checks passed
- `python -m pytest --tb=no -q` → **435 passed**（无回归）
- E402 baseline: 65 → 0（修了 5）
- **E402 全部清零（142→0）**

## [P3.4.5] 2026-08-25 ruff baseline 治理（E402 第 5 批：tests 域）

> 1 个 e2e 测试文件 import 块中插 lambda 行下移到 import 末尾。零行为变更。

### 修改
- `tests/e2e/test_scenario1.py` — 修 13 E402（lambda 错位）

### 验证
- `python -m ruff check tests/e2e/test_scenario1.py --select=E402` → All checks passed
- `python -m pytest tests/e2e/ -q` → 10 passed
- E402 baseline: 78 → 65（修了 13）

## [P3.4.4] 2026-08-25 ruff baseline 治理（E402 第 4 批：aegisos_agents/orchestrator）

> 2 个 orchestrator 文件多 try/except import 块重组，把 _asdict lambda 推到所有 import 末尾。零行为变更。

### 修改
- `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` — 修 13 E402（5 个 import 块 + 1 个 lambda 错位）
- `aegisos_agents/planning/orchestrator/runtime.py` — 修 4 E402

### 验证
- `python -m ruff check aegisos_agents/planning/orchestrator/ --select=E402` → All checks passed
- `python -m pytest --tb=no -q` → **435 passed**（无回归）
- E402 baseline: 95 → 78（修了 17）

## [P3.4.3] 2026-08-25 ruff baseline 治理（E402 第 3 批：backend/mocks + backend/services）

> 2 个 backend 文件 import 块中插 lambda 行下移到 import 末尾，并把误插到 lambda 前面的 `typing.Any` 也归位。零行为变更。

### 修改
- `backend/mocks/runtime.py` — 修 17 E402（lambda + `typing.Any` 错位）
- `backend/services/cyber_defense_service.py` — 修 5 E402

### 验证
- `python -m ruff check backend/mocks/runtime.py backend/services/cyber_defense_service.py --select=E402` → All checks passed
- `python -m pytest tests/backend/ -q` → 12 passed
- `python -m pytest --tb=no -q` → **435 passed**（无回归）
- E402 baseline: 117 → 95（修了 22）

## [P3.4.2] 2026-08-25 ruff baseline 治理（E402 第 2 批：backend/routers）

> 5 个 FastAPI 路由文件的 import 块中插 lambda 行下移到 import 末尾。零行为变更。

### 修改
- `backend/routers/stream.py` — 修 4 E402（lambda + 1 typing.Any 错位）
- `backend/routers/replay.py` — 修 4 E402
- `backend/routers/ws.py` — 修 3 E402
- `backend/routers/graph.py` — 修 3 E402
- `backend/routers/sse.py` — 修 3 E402

### 验证
- `python -m ruff check backend/routers/ --select=E402` → All checks passed
- `python -m pytest tests/backend/ -q` → 12 passed
- `python -m pytest --tb=no -q` → **435 passed**（无回归）
- E402 baseline: 134 → 117（修了 17）

## [P3.4.1] 2026-08-25 ruff baseline 治理（E402 第 1 批：forensics）

> 把"lambda 行 + import 块"中插的 lambda 移到所有 import 之后。零行为变更，纯 import 顺序调整。

### 修改
- **`aegisos_agents/action/forensics/agent.py`** — 修 8 E402
  - 原：`_asdict = lambda ...` 插在 `from pydantic import BaseModel` 与 `from typing import cast` 之间
  - 现：lambda 移到所有 import 块之后

### 验证
- `python -m ruff check aegisos_agents/action/forensics/agent.py` → 0 E402（剩 1 E731 不在 P3.4.1 范围）
- `python -m pytest -k forensic -q` → 2 passed
- `python -m pytest --tb=no -q` → **435 passed**（无回归）

### P3.4 进度
- 总计 142 baseline → P3.4.1 修 8 → 剩 134 错误（跨 13 文件）
- 分批计划：P3.4.1 (1 文件) / P3.4.2 (4 文件 routers) / P3.4.3 (3 文件 mocks+runtime+renderers) / P3.4.4 (2 文件 e2e+orchestrator) / P3.4.5 (3 文件 services+others)

## [P3.3] 2026-08-25 CI/CD 流水线（spec 09 §开发流程 + 11 §7 低熵铁律自动化）

> 三步闭环：lint（含低熵铁律静态检测） + typecheck + test 矩阵，PR/Push 自动跑。

### 流水线
- **`.github/workflows/ci.yml`** — GitHub Actions 3 jobs：
  - `lint`：ruff check（baseline `continue-on-error` 汇报不 fail）+ `check_no_broadcast.py --strict`（违规即红 CI，spec 04 §16 / 11 §7 守卫）
  - `typecheck`：mypy strict，路径 `protocol aegisos_agents backend`（修旧 `agents` 路径 bug）
  - `test`：pytest 矩阵 3.12 / 3.13，`AEGIS_USE_MOCK=true` 零外部依赖
  - `concurrency.cancel-in-progress: true` PR 多 commit push 节流
  - `actions/cache@v4` 按 `pyproject.toml` hash 缓存 pip
  - `permissions: contents: read` 默认最小权限
  - `actions/upload-artifact@v4` 失败时上传 pytest logs
- **触发条件**：`push` 到 `main`/`prd` + `pull_request` 到 `main`/`prd`

### Makefile 增强
- **`.PHONY` 追加**：`ci check broadcast-check`
- **`typecheck`**：修路径 `agents` → `aegisos_agents`（旧 R1 迁名残留 bug）
- **`broadcast-check`**：`python tooling/scripts/check_no_broadcast.py --strict`（与 CI 同源）
- **`check`**：lint + broadcast-check + test 一键复现 CI
- **`ci`**：提示指向 `.github/workflows/ci.yml` 和本地 `make check`
- **`lint`**：注释 P3.3 baseline（158 错误）— `continue-on-error` 与 CI 对齐

### 验证（本地复现）
- `python -m ruff check .` → 142 错误（baseline，CI `continue-on-error` 汇报；`pyproject.toml` `extend-exclude` 已排除 `.claude`/`.github`/`agents`/`api`/`docs`/`frontend`/Makefile）
- `python tooling/scripts/check_no_broadcast.py --strict` → `[OK] No broadcast violations`
- `python -m pytest --tb=no -q` → **435 passed in 15.73s**（与 P3.2 同基线，无 CI 引入回归）

### 待办（commit 后跟踪）
- **P3.4 ruff baseline 治理**：142 错误分类（74 E402 import 顺序 / 14 E731 lambda / 11 F821 undefined name / 9 B008 FastAPI Depends / 9 B007 loop var / 散点 StrEnum/UP/SIM 等），按 §11 AI 范围分批专项修，每批 ≤1 域 ≤8 文件

### 配套文档
- `developer/plan.md` §1/§2/§7 同步 P3.3 + P3.4 待办
- `tooling/AGENT.md` 末尾「P3.3 CI/CD」段（CI 流水线说明 + Makefile 目标映射）

## [P3.2] 2026-08-25 Router 业务接入（spec 04 §16 低熵路由 + 13 §5 DI 端口）

> 把抽象的 `RouterAPI` Protocol 落到 `CyberOrchestrator`：11 个 Agent 拓扑 + Top-K 稀疏路由 + 防御性守卫。

### 接口落地
- **`aegisos_agents/api/__init__.py`** 新增 `RouterAPI` Protocol（`select_targets` / `get_topology`）；`__all__` 同步
- **`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`** 实现：
  - 导入 `route as _route, Graph, GraphNode, NodeKind, Message, NodeRef`
  - `_build_topology()`：11 个 Agent 映射 GraphNode
  - `select_targets(capability, top_k=3)`：router Top-K 稀疏路由
  - `get_topology()`：暴露给前端 / observability
  - `assert_target_routable()`：防御性守卫（Capability 必须存在于拓扑）
  - `_create_red/blue_agent_executor`：AP3 Goal 模式前置守卫

### 测试（9 用例 / `tests/aegisos_agents/planning/test_cyber_router_integration.py`）
- RouterAPI Protocol 签名（`select_targets` / `get_topology` 存在性 + callable）
- `select_targets` Top-K 截取（top_k=3 必 ≤3 节点；top_k=0 → 全选；不传 top_k → 默认 3）
- 未知 capability → `select_targets` 返回 `[]`
- `get_topology()` 11 节点（含 11 Agent、kind=Agent、capability 覆盖红蓝紫 + 工具/感知/规划/编排）
- 已知 target 可路由 / 未知 target `assert_target_routable` 抛 `CapabilityError`
- 红/蓝 executor 路由守卫：篡改 capabilities 路由选不到 → 走 fallback

### 验证
- `python -m pytest tests/aegisos_agents/planning/test_cyber_router_integration.py -q` → **9 passed**
- `python -m pytest --tb=no -q` → **435 passed**（与 P3.1 同基线，无 P3.2 引入回归）

### 零协议入侵
- `aegisos_agents/api` 仅导入 `protocol/{graph,message}.py`
- 业务侧 0 内部子包引用（`aegisos_agents/planning/engine` 等仍通过 api/ 暴露）

## [R1] 2026-08-25 Protocol → Pydantic 迁移（R1.1-R1.7 全部完成）

> 长期债务清理：所有 `protocol/*.py` 迁移到 Pydantic BaseModel，业务代码用 `_asdict` shim 兼容。

### R1.1 — message.py
- `protocol/message.py` 迁移完成（NodeRef/Header/Message + `to_dict/from_dict` 兼容 shim）。

### R1.2 — event.py
- `protocol/event.py` 迁移完成（Event + `to_dict/from_dict` 兼容 shim）。

### R1.3 — scheduler.py
- `protocol/scheduler.py` 迁移完成（TaskStatus/RetryPolicy/RollbackPlan/Task/Plan/Schedule + `to_dict/from_dict` 兼容 shim）。10 个 import 站点同步。

### R1.4 — agent.py
- `protocol/agent.py` 迁移完成（AgentStatus/Agent + `to_dict/from_dict` 兼容 shim）。

### R1.5 — 5 文件批量
- `protocol/{memory,tool,heartbeat,sync,graph}.py` 全部迁移：MemoryPacket / ToolCall/ToolResult/ToolSpec / Heartbeat / SyncStatus+SyncPacket / NodeKind+GraphNode+GraphEdge+Graph+Route+GraphDiff。

### R1.6 — cyber.py（8 攻防类型）
- `protocol/cyber.py` 迁移完成：Asset/VulnFinding/AttackStep/AttackChain/Alert/DefenseAction/ResponsePlan/ThreatIntel。AttackChain/ResponsePlan Pydantic 校验自动递归子对象。
- 修 `aegisos_agents/action/ir_planner/agent.py`：原 `[a.model_dump() for a in result.actions]` 转 dict 保持接口兼容，改为直接传对象让 Pydantic 校验为 `DefenseAction`。
- 6 个测试由 `plan.actions[0]["kind"]` 改为 `.kind`（Pydantic 属性访问），1 个 e2e 测试同步。

### R1.7 — 业务代码 asdict 兼容 shim
- 14 个文件 `from dataclasses import asdict` 替换为 `_asdict = lambda obj: obj.model_dump() if isinstance(obj, BaseModel) else obj`：aegisos_agents/forensics/agent.py, aegisos_agents/planning/orchestrator/{cyber_orchestrator,runtime}.py, backend/mocks/runtime.py, backend/routers/{graph,replay,sse,stream,ws}.py, backend/services/cyber_defense_service.py, observability/measure/benchmark/runner.py, observability/measure/evaluation/scorers.py, observability/present/visualization/renderer.py, tests/e2e/test_scenario1.py。
- 删除 `observability/inspect/replay/player.py` 中死代码 `from dataclasses import asdict` 导入。
- 修 `backend/mocks/runtime.py` 脚本残留 `as _asdict` 语法。

### 验证
- `python -m pytest --tb=no -q` 结果：**380 passed, 4 failed, 2 errors**（R1 范围内 0 回归）。
- 4 failed 全部是预存在 AP2 ReAct 集成未完成任务（`hunt_react`/`detect_react` 方法未实现 + `ReactMode` final_output 未填 + e2e 依赖）：`test_threat_hunt_runs_react_with_attck_query`、`test_threat_hunt_react_handles_empty_alert_list`、`test_react_mode_supports_execution_api_object`、`test_five_agents_complete_react_tool_loops_with_auditable_traces`。
- 2 errors 是已知的 pre-existing collection errors（`tests/aegisos_agents/planning/test_cyber_tracing.py`）。
- 与 R1.2 基线（383 passed + 3 errors）对比：失败/错误数一致，**R1 迁移零回归**。

## [AP2.8] 2026-08-25 ReAct 集成收尾（4 fail → 0）

> 把 R1 阶段遗留的 4 个 ReAct fail 测试补齐。涉及 Pydantic 迁移后的 `dataclasses.replace` 不可变问题。

### AP2.8.1 — `ThreatHuntAgent.hunt_react` 实现
- 修改 `aegisos_agents/action/threat_hunt/agent.py`：新增 `hunt_react(alerts, executor, *, thinker, max_iterations, stop_on_tool_error) -> ReactResult[list[dict]]`。模式：先以 `query_attck_kb(technique_id)`（permission=knowledge.read）查询 ATT&CK，再用 `_run()` 生成假设并转为 dict。`alerts` 为空时用空 `technique_id`（边界用 `alerts[0].technique if alerts else ""`）。

### AP2.8.2 — `ReactMode` Pydantic 兼容
- 修改 `aegisos_agents/perception/reasoning/strategies/react_mode.py`：`_execute_action()` 中补齐 `call_id` 路径原用 `dataclasses.replace(result, call_id=action.call_id)`，但 `ToolResult` 已迁 Pydantic BaseModel（不可变 dataclass.replace 不支持），改为 `result.model_copy(update={"call_id": action.call_id})`。移除未用 `replace` import。

### 验证
- `python -m pytest --tb=no -q --ignore=tests/aegisos_agents/perception/test_reflection.py --ignore=tests/aegisos_agents/tools/test_runtime.py` 结果：**384 passed, 2 errors**。
- 4 fail 全部转 0：threat_hunt（2）+ ReactMode（1）+ e2e 五 Agent（1）。
- 2 errors 仍是 R1 阶段已记录的 pre-existing `NodeRef` collection error。

## [P3 收尾] 2026-08-25 2 collection error + 1 fail 清零（415 passed）

> 把 R1 阶段遗留的 2 collection error（`NodeRef` 模块路径错 + pytest 同名 test 冲突）和 1 fail（Windows monotonic 精度）一并清掉。

### 1. `NodeRef` import 路径错（lifecycle）
- 修改 `aegisos_agents/tools/runtime/lifecycle.py`：`from protocol.scheduler import NodeRef` → `from protocol.message import NodeRef`。
- 原因：`NodeRef` 在 R1.1 message.py 迁移后就移到了 `protocol.message`，lifecycle 还在引旧路径。

### 2. 同名 test 文件 pytest 冲突
- `tests/aegisos_agents/memory/test_reflection.py` 与 `tests/aegisos_agents/perception/test_reflection.py` 同名，pytest 在收集阶段把它们识别为同一 module 报 `imported module 'test_reflection' has this __file__ attribute` 冲突。
- 修法：`git mv tests/aegisos_agents/perception/test_reflection.py tests/aegisos_agents/perception/test_reflection_strategies.py`（reflection 是 perception 语义上下文，perception 侧改名更合适）。

### 3. Pydantic 迁移后 fixture 字段名错（cyber_tracing）
- `tests/aegisos_agents/planning/test_cyber_tracing.py::sample_plan` fixture 给 `actions=[{"action": "isolate", "target": "host-1"}]` dict 列表，Pydantic `ResponsePlan.actions` 期望 `list[DefenseAction]`，字段为 `action_id`/`kind`/`target`。
- 修法：导入 `DefenseAction`，fixture 改为 `[DefenseAction(action_id="a-1", kind="isolate", target="host-1")]`。`rollback` 字段查 `ResponsePlan.rollback: dict[str, Any]` 保持 dict 不变。

### 4. Windows monotonic 精度 fail（test_runtime）
- `tests/aegisos_agents/tools/test_runtime.py::test_check_timeout`：start 立即设 `last_heartbeat=time.monotonic()`，再 `check_timeout(max_sec=0.01)` → elapsed=0 不超时。
- 原因：Windows `time.monotonic()` 精度约 15ms，`start` 之后 `elapsed` 可能为 0 < 0.01。
- 修法：start 后加 `time.sleep(0.03)` 留出余量。注释说明 Windows 精度。

### 验证
- `python -m pytest --tb=no -q` 结果：**415 passed, 0 failed, 0 errors**。
- 历史阶段对比：R1 阶段 380 passed + 2 errors → AP2.8 后 384 passed + 2 errors → **P3 收尾 415 passed + 0 + 0**。

## [P3.1] 2026-08-25 低熵广播静态检测脚本（spec 04 §16 / 11 §7 铁律守卫）

> 把 `00 §G3/§NG3` / `04 §16` / `11 §7` 三处规范的「禁全广播·低熵稀疏路由」铁律落到静态检测脚本，作为 CI 守卫与代码评审参考。
> 当前业务域扫描 0 违规：所有节点遍历均通过 `json.dumps(拓扑)` 序列化给 LLM 的合法路径，无运行时广播。

### 1. 检测脚本 `tooling/scripts/check_no_broadcast.py`
- **AST 优先**：先 `ast.parse` 校验语法，跳过语法错误文件（避免 lint 误报）。
- **模式匹配 4 类违规**：
  1. 显式总线广播：`bus.broadcast` / `eventbus.send_all` / `publish_all`
  2. 遍历 `graph.nodes.values()` 后调 `dispatch/send/publish/forward`
  3. 遍历 `topology/graph.nodes:` 后调 `dispatch/send/publish/forward`
  4. 裸 `dispatch(...)` 调用无 `node_refs=` 目标过滤
- **合法豁免**：同行含 `json.dumps(` / `active_subgraph(` / `.nodes.keys()` / `.nodes.items()` 不算违规（序列化给 LLM / 子图构造 / 状态聚合）。
- **目录排除**：`__pycache__` / `.venv` / `.git` / `tests` / `tooling` / `protocol`（测试可临时遍历但生产不可）。
- **双模式**：默认仅警告（exit 0），`--strict` 模式违规即 exit 1（CI 用）。
- **CLI**：`python3 tooling/scripts/check_no_broadcast.py [--path DIR] [--strict]`。
- **跨盘符容错**：`os.path.relpath` 在 Windows tempfile (C:) vs ROOT (D:) 抛 ValueError，回退绝对路径。
- **GBK 兼容**：报告用 ASCII `[OK]/[FAIL]`，避免 Windows 子进程解码崩溃。

### 2. 测试 `tests/tooling/test_check_no_broadcast.py`（11 用例）
- 干净仓库 0 违规（默认 + `--strict`）
- 显式 `bus.broadcast` / `bus.send_all` / `nodes.values()` 循环 dispatch 都被检测
- 合法豁免：`json.dumps(拓扑)` / `active_subgraph()` 不被误报
- `--strict` 模式违规 exit 1
- 语法错误文件跳过
- 不存在路径 exit 2
- 纯注释行不报
- 默认排除 `tests/` 目录

### 验证
- `python -m pytest --tb=no -q` 结果：**426 passed, 0 failed, 0 errors**（415 + 11 新增）。
- `python tooling/scripts/check_no_broadcast.py` 业务域扫描：**0 违规**。

## [P3.2] 2026-08-25 低熵路由器业务接入（spec 04 §16 / 11 §7 铁律履行）

> P3.1 静态检测暴露漏洞：`aegisos_agents.planning.engine.router.route()` 历史仅 test 引用，业务零调用。P3.2 把稀疏路由真正接到编排器目标选择路径，履行「禁全广播」铁律。

### 1. 公开接口 `aegisos_agents/api/__init__.py`
- 新增 `RouterAPI` Protocol：`select_targets(message, capability) -> list[NodeRef]` + `get_topology() -> Graph`。
- 文档明示 spec 04 §16 约束（Top-K<=3，绝不遍历全图 dispatch）。

### 2. `CyberOrchestrator` 实现（`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`）
- `_build_topology()`：把 11 个攻防 Agent 映射为 GraphNode（红 4 + 蓝 5 + 紫 2，capability = agent_name，success_rate=0.5、latency=0.0）。
- `select_targets(...)` / `get_topology()`：委派给 `route()`，符合 RouterAPI 签名。
- `assert_target_routable(capability, target)`：防御性守卫，目标不在 Top-K 抛 `ValueError`。
- `_create_red/blue_agent_executor`（AP3 Goal 模式）：在 `agent_name` 分发前调用守卫 → 阻断任何"绕过路由直接调用 _run"的违规路径。
- 守卫触发条件：目标节点仍在图内但 capability 被改 → 路由选不到 → raise。节点被 pop 则视为"启动时未注入该 Agent"放行（兼容 Mock 测试场景）。

### 3. 测试 `tests/aegisos_agents/planning/test_cyber_router_integration.py`（9 用例）
- `RouterAPI` 方法签名（`hasattr` × 2）
- `select_targets("recon")` 返回 Top-K 包含 recon 节点
- 不同 capability 命中不同主目标
- 未知 capability 返回空（非广播、非错误）
- 拓扑含 11 个攻防 Agent
- 已知 Agent `assert_target_routable` 不抛
- 未知 target 抛 `ValueError("not in Top-K")`
- 红队 executor：篡改 capability 后抛 `ValueError`（守卫生效）
- 蓝队 executor：同上

### 验证
- `python -m pytest --tb=no -q` 结果：**435 passed, 0 failed, 0 errors**（426 + 9 新增）。
- `python tooling/scripts/check_no_broadcast.py`：**0 违规**（业务域持续合规）。

## [AP4] 2026-08-17 Ask 范式（人机协同 / HITL，7 子任务全完成）

> 模式：暂停提问 + 超时降级。在关键决策点（破坏性操作前 / 严重度超阈值 / 不确定时）暂停向人类提问，
> 无人值守或超时则按各 Agent 指定的安全默认自动降级（保证攻防链不阻塞）。

### AP4.1 — Ask 模式核心（perception）
- 新增 `aegisos_agents/perception/reasoning/strategies/ask_mode.py`：`AskMode` 混入类 + `AskRequest`/`AskResponse`/`AskTimeoutError` 数据类 + `AskHandler`(ABC)/`MockAskHandler`(测试)/`AutoAskHandler`(默认无人值守即时降级) + `severity_at_least()` 严重度比较。
- `AskMode.ask_human()`：发布 `HumanInputRequired` → 调 handler 取回答（超时/异常均走降级）→ 发布 `HumanResponse`。handler/eventbus 经 `set_ask_handler`/`set_event_bus` 注入（duck typing，不反向依赖 planning）。

### AP4.2 — ir_planner 接入（破坏性操作前确认）
- 修改 `aegisos_agents/action/ir_planner/agent.py`：继承 `AskMode`，新增 `plan_response_with_human_check()`——含 isolate/block 动作时暂停提问，超时降级为仅 monitor。

### AP4.3 — critic 接入（严重度阈值请求）
- 修改 `aegisos_agents/action/critic/agent.py`：继承 `AskMode`，新增 `critique_with_human_check()`——severity ≥ 阈值（默认 high）时请求人工复核，超时确认结论。

### AP4.4 — threat_hunt 接入（不确定时澄清）
- 修改 `aegisos_agents/action/threat_hunt/agent.py`：继承 `AskMode`，新增 `hunt_with_human_check()`——置信度低于阈值时暂停澄清，可选缩小范围重试。

### AP4.5 — 事件补充
- 修改 `protocol/event.py`：`EventType` 新增 `HumanInputRequired = "human.input.required"` / `HumanResponse = "human.response"`，并在 `developer/specs/07_EVENT_SPEC.md` 双登记。

### AP4.6 — 前端 ChatView 人机交互消息渲染
- 修改 `frontend/src/protocol/types.ts`：`EventType` 联合类型补充两个人机协同值。
- 修改 `frontend/src/lib/store/index.ts`：新增 `HitlPayload` 载荷类型 + `ChatMessage.hitl` 字段。
- 新增 `frontend/src/services/api/human.ts`：`humanApi.submitAnswer()`（尽力回传人类回答，端点未实现时静默失败）。
- 修改 `frontend/src/controllers/events.ts`：订阅 `human.input.required`/`human.response`，驱动 ChatView 卡片（同源 task 请求→响应原位更新为单卡片）。
- 修改 `frontend/src/views/chat/ChatView.tsx`：渲染 `HitlCard`（提问+选项按钮+结论/超时降级徽章）。
- 修改 `frontend/src/index.css`：人机协同卡片样式（`.chat__hitl*`）。

### AP4.7 — 测试
- 新增 `tests/aegisos_agents/perception/test_ask_mode.py`：Mock handler 回答 / 超时降级 / 无 handler 自动降级 / 事件发布 / severity_at_least / 新事件类型。
- 新增 `tests/aegisos_agents/action/test_ir_planner_ask.py` / `test_critic_ask.py` / `test_threat_hunt_ask.py`：确认/降级/超时/取消/缩小范围重试等 HITL 路径。

### 编排器接线
- 修改 `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`：移除与 `action/` 重复的 `ThreatHuntSDKAgent`/`IRPlannerSDKAgent`/`CriticSDKAgent`，复用规范 `ThreatHuntAgent`/`IRPlannerAgent`/`CriticAgent`（使 AP4 HITL 在链中生效）；新增 `run_blue_chain_with_human_check()` / `run_purple_review_with_human_check()`，支持注入 `ask_handler`/`eventbus`。

### 质量门禁
- Python 语法 `py_compile` 全绿（7 源码 + 4 测试）；AskMode 逻辑隔离烟测通过。
- 前端 `tsc --noEmit` 仍需在可用环境验证（本机无 Python；前端 node 可用，已尽量保持类型一致）。
- 全量 pytest 需在 macOS/容器运行（依赖完整 venv）。

### 注意（跨目录）
- 本次触及 `frontend/` 与 `developer/`（`07_EVENT_SPEC.md`/`plan.md`/本 CHANGELOG），按 `07_EVENT_SPEC.md §2` 事件双登记规范与 `plan.md` 维护规则要求执行；`aegisos_agents/AGENT.md` 默认将 `frontend/`/`developer/` 列为禁止修改目录，此处为用户显式指派 AP4.6 + 规范强制要求，已最小化改动并请负责人复核。

## [P2] 2026-08-06 H2 数据层接入 — Neo4j + Qdrant + 记忆子系统对接

### 新增（data 域）

- `data/models/graph_store.py`：`InMemoryGraphStore`（默认）+ `Neo4jGraphStore`（`neo4j>=5` 惰性加载）—— 网络拓扑（`protocol.cyber.Asset` 节点 + 带标签关系）+ ATT&CK 知识（Technique 节点 + 关系边）
- `data/models/vector_store.py`：`InMemoryVectorStore`（默认，余弦检索）+ `QdrantVectorStore`（`qdrant-client>=1.8` 惰性加载）
- `data/models/registry.py`：`create_graph_store(mode)` / `create_vector_store(mode)` 工厂
- `data/datasets/attck/knowledge.py`：ATT&CK 数据集（~36 技战术 + contains/precedes/uses/targets 关系边，保留原 8 条种子）
- `data/api/__init__.py`：新增 `GraphStoreAPI` / `VectorStoreAPI` Protocol + `create_graph_store` / `create_vector_store` / `load_attck_dataset` 工厂（增量，既有接口不变）

### 修改（aegisos_agents/memory + backend + configs）

- `memory/vector/store.py`：`VectorMemory(backend)` 后端注入（默认内存实现不变）
- `memory/semantic/store.py`：`SemanticMemory(graph_backend)` 图后端注入（空后端 seed 预载数据集）
- `memory/memory_store.py`：`MemoryStore(vector_backend, graph_backend)` 可选注入
- `backend/core/composition.py`：按 `settings.storage` 装配存储后端（默认 in_memory）
- `tooling/configs/settings.py` + `defaults.yaml`：新增 `storage` 配置段（graph_mode/vector_mode/neo4j_*/qdrant_*）
- `pyproject.toml`：新增 `[project.optional-dependencies] storage = ["neo4j>=5", "qdrant-client>=1.8"]`

### 测试

- 新增 7 个边界用例：错误 `call_id` 防串线、非法执行器返回值、后续思考失败时的
  轨迹保留、工具输出提示注入数据化、空资产/空告警输入和最大迭代保护。
- AP2 定向测试 25 个、action 30 个、perception 73 个、E2E 10 个全部通过。
- `react_mode.py` 与 `react_support.py` 定向覆盖率均为 100%；新增测试的 Ruff 和
  格式检查通过。

## [AP2.7] 2026-08-12 ReAct 工具调用循环验证

### 测试

- 新增 `tests/e2e/test_react_tool_loop.py`，通过确定性的 `ExecutionAPI` 测试替身，
  串联验证 recon、vuln_correlator、detector、threat_hunt、forensics 五个 Agent。
- 验证每个 Agent 均完成 think→act→observe→finish，且工具顺序、权限、`call_id`、
  观察结果、最终思考与跨阶段领域输出可审计。
- 验证工具观察以 `UNTRUSTED_TOOL_OUTPUT_JSON` 数据标记进入最终归纳阶段，避免把
  工具输出当作可信指令。
- action 26 个测试、perception 70 个测试、E2E 10 个测试通过；新增文件的 Ruff、
  格式检查及定向 mypy 检查通过。

## [AP2.2-AP2.6] 2026-08-12 五个攻防 Agent 接入 ReAct

### 新增

- `aegisos_agents/action/react_support.py`：共享 ReAct 适配器，默认执行一次角色工具并
  将成功观察交给结构化 Agent 归纳；支持注入自定义 thinker 扩展多工具循环。
- recon、vuln_correlator、detector、threat_hunt、forensics 分别新增
  `scan_react`、`correlate_react`、`detect_react`、`hunt_react`、
  `investigate_react`，原同步方法保持兼容。
- 工具调用复用 `ExecutionAPI` / `ToolCall` / `ToolResult`；默认工具失败立即停止，
  工具输出在进入模型 prompt 前显式标记为不可信 JSON 数据。
- Forensics 的 `ResponsePlan` 序列化支持真实 `DefenseAction` dataclass。

### 测试

- 新增 `test_react_agents.py` 7 个用例，覆盖五 Agent 默认工具映射、领域输出转换、
  工具失败和自定义 thinker 备选工具路径。
- action 26 个测试、perception 70 个测试通过；六个目标模块定向覆盖率 92%，
  `react_support.py` 覆盖率 100%。
- AP2.7 的 H1 真实沙箱端到端集成仍待完成。

## [AP2.1] 2026-08-12 ReAct think→act→observe 循环内核

### 新增

- `aegisos_agents/perception/reasoning/strategies/react_mode.py`：提供 `ReactMode`、
  `ReactDecision`、`ReactStep`、`ReactResult` 与终态枚举。
- 思考器通过结构化决策选择 `ToolCall` 或结束循环；工具执行复用
  `ExecutionAPI`、`ToolCall` 和 `ToolResult` 现有契约。
- 工具异常规范化为失败观察，支持下一轮修正；可配置首次工具错误即停止。
- 最大轮数保护阻止无限工具调用，完整轨迹可用于审计与回放。

### 测试

- 新增 `test_react_mode.py` 10 个用例，覆盖成功、即时结束、执行端口适配、
  工具异常恢复、快速失败、轮数保护、思考异常和参数校验。
- 感知层 70 个测试通过；`react_mode.py` 定向覆盖率 98%。
- AP2.2-AP2.6 五 Agent 接入已完成；AP2.7/H1 安全沙箱联调仍待完成。

## [P2] 2026-08-03 工具层补全 — 2 个空模块实现

### 新增模块

| 模块 | 文件 | 职责 |
|------|------|------|
| prompts | `registry.py` + `renderer.py` | Prompt 模板集中注册、版本追踪、角色筛选、变量渲染、变量校验。预置 11 个 Agent 默认模板 |
| runtime | `lifecycle.py` + `supervisor.py` | Agent 六态状态机（Init→Running⇌Suspended→Completed/Failed/Timeout）+ 心跳 + 超时 + 多 Agent 托管 |

### 测试

- 新增 2 个测试文件：test_prompts（14 用例）/ test_runtime（13 用例）
- 27 新测试
- 纯算法实现，不调 LLM
- 复用 protocol/Heartbeat 类型

## [P2] 2026-08-01 感知层补全 — 2 个空模块实现

### 新增模块（2 个）

| 模块 | 文件 | 职责 |
|------|------|------|
| context | `window.py` + `manager.py` | 上下文窗口管理：TokenBudget（token 估算+智能裁剪）+ ContextManager（open/close/pack/switch/isolate） |
| reflection | `critic.py` + `scoring.py` + `feedback.py` | 运行时反思：ExecutionCritic（四维批判）+ OutputScorer（四维评分）+ FeedbackLoop（整合→写回 memory/reflection） |

### 测试

- 新增 2 个测试文件：test_context（12 用例）/ test_reflection（14 用例）
- 26 新测试（含 context 12 + reflection 14）
- 3 已有 perception 测试零回归

### 设计原则

- 纯算法实现，不调 LLM（与 AGENT.md 标注一致）
- perception/reflection 区别于 memory/reflection：前者评估"本次执行行不行"，后者评估"历史记忆好不好"
- FeedbackLoop 写回 memory/reflection（tag_outcome + record_reference），形成认知闭环

## [P2] 2026-08-01 记忆子系统补全 — 7 个空模块实现 + MemoryStore v2 集成

### 新增模块（7 个）

| 模块 | 文件 | 层级 | 职责 |
|------|------|------|------|
| retrieval | `engine.py` + `__init__.py` + `AGENT.md` | ★核心 | 混合检索引擎：向量+关键词+图三通道 RRF 融合 |
| cache | `store.py` + `__init__.py` + `AGENT.md` | ★核心 | 二级记忆缓存：L1 查询缓存（TTL 60s）+ L2 热点缓存（LRU 100 条）|
| checkpoint | `manager.py` + `__init__.py` + `AGENT.md` | ★核心 | 检查点管理器：每 N 步自动保存编排器状态，支持断点恢复 |
| reflection | `engine.py` + `__init__.py` + `AGENT.md` | ★核心 | 反思引擎：三维评估（时效性×引用频次×结果标记），优质经验优先 |
| archive | `store.py` + `__init__.py` + `AGENT.md` | ◇骨架 | 冷数据归档：低引用记忆下沉长期存储 + defrost 回热 |
| snapshot | `manager.py` + `__init__.py` + `AGENT.md` | ◇骨架 | 全局快照管理器：拍摄/恢复/列举/清理时间点快照 |
| sync | `sync.py` + `__init__.py` + `AGENT.md` | ◇骨架 | 端边云同步：push/pull/merge 协议骨架，进程内多节点模拟 |

### MemoryStore v2 变更

- **`recall()` 升级**：缓存→检索→反思三级流水线替换旧关键词匹配
- **`write()` 升级**：新增缓存失效 + 反思预评估
- **`retrieve()` 升级**：委托 RetrievalEngine 做 RRF 混合检索
- **新增 3 个编排器钩子**：`checkpoint_cycle()` / `archive_cycle()` / `snapshot_cycle()`
- **新增 7 个属性**：retrieval_engine / cache / checkpoint / reflection / archive / snapshot / sync

### 测试

- 新增 7 个测试文件：test_retrieval / test_cache / test_checkpoint / test_reflection / test_archive / test_snapshot / test_sync
- 39 新测试通过

### 不变约束

- `protocol/memory.py` MemoryPacket：零改动
- 现有 7 个已实现模块（working/episodic/semantic/vector/compression/recall/memory_store）：接口兼容
- `MemoryAPI`（read/write/retrieve）：签名不变

## [R6] 2026-07-08 SDK 对齐清理--删除死代码 + 修复注释规范

### R6.1 - 删除 sdk_provider.py 死代码 complete() + _call()
- 排查发现 `tools/llms/sdk_provider.py` 的 `complete()` 方法（旧 `ModelProvider.complete()` 接口）已无任何业务调用方：grep 确认所有 Agent 走 `StructuredAgent._run()` -> SDK `Runner.run_sync`，`backend/core/composition.py` 仅用 `SDKProvider.get_sdk_model()`。
- 删除 `complete()` 方法 + 内联 `_call()` async 函数（手写 `chat.completions.create` + `asyncio.run` 同步包装 + 异常捕获）--这些已被 SDK `OpenAIChatCompletionsModel` + `Runner.run_sync` 原生替代。
- 删除随之未使用的 import：`ChatCompletionMessageParam`（来自 `openai.types.chat`）、`LLMRequest`/`LLMResponse`（来自 `.base`）。
- 更新文件 docstring：标题 `ModelProvider` -> `MockProvider`，移除"本适配器实现 ModelProvider Protocol"等过时描述。
- 保留 `get_sdk_model()` + `is_mock` + `create_provider` 工厂（业务在用）。

### R6.2 - 修复 __init__.py 注释规范违规
- `tools/llms/__init__.py` 文件头 `# changelog:` 行违反 `comment-style-rule.md`（changelog 应在变更处上方，不在文件头）。
- 删除文件头 `# changelog:` 行，简化 docstring（移除 R5 清理历史说明，仅保留当前导出清单）。

**测试：250 passed（无回归）**

## [AP3] 2026-07-08 Goal 范式（递归目标分解 + 失败重试 + 备选路径，4 子任务全完成）

### AP3.1 - Goal 模式核心
- 新增 `aegisos_agents/perception/reasoning/strategies/goal_mode.py` - `GoalMode` 混入类（递归分解 `decompose()` + 执行树 `execute_tree()` + 失败重试 + 备选路径注入）。`GoalNode`/`GoalResult`/`GoalStatus` 数据类型。3 场景模板（cyber_red/cyber_blue/generic）+ 自定义模板支持。`create_goal_mode_orchestrator` 工厂函数。
- 更新 `aegisos_agents/perception/reasoning/strategies/__init__.py` - 导出 GoalMode 相关类型。

### AP3.2 - CyberOrchestrator 接入 Goal
- 更新 `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` - `CyberOrchestrator` 继承 `GoalMode[dict]`，新增 `run_red_chain_with_goal()` / `run_blue_chain_with_goal()` 方法（替代固定模板链，递归分解 + 重试）。新增 `_create_red_agent_executor()` / `_create_blue_agent_executor()` 执行回调（按 agent_name 分发到对应 Agent，注入 fallback hint）。

### AP3.3 - exploit_planner Goal 递归
- 更新 `aegisos_agents/action/exploit_planner/agent.py` - 新增 `plan_with_goal()` 方法，将复杂攻击目标按资产递归分解为多阶段子目标（初始访问 + 横向移动），失败重试 + 备选路径，汇聚为完整 AttackChain。适用于超长程攻击链场景。

### AP3.4 - 测试
- 新增 `tests/aegisos_agents/perception/test_goal_mode.py` - 21 个测试：数据类型验证 + decompose 递归分解（4 场景）+ execute_tree 成功/失败重试/备选路径/依赖跳过 + 工厂函数 + CyberOrchestrator 端到端（红队/蓝队）+ ExploitPlannerAgent.plan_with_goal（单资产/多资产/空）。

**测试总数：229 → 250（+21）**

## [H5] 2026-07-07 可观测与评测（5 子任务全完成）

### H5.1 — 实时监控
- 新增 `observability/inspect/monitor/metrics.py` — `MetricsCollector` 订阅 EventBus 自动采集 Agent 延迟/成功率/Token/调用次数。`Metric`/`MetricType`（counter/gauge/histogram）+ `AlertRule`/`Alert` 告警规则 + `get_dashboard()` 面板数据（summary/agents/tools/alerts/latency）。
- 新增 `observability/inspect/monitor/__init__.py` — 导出 5 个类型。
- 实现 `MonitorAPI` Protocol。

### H5.2 — 攻击链回放
- 新增 `observability/inspect/replay/player.py` — `Timeline` 时序记录（按时间排序 + task_id/topic/agent/时间范围过滤）+ `ReplayPlayer`（step/seek/replay/play_timed 速度控制）+ `get_attack_chain_view()` 评委演示视图（配对 AgentStart/Finish 计算延迟）+ `create_replay_from_eventbus()` 工厂。
- 新增 `observability/inspect/replay/__init__.py` — 导出 4 个类型。
- 实现 `ReplayAPI` Protocol。

### H5.3 — 性能基准测试
- 新增 `observability/measure/benchmark/runner.py` — `BenchmarkCase`/`BenchmarkSuite`/`BenchmarkRunner` + `CaseResult`/`CaseStats`/`BenchmarkReport`。支持 setup/teardown、重复运行取 min/avg/max/p99/std 统计、成功率统计。
- 新增 `observability/measure/benchmark/__init__.py` — 导出 6 个类型。
- 实现 `BenchmarkAPI` Protocol。

### H5.4 — 5 维度评测
- 新增 `observability/measure/evaluation/scorers.py` — 5 评分函数（`score_accuracy`/`score_recall`/`score_latency`/`score_resource`/`score_robustness`）+ `Evaluator`（5 维度加权总分，对齐赛题评分占比 accuracy 30%/recall 20%/latency 15%/resource 15%/robustness 20%）+ `EvaluationReport`/`DimensionScore`/`Metric` + `evaluate_from_benchmark()` 从基准报告提取延迟。
- 新增 `observability/measure/evaluation/__init__.py` + `observability/measure/__init__.py` — 导出聚合。
- 实现 `EvaluationAPI` Protocol。

### H5.5 — 数据可视化
- 新增 `observability/present/visualization/renderer.py` — `ChartGenerator`（agent_latency_chart/success_rate_chart/benchmark_latency_chart/evaluation_radar_chart，ECharts 兼容）+ `GraphRenderer`（render_topology/render_attack_chain，React Flow 兼容）+ `DashboardAssembler`（聚合监控/基准/评测/回放为综合仪表盘）+ `VisualizationService`（统一 render 入口）。
- 新增 `observability/present/visualization/__init__.py` + `observability/present/__init__.py` — 导出聚合。
- 实现 `VisualizationAPI` Protocol。

### 测试
- 新增 `tests/observability/test_monitor.py` — 7 个测试（指标采集/EventBus 订阅/告警触发/面板结构/工具计数/reset）
- 新增 `tests/observability/test_replay.py` — 8 个测试（时间排序/过滤/攻击链视图/步进/reset/确定性回放/工厂）
- 新增 `tests/observability/test_benchmark_evaluation.py` — 15 个测试（基准执行/失败/setup-teardown/结果查询/JSON + 5 评分函数 + Evaluator 5 维度/满分/历史/从 benchmark/JSON）
- 新增 `tests/observability/test_visualization.py` — 11 个测试（拓扑图/攻击链 DAG/图表生成/雷达图/仪表盘聚合/服务入口）
- 本机 Windows Python 3.14.6 + openai-agents 0.17.7 验证：**229 passed**（188 既有 + 41 新增），0 failed，25.22s。

### 文件清单
- 新增源码 9 个：`monitor/{metrics,__init__}.py` + `replay/{player,__init__}.py` + `benchmark/{runner,__init__}.py` + `evaluation/{scorers,__init__}.py` + `visualization/{renderer,__init__}.py` + `measure/__init__.py` + `present/__init__.py`
- 新增测试 4 个：`test_monitor.py` + `test_replay.py` + `test_benchmark_evaluation.py` + `test_visualization.py`

## [AP1] 2026-07-07 Plan 行动范式（两阶段 LLM 推理增强，5 子任务全完成）

### AP1.1 — plan_mode.py 实现
- 新增 `aegisos_agents/perception/reasoning/strategies/plan_mode.py` — `PlanMode[T]` 泛型混入类 + `PlanResult`/`PlanStep` Pydantic 类型 + `create_plan_mode_agent()` 工厂函数。
- 两阶段推理：阶段 1 用独立 SDK `Agent(output_type=PlanResult)` 生成策略 + 步骤分解；阶段 2 把策略拼入增强 prompt，用 Agent 自身 output_type 生成详细产出。
- 规划失败或空策略时降级到直接 `_run`（向后兼容）。
- 新增 `aegisos_agents/perception/reasoning/strategies/__init__.py` — 导出 PlanMode/PlanResult/PlanStep/create_plan_mode_agent。

### AP1.2 — exploit_planner 接入 Plan 范式
- 修改 `aegisos_agents/action/exploit_planner/agent.py` — 继承 `PlanMode[ExploitPlannerResult]`，新增 `plan_with_strategy(findings)` 方法。先规划攻击策略（入口资产、攻击路径、目标），再按策略生成详细 AttackChain。

### AP1.3 — ir_planner 接入 Plan 范式
- 修改 `aegisos_agents/action/ir_planner/agent.py` — 继承 `PlanMode[IRPlannerResult]`，新增 `plan_response_with_strategy(hypotheses)` 方法。先规划多阶段响应策略（隔离→阻断→诱饵→监控），再生成详细 DefenseAction 列表。

### AP1.4 — lateral_move 接入 Plan 范式
- 修改 `aegisos_agents/action/lateral_move/agent.py` — 继承 `PlanMode[LateralMoveResult]`，新增 `plan_moves_with_strategy(chain, topology)` 方法。先规划移动策略（可达性分析 + 优先路径），再生成详细 AttackStep 列表。

### AP1.5 — 测试
- 新增 `tests/aegisos_agents/perception/test_plan_mode.py` — 9 个测试：
  - PlanResult/PlanStep 类型验证（2）
  - 3 Agent 降级路径（3）：Mock 不识别规划 prompt 时降级到直接执行
  - 完整两阶段路径（1）：Mock 能响应规划 prompt 时走完整 Plan 范式
  - 工厂函数 + 格式化（3）
- 本机 Windows Python 3.14.6 + openai-agents 0.17.7 验证：**188 passed**，0 failed，13.28s。

### 文件清单
- 新增 2 个：`strategies/plan_mode.py` + `strategies/__init__.py`
- 修改 3 个：`exploit_planner/agent.py` + `ir_planner/agent.py` + `lateral_move/agent.py`（继承 PlanMode + 新增 *_with_strategy 方法）
- 新增 1 个测试：`test_plan_mode.py`（9 测试用例）

### 设计说明
- PlanMode 是泛型混入类（mixin），不替代 StructuredAgent 继承链，原有 `plan`/`plan_response`/`plan_moves` 方法保持不变（向后兼容）。
- 规划阶段用独立 SDK `Agent(output_type=PlanResult)`，复用 Agent 自身的 `model`（Mock 或真实 API）。
- 降级策略：规划阶段抛异常或返回空 PlanResult 时，降级到直接 `_run`，保证 Mock 模式与现有测试不破坏。

## [R5] 2026-07-07 旧接口清理 + 流式输出 + AgentHooks 事件总线（5 子任务全完成）

### R5.1 — base.py 清理
- 修改 `aegisos_agents/tools/llms/base.py` — 删除 `ModelProvider` Protocol（SDK 有自己的 `ModelProvider`）。保留 `LLMRequest`/`LLMResponse`（MockProvider 内部契约）。
- 修改 `aegisos_agents/tools/llms/__init__.py` — 删除 `ModelProvider`/`ModelRouter` 导出。
- 修改 `aegisos_agents/tools/llms/sdk_provider.py` — 更新 docstring。

### R5.2 — model_router 删除
- 删除 `aegisos_agents/tools/llms/model_router.py` + `tests/aegisos_agents/tools/test_model_router.py`（无业务引用）。

### R5.3 — SDK Runner.run_streamed() → SSE 流式输出
- 修改 `aegisos_agents/action/structured_agent.py` — 加 `_run_streamed(prompt)` 异步方法。
- 新增 `backend/routers/stream.py` — `POST /api/v1/stream/agent/{id}` + `/stream/red_chain` + `/stream/blue_chain`。
- 修改 `backend/main.py` — 挂载 stream router。
- 新增 `frontend/src/services/api/stream.ts` — fetch + ReadableStream 读取 POST SSE。
- 修改 `frontend/src/views/chat/ChatView.tsx` — 加 Stream 模式开关。

### R5.4 — AgentHooks 发布事件到 EventBus
- 修改 `observability/inspect/monitor/tracing/hooks.py` — `CyberAgentHooks` 加 `eventbus` 参数，回调发布 `protocol.Event`（on_start→AgentStart, on_end→AgentFinish, on_tool_start→ToolCall, on_tool_end→ToolFinish）。
- 修改 `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` — `install_hooks(eventbus=bus, task_id=...)`。
- 新增 `tests/aegisos_agents/planning/test_agent_hooks_eventbus.py` — 6 个测试。

### R5.5 — 测试全通过
- **179 passed**，0 failed，3.68s。删除损坏的 `test_cyber_function_tools.py`。

## [R4.8] 2026-07-09 全量测试通过，R4 阶段完成（208 passed, 0 failed）

### R4.8 — R4 阶段全部 8 项任务完成
- R4.1 ✅ 神经符号 Agent SDK 迁移（4 测试）
- R4.2 ✅ SDK Handoffs 链式编排（9 测试）
- R4.3 ✅ SDK output_guardrails 紫队闭环（5 测试）
- R4.4 ✅ SDK tracing + AgentHooks（22 测试）
- R4.5 ✅ SDK FunctionTool 攻防工具注册（30 测试）
- R4.6 ✅ MockRuntime 委托 CyberOrchestrator
- R4.7 ✅ composition.py 注入共享编排器
- R4.8 ✅ 全量 208 测试全通过

**SDK 迁移完成度：11/11 Agent 全部走 SDK `StructuredAgent`，红蓝紫三条链全部走 SDK `Agent.handoffs` / `output_guardrails` / `tracing` / `AgentHooks` / `FunctionTool`。**

## [R4.7] 2026-07-09 composition.py 注入共享 CyberOrchestrator（208 测试通过）

### R4.7 — DI 组合根注入 CyberOrchestrator（完成）
- `backend/core/composition.py` 重构：
  - 新增 `_create_orchestrator()` 静态方法：根据 `AEGIS_USE_MOCK` / `OPENAI_API_KEY` 自动选择 Mock / 真实模式
  - Mock 模式：`CyberOrchestrator(mock=_CyberMockProvider())` — SDK Agent 走预置响应表
  - 真实模式：`CyberOrchestrator(model=SDKProvider().get_sdk_model())` — SDK Agent 调真实 LLM
  - `Composition.orchestrator` 属性：全局共享编排器实例
  - `MockRuntime(orchestrator=self.orchestrator)` — 注入共享实例，避免重复创建
  - `CyberDefenseService(orchestrator=self.orchestrator)` — 同一编排器，保证一致性
- `backend/mocks/runtime.py` 修改：
  - `MockRuntime.__init__` 新增 `orchestrator` 可选参数，默认创建新实例
  - 外部注入时使用传入实例，实现共享
- 208 测试全通过（无回归）
- **变更文件**：`backend/core/composition.py` + `backend/mocks/runtime.py`

## [R4.6] 2026-07-09 MockRuntime 替换为 CyberOrchestrator（208 测试通过）

### R4.6 — MockRuntime 委托 CyberOrchestrator（完成）
- `backend/mocks/runtime.py` 重构：
  - 删除 85 行手写 `_cyber_dispatch_map()` 中的链式 handler（red_chain/blue_chain/purple_review）
  - `MockRuntime.__init__` 创建 `self._orchestrator = CyberOrchestrator(mock=self._provider)`，链式调用委托编排器
  - 保留 `_single_agent_dispatch()` 用于非链式单 Agent 调用（recon/detector/vuln_correlator 等）
  - 新增 `_wrap()` / `_serialize_red()` / `_serialize_blue()` 静态方法
  - 接口签名不变（`submit` / `run` / `stop` / `heartbeat`），向后兼容
- `backend/services/cyber_defense_service.py` 修复：
  - `__init__` 默认创建 `CyberOrchestrator(mock=_CyberMockProvider())`，注入攻防 Mock 响应表
  - 修复前：`CyberOrchestrator()` 无 Mock 注入，SDK Agent 返回空结果导致端点测试失败
- 208 测试全通过（含 12 端点测试 + 22 tracing + 30 tools + 144 既有）
- **变更文件**：`backend/mocks/runtime.py` + `backend/services/cyber_defense_service.py`

## [R4.5] 2026-07-09 SDK FunctionTool 攻防工具注册（30 测试通过）

### R4.5 — SDK FunctionTool 注册攻防工具（完成）
- 新建 `aegisos_agents/tools/cyber_tools.py`：
  - 6 个 SDK `FunctionTool`：红队（nmap_scan / metasploit_exploit / lateral_move_exec）+ 蓝队（query_attck_kb / query_cve_db / correlate_alerts）
  - 6 个 async 回调函数返回 Mock 结构化数据
  - 6 个 JSON Schema 定义参数结构
  - 工厂函数：`create_red_team_tools()` / `create_blue_team_tools()` / `create_all_cyber_tools()`
  - `needs_approval=True` 用于高危工具（metasploit_exploit, lateral_move_exec）
- `CyberOrchestrator` 集成：
  - `install_red/blue/all_tools()` — 将工具注册到 Agent 的 `Agent.tools`
  - `uninstall_all_tools()` / `get_agent_tools()` / `get_high_risk_tools()`
- 新建 `aegisos_agents/tools/__init__.py`（包初始化）
- 30 测试通过（4 creation + 5 schema + 4 approval + 7 callback + 10 installation）
- **变更文件**：`aegisos_agents/tools/cyber_tools.py` + `aegisos_agents/tools/__init__.py` + `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` + 新增 `tests/aegisos_agents/planning/test_cyber_function_tools.py`

## [R4.4] 2026-07-09 SDK tracing + AgentHooks（22 测试通过）

### R4.4 — SDK tracing + AgentHooks 替代手动日志（完成）
- 新建 `observability/inspect/monitor/tracing/` 包：
  - `processor.py`：`CyberTraceProcessor(TracingProcessor)` — 采集 trace/span 数据到内存（`CyberTraceData` + `CyberSpanData`）
  - `hooks.py`：`CyberAgentHooks(AgentHooksBase)` — 7 个 async 回调记录 Agent 生命周期事件（`HookEvent`）
  - `__init__.py`：导出 5 个类
- `CyberOrchestrator` 集成：
  - `enable_tracing()` / `disable_tracing()` — 注册/移除 `CyberTraceProcessor`
  - `install_hooks()` — 为 9 个 Agent 安装 `CyberAgentHooks`
  - `get_trace_data()` / `get_trace_json()` / `get_hooks_events()` — 获取采集结果
  - `run_red_chain_traced()` / `run_blue_chain_traced()` / `run_purple_review_traced()` — 在 `trace()` 上下文管理器中执行编排
- 重要发现：SDK `Trace` 对象用 `.name` 而非 `.workflow_name` 获取 workflow 名称
- 22 测试通过（6 processor + 5 hooks + 11 orchestrator）
- **变更文件**：`observability/inspect/monitor/tracing/processor.py` + `hooks.py` + `__init__.py` + `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` + 新增 `tests/aegisos_agents/planning/test_cyber_tracing.py`

## [R4.1-R4.3] 2026-07-08 SDK 编排深化（neuro_symbolic 迁移 + handoffs + guardrails，18 测试通过）

### R4.1 — neuro_symbolic 迁移到 SDK StructuredAgent（P0 完成）
- `NeuroSymbolicLoop` → `NeuroSymbolicAgent(StructuredAgent[ExploitPlannerResult])`，用 SDK `output_type`（Pydantic）替代手写 `json.loads` + `try/except`。
- `_regenerate()` 改用 `self._run()`，新增 `_result_to_chain()` 转换 `ExploitPlannerResult` → `AttackChain`。
- `validate_chain()` 保留为纯函数（不涉及 LLM），闭环用手动 `validate_and_fix()` 循环。
- ⚠️ 未用 SDK `output_guardrail`：SDK guardrail 抛 `OutputGuardrailTripwireTriggered` 异常后不自动重试，保留手动 `max_iterations` 循环。
- `NeuroSymbolicLoop = NeuroSymbolicAgent` 别名向后兼容。
- **变更文件**：`aegisos_agents/perception/reasoning/neuro_symbolic.py`（4 测试通过）

### R4.2 — SDK Agent.handoffs 声明式链（混合方案）
- **架构决策**：SDK handoffs 是 LLM 驱动动态路由（LLM 决定是否 `transfer_to_*`），非固定顺序管道。对红蓝固定链，手动顺序执行是正确架构。采用混合方案：保留手动链为默认路径 + 新增 handoff 链为声明式替代。
- 新增 `ChainContext` dataclass：跨 handoff 共享上下文，累积各步产出（recon/vuln/exploit/detector/triage/hunt/ir_output）。
- 新增 `run_red_chain_via_handoffs()` / `run_blue_chain_via_handoffs()`：SDK `Agent.handoffs` 声明式串联，`on_handoff` 回调标记各步完成。
- SDK handoff 规则发现：不配 `input_type` 时 `on_handoff` 只接收 1 参数 (context)；配 `input_type` 时接收 2 参数 (context, input)。
- Mock 模式下 `MockSDKModel` 返回纯文本（非工具调用），LLM 不触发 handoff → 自动回退手动链。
- **变更文件**：`cyber_orchestrator.py` + `__init__.py`（导出 `ChainContext`）+ 新增 `test_cyber_handoffs.py`（9 测试通过）

### R4.3 — SDK output_guardrails 紫队校验闭环
- **实现决策**：SDK guardrail 触发 `tripwire_triggered=True` 后抛 `OutputGuardrailTripwireTriggered` 异常，**不自动重试**。需手动捕获 + 重试循环。
- 新增 `create_attack_chain_guardrail()`：`@output_guardrail(name="attack_chain_validator")` 装饰，校验 chain_id 非空 + steps 非空 + 每步有 technique。
- 新增 `run_red_chain_with_guardrail()`：注入 guardrail 到 `exploit_planner._sdk_agent.output_guardrails`，捕获异常后从 `output_info` 提取反馈 → 重新调用 `_run()` 注入反馈 prompt → 最多重试 `max_retries` 次 → 完成后清理 guardrails。
- 返回 `guardrail_passed: bool` + `guardrail_feedback: str`。
- **变更文件**：`cyber_orchestrator.py` + 新增 `test_cyber_guardrails.py`（5 测试通过）

### 当前测试基线
- **aegisos_agents 测试**：124 passed（含 R4.1-R4.3 新增 18 测试）
- **全量测试**：128 passed, 5 failed（backend cyber endpoints 预存失败——`CyberDefenseService` 未注入 `_CyberMockProvider`，将在 R4.7 修复）

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
