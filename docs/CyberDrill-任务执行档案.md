# CyberDrill（攻防演练）模块 · 任务执行档案

> **本文件是攻防演练（Red-Blue-Purple 多 Agent 演练）模块的唯一执行档案**：
> 任务切分、每轮「开工前报告」与「开工后记录」、比赛要求映射、git 提交与版本回退同步规则，
> 全部沉淀在此。每开一轮新任务前必须回到本文档对应小节，先讲清楚再动手。
>
> 配套文档：
> - `docs/CyberDrill-开工审查报告.md` —— 技术审查结论、验收口径、T1-T7 原始任务清单
> - `docs/ARCHITECTURE.md` —— 全系统架构仪表盘（各域实现状态）
> - 根目录 `XH-...比赛方案.pdf` —— 赛事原文（评分标准/能力维度）

---

## 0. 使用规则（每次开工前必读）

### 0.1 每轮循环工作流

1. **开工前（必做）**：回到本文档对应 Round 小节，把「开工前报告」的 5 件事讲给用户：
   ① 要干什么（本轮落盘范围） → ② 对应比赛什么要求（能力维度/评分点） → ③ 与其他模块的联系 → ④ 模块内部逻辑（流程/契约/接口） → ⑤ 验收标准与实测位置。
   **等用户确认后**才动手写代码。
2. **开工**：严格按该 Round「落盘文件清单」实现；尽量小步、可回退。
3. **开工后（必做）**：填写该 Round「开工后记录」：改动文件清单、改动体现在项目哪里（前端哪里可见 / 内部调用用在哪）、测试结果、git commit、实测结果、遗留问题。
4. **git 提交**：每轮一个 commit（Conventional Commits 风格，如 `feat(cyber-drill): ...`），commit message 只描述产品变更与验证，不写内部工具/流程名。
5. **版本回退同步**：如果因任何原因执行 `git reset/revert` 回退到某轮，**本文档必须同步回退到该轮「开工后记录」完成时的状态**（删除超前轮次的记录，不留"超前文档"）；代码有新更新，本文档跟随更新。**文档与代码永远在同一版本**。

### 0.2 比赛要求速查（XH-202631 荣耀 · 面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术）

> 原文要点：作品须在**材料文档 + 可运行系统**两方面体现能力；可运行系统须能**接受动态注入的异常、需求变更或节点失效，并在无人干预下自主完成从高层意图到最终交付物的全链路推理与执行，展示中间决策过程与推理轨迹**。截止 2026-09-15。

| 比赛要求 | 方案原文要点 | 本模块落点 | 相关轮次 |
|---|---|---|---|
| 能力维度 a：超长程上下文连续性与记忆保持 | 跨越多轮决策流，克服注意力稀释与记忆坍缩；关键信息、中间决策、全局目标在长链推理中不丢失不漂移 | drill 多轮循环 + 跨轮事件 `carry_forward` + 收敛历史记录；R7 接入记忆子系统做跨轮决策摘要 | R1、R7 |
| 能力维度 b：动态异构拓扑与低熵通信 | 通信拓扑随任务语义动态生成稀疏路由；抑制通信冗余与噪声级联，显著降低信息熵 | 每轮 SSE 只推**增量战报**（new_steps/new_issues），不重放全量；R8 事件总线化（EventBus `/events` 可订阅） | R3、R8 |
| 能力维度 c：端-边-云异构资源自适应调度 | 依据子任务实时性要求与数据敏感等级，自动完成推理位置的动态选择与模型切分 | R9 演练各阶段 `placement` 标注，复用 scheduler 卸载规则（latency<1s→device / <5s→edge / 否则→cloud） | R9 |
| 能力维度 d：评测场景验证 | 在典型产业场景中完成可运行系统验证 | 场景 1「网络防御（红→蓝→紫完整链路）」一键闭环，可作为赛事演示主场景 | R1-R6、R10 |
| 能力维度 e：交付物 | 可运行系统无人干预全链路；展示中间决策过程与推理轨迹 | 前端轮次时间线逐轮展示红/蓝/紫决策摘要；演练记录持久化可回放（`data/drills/<drill_id>.json`） | R2、R5、R10 |
| 评分·作品完整性 40 | 感知-规划-执行-反馈闭环 / 组织架构与协作机制 / 多任务场景演示 | 一键演练闭环 = 感知（红队扫描）→规划（攻击链/响应计划）→执行（蓝队处置）→反馈（紫队评审→下一轮）；红蓝紫三层分工即"层级/分工协作机制" | R1-R6 |
| 评分·技术创新性 20 | 降噪创新 + 核心算法与底层突破 | 收敛判定算法（4 规则提前终止）、增量事件合成（避免全量重放、控制 token 消耗） | R1、R8 |
| 评分·系统性能与效率 15 | 鲁棒性 / token 与时间资源效率 / 兼容扩展 | 提前收敛减少空转轮次（省 token/时间）；增量合成避免上下文膨胀；既有红/蓝/紫 REST 端点不动（兼容性） | R1、R6 |
| 评分·应用创新性 25 | 用户体验与易用性 5 / 场景覆盖 | 前端一键"开始演练"+ 实时时间线 + 总结报告，降低使用门槛 | R5 |

### 0.3 总路线图（Phase 0-5 · Round 0-10）

| 轮次 | 任务 | 阶段 | 依赖 | 比赛维度 | 状态 |
|---|---|---|---|---|---|
| **R0** | git 仓库初始化 + 本档案建档 + 全量初始提交 | 基线 | — | 工程保障 | ✅ 本轮完成 |
| **R1** | 编排器收敛式演练内核（`run_drill` + 事件合成 + 收敛判定纯函数） | 核心 | R0 | a / 完整性40 / 技术20 / 效率15 | ⬜ 待开工 |
| **R2** | Service 层透出 `run_drill` + 演练记录持久化（`data/drills/`） | 核心 | R1 | e / 回放 | ⬜ |
| **R3** | 后端 drill 路由（REST + SSE 5 端点）+ 路由挂载 | 核心 | R2 | b / d | ⬜ |
| **R4** | 前端类型 + `cyberApi` drill 客户端（含 SSE 订阅） | 核心 | R3 | d | ⬜ |
| **R5** | 前端演练视图（开始/停止 + 轮次时间线 + 总结报告） | 核心 | R4 | d / e / 体验5 | ⬜ |
| **R6** | 端到端联调 + 全量回归 + 实测指南定稿 | 核心 | R1-R5 | d | ⬜ |
| **R7** | 跨轮记忆与上下文压缩（紫队带历史决策摘要） | 延申 P1 | R6 | a（重点加分） | ⬜ |
| **R8** | 演练事件总线化 + 低熵增量推送（EventBus 联动） | 延申 P1 | R6 | b（技术分10） | ⬜ |
| **R9** | 端-边-云 placement 联动（演练阶段调度位置标注） | 延申 P2 | R8 | c | ⬜ |
| **R10** | 无人干预演示脚本 + 赛事材料文档补全收尾 | 延申 P2 | R6-R9 | d / e | ⬜ |

> 优先级策略：**R1-R6 为必做**（9-15 截止前保证一键闭环可演示）；**R7-R8 为强加分**（直接命中维度 a/b，优先于 R9）；**R9-R10 视剩余时间与稳定性决定**。

---

## 1. Phase 0 · 工程基线

### R0 · git 仓库初始化 + 本档案建档

- **一句话目标**：让项目进入可版本回退状态，并建立本执行档案作为后续所有轮次的"开工前/开工后"载体。
- **比赛要求映射**：无直接评分点，属交付物工程保障——保证每一轮成果可回退、可追溯（对应 e 交付物的"材料文档"部分）。
- **与其他模块的联系**：全项目基线，不触碰业务代码。
- **模块内部逻辑**：`git init` → 确认 `.gitignore` 已覆盖运行时产物（env/缓存/日志/前端构建物）→ `git add -A` 全量纳入 → 首次 commit。
- **落盘文件清单**：`.git/`（新建）、`docs/CyberDrill-任务执行档案.md`（本文件，新建）。
- **验收标准**：`git log --oneline` 可见初始提交；后续每轮一个 commit。
- **实测位置**：命令行 `git log --oneline` / `git status`。
- **风险与对策**：仓库首次提交包含历史全量代码，回退粒度以轮次 commit 为准；大文件（比赛 PDF ~400KB）一并纳入，属材料文档，合理保留。

- **开工确认**：[x] 用户已确认（2026-09-04，用户指令"每一次做完一轮任务都要提交一次 git 以防版本回退"）
- **开工后记录**：
  - 改动文件清单：`docs/CyberDrill-任务执行档案.md`（新增）；`.git/`（初始化）
  - 改动体现在项目哪里：仓库根目录出现 git 版本历史；档案文档作为攻防模块唯一执行档案
  - 前端哪里可见 / 内部调用位置：无业务可见性（纯工程基线）
  - 测试结果：`git status` 干净、`git log` 有初始提交
  - git commit：`docs(cyber-drill): 建档——任务切分与执行档案（R0）`
  - 实测结果：待首轮提交后回填
  - 遗留问题 / 下一步：进入 R1（编排器收敛式演练内核）

---

## 2. Phase 1 · 一键闭环基础版（核心交付，对应开工审查报告 T1-T7）

### R1 · 编排器收敛式演练内核

- **一句话目标**：在 `CyberOrchestrator` 上新增 `run_drill` 主循环——一次调用自动跑完「红→蓝→紫」≤M 轮并提前收敛，配套两个纯函数（事件合成、收敛判定）保证可单测。
- **比赛要求映射**：
  - 能力维度 a：多轮循环 + 事件 `carry_forward`，跨轮上下文连续；
  - 完整性 40：「感知-规划-执行-反馈」闭环一次跑通；
  - 技术创新 20 / 效率 15：原创收敛判定（4 规则提前终止，不空转）+ 增量事件合成（不重放全量，控制 token 膨胀）。
- **与其他模块的联系**：
  - 复用既有 `run_red_chain`（L402）/`run_blue_chain`（L465）/`run_purple_review`（L516）及其变体（guardrail/handoffs/traced/goal/human-check 全部保留、语义不变）；
  - 协议契约 `protocol/cyber.py` 只读复用（`AttackChain`/`Alert`/`ResponsePlan`/`PurpleReviewResponse`）；
  - 被 R2 Service 层包装、被 R3 路由经回调推送 SSE、被 R7 记忆注入扩展。
- **模块内部逻辑**：
  ```
  run_drill(target_range, max_rounds=5, on_round=None) -> dict
    history = []                                  # 每轮收敛判定历史
    prev_stream = []                              # 事件流累计（跨轮 carry）
    chain = None
    for round in 1..max_rounds:
      event_stream = _synthesize_event_stream(chain, prev_stream, round)   # 纯函数①
      red   = run_red_chain(target_range)         # 复用；后续轮可带上一轮紫队反馈
      blue  = run_blue_chain(event_stream)        # 复用，契约 list[dict]
      purple= run_purple_review(red, blue)        # 复用
      stop, code = _evaluate_stop(purple.critique, purple.review, round, history)  # 纯函数②
      on_round(round_payload)                     # 回调供上层推 SSE
      if stop: break
    聚合 PurpleReviewResponse + 跨轮摘要（conclusion / convergence_code /
    rounds_executed / red_summary / blue_summary / purple_summary / remaining_risks）
  ```
  - 纯函数① `_synthesize_event_stream(chain, prev_stream, round)`：
    - Round 1：`AttackChain.steps` 逐条映射为事件 `{round, seq, type:"attack_step", source, target, technique, success}`；
    - Round N+1：上一轮事件全部 `carry_forward: true` 保留 + 追加本轮 `step_id` 未出现过的新步骤为增量事件；
    - 无新步骤 → 仅 carry，配合收敛规则 2 触发"无进展"结束；
    - 返回 `list[dict]` 副本，不改动红队原始链。
  - 纯函数② `_evaluate_stop(critique, review, round, history) -> (stop: bool, code: str)`，满足其一即停：
    1. 完全收敛：`critique.valid == True and review.consistent == True` → `converged`；
    2. 无进展：连续 2 轮 `new_issue_count == 0` 且 severity 不升高 → `no_progress`；
    3. 轮次上限：`round >= max_rounds` → `max_rounds`；
    4. 显式中止：外部 `abort_flag` → `aborted`。
- **落盘文件清单**：
  - `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（新增 3 个方法）
  - `tests/aegisos_agents/planning/orchestrator/test_drill_convergence.py`（新建：事件合成 3 场景 + 收敛 4 规则 + max_rounds 边界）
- **验收标准**：单测全绿；默认 5 轮，未收敛恰在 5 轮结束，收敛提前结束；既有 594 项 Python 回归不破。
- **实测位置**：`pytest tests/aegisos_agents/planning/orchestrator/test_drill_convergence.py`；或 Python REPL：`CyberOrchestrator(mock=...).run_drill("10.0.0.0/24", max_rounds=5)` 看返回结构。
- **风险与对策**：mock 模式下多轮产出变化小 → 收敛判定基于结构字段而非文本相似；回调 `on_round` 抛异常 → 捕获后转 `drill_error` 并中止。
- **可延申点**：R7 在循环内注入记忆摘要；R9 在每阶段标注 placement。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

### R2 · Service 层透出 drill + 演练记录持久化

- **一句话目标**：`CyberDefenseService.run_drill(...)` 包装编排器，并把每次演练完整落盘到 `data/drills/<drill_id>.json`，支持查询与中止。
- **比赛要求映射**：能力维度 e —— 演练记录 = 中间决策过程与推理轨迹的可回放证据；同时是 SSE 断线后的轮询兜底数据源。
- **与其他模块的联系**：包装 R1 编排器；被 R3 路由调用；复用 `MemoryStore`（R7 将在此基础上做跨轮记忆）；落盘目录 `data/drills/` 与既有 `data/` 数据层共存。
- **模块内部逻辑**：
  ```
  run_drill(target_range, max_rounds=5, event_callback=None) -> dict
    drill_id = f"drill_{uuid4().hex[:8]}"
    status = "running"
    events = []                       # 内存事件队列（SSE 用）
    event_callback 逐事件产出：drill_start / drill_round / drill_summary / drill_error / drill_done
    每轮结束 → append 到 events + 写 data/drills/<drill_id>.json（增量更新）
    get_drill(drill_id) -> {status, rounds, events}      # 轮询兜底
    abort_drill(drill_id) -> 置 abort_flag（配合 R1 收敛规则 4）
  ```
  JSON 结构 = `{drill_id, target_range, max_rounds, status, created_at, rounds:[...], summary:{...}}`，与 SSE 战报契约同构。
- **落盘文件清单**：
  - `backend/services/cyber_defense_service.py`（新增 3 个方法）
  - `tests/backend/services/test_drill_service.py`（新建：mock 编排器下 run/get/abort/持久化还原）
- **验收标准**：单测通过；演练后 `data/drills/<drill_id>.json` 可还原各轮战报与总结。
- **实测位置**：`pytest tests/backend/services/test_drill_service.py`；REPL 调 `CyberDefenseService().run_drill(...)` 后查看 `data/drills/` 生成文件。
- **风险与对策**：并发写文件 → 按 drill_id 独立文件 + 原子写（写临时文件后 rename）；内存 registry 无界 → 演练完成后保留最近 N 条，历史靠磁盘文件。
- **可延申点**：R10 材料文档直接引用 `data/drills/` 样例作为交付证据。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

### R3 · 后端 drill 路由（REST + SSE）

- **一句话目标**：新建 `backend/routers/drill.py`，提供 5 个端点：启动 / SSE 直播 / 状态查询 / 总结拉取 / 显式中止，并挂载到既有网关。
- **比赛要求映射**：
  - 能力维度 d：可运行系统的对外接口；
  - 能力维度 b：SSE 每轮只推**增量战报**（本轮新步骤数、新问题数、各阶段摘要），不推全量链，体现低熵推送。
- **与其他模块的联系**：
  - 网关 `backend/core/routes.py` 已统一 `prefix="/api/v1"` + `verify_api_key` 鉴权，新路由自动继承；
  - 挂载点：`backend/routers/__init__.py` 加入 `drill`；
  - SSE 帧格式参考 `backend/routers/stream.py` 的 `_event_to_sse`（`event: <type>\ndata: <json>\n\n`）；
  - 数据源来自 R2 Service（含内存 registry 与磁盘持久化兜底）。
- **模块内部逻辑**（端点契约）：
  | 方法/路径 | 请求 | 响应 |
  |---|---|---|
  | `POST /api/v1/drill/start` | `{target_range?, max_rounds?=5}` | `201 {drill_id, status:"running", max_rounds}`，后台任务启动 |
  | `GET /api/v1/drill/{id}/stream` | — | `text/event-stream`：`drill_start → drill_round* → drill_summary → drill_done`；异常推 `drill_error` |
  | `GET /api/v1/drill/{id}` | — | 已发生轮次 + 当前状态（SSE 断开轮询兜底） |
  | `GET /api/v1/drill/{id}/summary` | — | 最终总结报告；未收敛 `409` + 当前中间态 |
  | `POST /api/v1/drill/{id}/abort` | — | `{status:"aborted"}`（收敛规则 4） |
  后台任务用 `asyncio.create_task` 跑 R2 `run_drill`；SSE 生成器从事件队列消费（asyncio.Queue 或 service 内存 list + 游标）。
- **落盘文件清单**：
  - `backend/routers/drill.py`（新建）
  - `backend/routers/__init__.py`（改：include drill）
  - `tests/backend/routers/test_drill_api.py`（新建：TestClient 覆盖 start→stream→summary→abort 全流程 + 409 分支）
- **验收标准**：curl 全端点可用；SSE 从 `drill_start` 到 `drill_done` 完整推送；既有 `/attack` `/defense` `/defense/purple-review` 回归不变。
- **实测位置**：`uvicorn backend.main:app` 起服务后：
  - `curl -X POST http://localhost:8000/api/v1/drill/start -H "X-API-Key: <key>" -H "Content-Type: application/json" -d '{"target_range":"10.0.0.0/24"}'`
  - 浏览器打开 `http://localhost:8000/api/v1/drill/<id>/stream` 看 SSE 流；FastAPI `/docs` 页面可直接调试 5 个端点。
- **风险与对策**：SSE 连接断开后任务仍在跑 → 状态/总结走 R2 磁盘与内存兜底；后台任务异常 → `drill_error` 事件 + 状态置 failed。
- **可延申点**：R8 将 drill_round 同时发布到 EventBus，Monitor 视图可订阅。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

### R4 · 前端类型 + drill API 客户端

- **一句话目标**：前端补上 drill 的类型定义与 API 方法（含 SSE 订阅封装），为 R5 视图铺路。
- **比赛要求映射**：能力维度 d/e —— 前端可运行系统的数据通道。
- **与其他模块的联系**：
  - `frontend/src/protocol/types.ts`：新增 `StartDrillRequest/StartDrillResponse/DrillRoundEvent/DrillSummaryResponse`（与 R3 契约对齐）；
  - `frontend/src/services/api/cyber.ts`：`cyberApi` 新增 `startDrill / openDrillStream / getDrill / getDrillSummary / abortDrill`；
  - SSE 订阅复用 `frontend/src/services/realtime/sse.ts` 的既有封装（EventSource/fetch-stream 模式）。
- **模块内部逻辑**：
  - `openDrillStream(drillId, onEvent)`：按 `event:` 名分发 `drill_start / drill_round / drill_summary / drill_error / drill_done` 到回调；
  - `getDrill/getDrillSummary` 走普通 `apiClient.get`，作为 SSE 断线兜底；
  - 类型字段与 R3 SSE 战报 JSON 严格对齐（round/max_rounds/status/phase{red,blue,purple}/event_id）。
- **落盘文件清单**：
  - `frontend/src/protocol/types.ts`（改）
  - `frontend/src/services/api/cyber.ts`（改）
  - `frontend/src/services/api/__tests__/cyber.drill.test.ts`（新建，若项目已有前端测试基建则并入）
- **验收标准**：前端单测/tsc 通过；`cyberApi` 方法可被 R5 调用。
- **实测位置**：`npm run build`（或 `npx tsc --noEmit`）类型通过；单测跑前端测试命令。
- **风险与对策**：SSE 事件名拼写不一致 → 以 R3 后端契约为唯一事实源，前端类型注解加注释锚点。
- **可延申点**：R8 后可在 Monitor 视图复用同一订阅封装。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

### R5 · 前端演练视图（开始/停止 + 轮次时间线 + 总结报告）

- **一句话目标**：在攻防页新增「Drill 演练」面板：一键开始、实时轮次时间线、收敛后总结报告展示、可停止。
- **比赛要求映射**：
  - 能力维度 e：时间线逐轮展示红/蓝/紫决策摘要 =「展示中间决策过程与推理轨迹」；
  - 应用创新·用户体验 5 分：一键闭环 + 实时可视化，降低使用门槛；
  - 完整性 40：演练闭环的前端呈现。
- **与其他模块的联系**：
  - 采用**方案 A（推荐）**：在 `frontend/src/views/cyber/CyberView.tsx` 现有 4 个 tab（Red/Blue/Purple/Threat）后追加 `Drill` tab，新建 `CyberDrillPanel.tsx`——**不动** `ViewName` 联合类型、Sidebar、store，回归风险最小、演示集中；
  - 备选方案 B（独立视图 + `ViewName` 加 `'cyber-drill'` + Sidebar 入口 + `App.tsx` 注册）仅在时间充裕时实施，开工时与用户确认选型；
  - 数据来自 R4 `cyberApi`；状态复用 store 的 `cyberLoading/cyberError` 模式。
- **模块内部逻辑**（方案 A）：
  ```
  CyberDrillPanel
    头部：target_range 输入（默认 10.0.0.0/24）+ 最大轮数（默认 5）+ [开始演练] / [停止]
    进行中：按钮变 [停止] → POST /drill/abort
    SSE 订阅 openDrillStream：
      drill_start   → 记录 drill_id、清空时间线、状态徽标 running
      drill_round   → 追加一张轮次卡片（轮次号、状态徽标、
                      红 steps/new_steps、蓝 alerts/triaged、紫 converged/new_issue_count，
                      可展开看 critique/review 详情，自动滚动到最新）
      drill_summary → 渲染总结报告卡（conclusion、convergence_code、
                      rounds_executed、red/blue/purple 统计、remaining_risks）
      drill_error   → 错误条 + 中止
      drill_done    → 恢复 [开始演练]
    断线兜底：SSE error → getDrill 轮询补拉已发生轮次
  ```
- **落盘文件清单**：
  - `frontend/src/views/cyber/CyberDrillPanel.tsx`（新建）
  - `frontend/src/views/cyber/CyberView.tsx`（改：TABS 加 `{id:"drill", label:"Drill"}` + 渲染分支）
  - `frontend/src/index.css`（改：时间线/徽标/总结卡样式，沿用现有 badge 体系）
- **验收标准**：点击开始 → 时间线逐轮实时出现 → 收敛后总结报告展示；「停止」可中止并输出已收敛部分；断线后可轮询补拉。
- **实测位置**：`npm run dev` 起前端 + `uvicorn backend.main:app` 起后端 → 浏览器侧边栏 Cyber → Drill tab → 输入目标范围 → 开始演练。
- **风险与对策**：SSE 断线/重连 → 轮询兜底；多轮数据量大 → 时间线默认折叠详情、只展示摘要行。
- **可延申点**：R7 总结报告加「跨轮记忆摘要」区；R9 轮次卡加执行位置徽标。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

### R6 · 端到端联调 + 全量回归 + 实测指南定稿

- **一句话目标**：把 R1-R5 串起来跑通完整演示链路，全量回归，并把「实测指南」定稿写进本档案。
- **比赛要求映射**：能力维度 d —— 可运行系统的完整验证；系统性能与效率 15 —— 回归证明鲁棒性/兼容性。
- **与其他模块的联系**：覆盖 backend（R1-R3）、frontend（R4-R5）、tests（全量）、docs（本档案实测指南区）。
- **模块内部逻辑**：按 `start.ps1` 启动 → 前端 Drill tab 完整跑一次演练 → 逐条核对开工审查报告 §5 验收表 → `pytest` 全量 + 前端测试 + `tsc`/build → 修复联调中暴露的小问题。
- **落盘文件清单**：可能的小修 bug；本档案「实测指南」区定稿；必要时 `README.md` 补演示入口说明。
- **验收标准**：开工审查报告 §5 六条验收全勾；Python 全量 + 前端测试全绿。
- **实测位置**：完整路径 = 后端 `uvicorn backend.main:app`（或 `start.ps1`）→ 浏览器 `http://localhost:5173` → Cyber → Drill tab。
- **风险与对策**：联调暴露跨层字段不一致 → 以 `protocol/cyber.py` 与 R3 契约为基准对齐，优先改前端/路由层，不动协议层。
- **可延申点**：为 R7-R10 提供稳定基线。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

## 3. Phase 2 · 超长程上下文连续性与记忆保持（能力维度 a）

### R7 · 跨轮记忆与上下文压缩（紫队带历史决策摘要）

- **一句话目标**：让演练循环接入既有记忆子系统——每轮紫队评审携带前几轮的**压缩摘要**（而非全量重放），直接命中「跨越多轮决策流、克服注意力稀释与记忆坍缩」。
- **比赛要求映射**：能力维度 a（重点加分项）；技术创新 20 的「核心算法与底层突破」展示。
- **与其他模块的联系**：
  - `aegisos_agents/memory/` 四层存储 + `compression/compactor.py` + `recall/recaller.py` 全部已就绪，直接复用；
  - R2 Service 已持有 `MemoryStore`，注入编排器即可；
  - 前端 R5 总结报告新增「跨轮记忆摘要」区展示。
- **模块内部逻辑**：
  ```
  每轮 purple 完成后：
    working.write(session_id=drill_id, {"round": r, "critique": ..., "review": ...})
    episodic.save(摘要)（按轮追加）
  下一轮 purple 输入附加 prior_rounds_summary =
    compactor.compress(历史 working/episodic, budget)  # 超 budget 时保留 decision+recent，其余 digest
  总结报告 purple_summary 增加 memory_trace: [round→摘要]
  ```
- **落盘文件清单**：`aegisos_agents/planning/orchestrator/cyber_orchestrator.py` 或 `backend/services/cyber_defense_service.py`（记忆注入，改）；`frontend/src/views/cyber/CyberDrillPanel.tsx`（总结区加记忆摘要，改）；对应单测。
- **验收标准**：跑 3 轮演练，第 3 轮紫队评审/总结中能引用第 1 轮结论（可在 mock 下断言摘要字段非空且含前轮关键点）；既有记忆子系统测试不破。
- **实测位置**：Drill tab 跑多轮 → 展开第 N 轮 critique 详情，观察其输入含 `prior_rounds_summary`；总结报告「跨轮记忆摘要」区可见。
- **风险与对策**：摘要质量依赖 compactor → 先验证字段链路（摘要确实生成并注入），语义质量用真实模型抽检。
- **可延申点**：演练结束后把整场经验写回 episodic，供下次演练 recall（形成跨演练学习）。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

## 4. Phase 3 · 动态异构拓扑与低熵通信（能力维度 b）

### R8 · 演练事件总线化 + 低熵增量推送（EventBus 联动）

- **一句话目标**：把 `drill_round` 战报发布到系统 EventBus，使 Monitor 等既有视图可订阅；并强化"每轮只推增量"的低熵设计。
- **比赛要求映射**：能力维度 b（架构与交互降噪创新，技术分 10）——抑制通信冗余、信息熵显著降低。
- **与其他模块的联系**：
  - `backend/core/composition.py` 的 EventBus（`/events` SSE 端点已存在，按 topic 过滤）；
  - `frontend/src/services/realtime/sse.ts` 前端订阅基建；
  - Monitor 视图可顺带展示 drill 事件流（不强制改 Monitor，先保证事件可达）。
- **模块内部逻辑**：
  ```
  R3 drill 路由在每轮 on_round 时：
    event_bus.publish(topic="drill.round", payload={round, new_steps, new_issues, carry_count, ...})
  低熵原则：payload 只含增量与摘要，不含全量 AttackChain/ResponsePlan；
  前端订阅 topic="drill.round" 即可在 Monitor/任意视图看到演练心跳。
  ```
- **落盘文件清单**：`backend/routers/drill.py`（发布事件，改）；`backend/routers/__init__.py` 若需注册 topic（视 EventBus 实现）；测试断言 topic 可达。
- **验收标准**：`GET /api/v1/events?stream=drill.round` 能看到演练轮次事件；payload 为增量摘要。
- **实测位置**：演练进行时打开 `http://localhost:8000/api/v1/events?stream=drill.round`（带 API Key）观察事件流；或前端 Monitor 页。
- **风险与对策**：EventBus 为轮询式 0.5s 拉取 → drill 事件量小，无性能问题；topic 命名与现有约定对齐。
- **可延申点**：R9 的 placement 信息并入 drill.round 增量事件。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

## 5. Phase 4 · 端-边-云异构资源自适应调度（能力维度 c）

### R9 · 演练阶段 placement 联动（调度位置标注）

- **一句话目标**：演练每个阶段（红/蓝/紫）标注执行位置（device/edge/cloud），复用既有 scheduler 卸载规则，把「端-边-云自适应调度」落到攻防场景演示上。
- **比赛要求映射**：能力维度 c —— 依据子任务实时性与敏感度自动选择推理位置。
- **与其他模块的联系**：
  - `aegisos_agents/planning/engine/scheduler/scheduler.py` 的 `schedule()`（latency<1s→device、<5s→edge、否则→cloud，降级 端→边→云）；
  - `infrastructure/nodes/descriptor.py` 的 `Tier`；
  - 前端 R5 轮次卡加「执行位置」徽标。
- **模块内部逻辑**：
  ```
  run_drill 每阶段构造 task_features（如 recon=高实时性→device/edge，
  purple_review=高算力需求→cloud），调用 schedule() 得 placement，
  写入轮次战报 phase.{red,blue,purple}.placement；
  前端徽标展示 device/edge/cloud + 卸载理由（latency/privacy）。
  ```
- **落盘文件清单**：`cyber_orchestrator.py`（placement 标注，改）；R3 战报契约对应字段；`CyberDrillPanel.tsx`（徽标，改）；测试。
- **验收标准**：战报含 placement 且符合调度规则；前端可见徽标。
- **实测位置**：Drill tab 轮次卡片上的 placement 徽标；展开详情看卸载理由。
- **风险与对策**：调度器为 mock 语义 → 标注真实调度结果即可，不强求真实异构节点（与项目"演示版跳过真实端边云"一致）。
- **可延申点**：与 `infrastructure/nodes/` 真实节点注册联动（演示版不做）。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

## 6. Phase 5 · 评测场景与交付物收尾（能力维度 d/e）

### R10 · 无人干预演示脚本 + 赛事材料文档补全

- **一句话目标**：输出一份"一键演示脚本"（无人干预跑完整 drill），并把攻防模块的设计/验收结论补进赛事材料文档，形成交付闭环。
- **比赛要求映射**：能力维度 d/e —— 可运行系统验证 + 材料文档交付。
- **与其他模块的联系**：汇总 R1-R9 成果；更新 `docs/`（含本档案）、`README.md`、必要时 `developer/CHANGELOG.md` 与赛事方案对应章节引用。
- **模块内部逻辑**：演示脚本 = 启动后端/前端 → 自动 POST /drill/start → 轮询至 done → 输出 summary JSON + 截图指引；材料文档 = 架构设计（本档案 R1/R3/R5 核心设计）+ 验收记录（R6 验收表）+ 实测证据（data/drills/ 样例）。
- **落盘文件清单**：`tooling/scripts/drill_demo.ps1`（新建，仿 sandbox.ps1 风格）；`README.md`/`developer/CHANGELOG.md`（改）；本档案「实测指南」区补最终版。
- **验收标准**：按脚本走完无人工干预；材料文档各章节与本档案一致。
- **实测位置**：命令行执行脚本；按 README 指引复现。
- **风险与对策**：脚本依赖 mock 模型即可跑通（真实模型可选）；文档与代码版本一致性由 0.1 规则保证。
- **可延申点**：录制演示视频素材。

- **开工确认**：[ ] 用户已确认（日期：____）
- **开工后记录**：
  - 改动文件清单：
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
  - 测试结果：
  - git commit：
  - 实测结果：
  - 遗留问题 / 下一步：

---

## 7. 实测指南（总览）

> 启动方式以项目既有 `start.ps1` / `start.sh` 为准（前端 Vite + 后端 uvicorn）。以下为攻防演练链路实测路径。

| 层 | 怎么启动 | 在哪测 | 看什么 |
|---|---|---|---|
| 后端 | `uvicorn backend.main:app`（或 start.ps1） | `http://localhost:8000/api/v1/...`（需 `X-API-Key`，见 `.env.example`） | R3 五个 drill 端点；`/docs` 页面直接调试 |
| 前端 | `npm run dev` | `http://localhost:5173` → 侧边栏 Cyber → **Drill tab** | 开始/停止按钮、轮次时间线、总结报告（R5） |
| 事件流 | 后端运行中 | `GET /api/v1/events?stream=drill.round` | drill 增量战报（R8 后） |
| 数据落盘 | 演练结束后 | `data/drills/<drill_id>.json` | 各轮战报 + 总结（R2） |
| 测试 | 命令行 | `pytest`（Python 全量）、前端测试命令、`npm run build` | 回归结果（R6） |
| git | 命令行 | `git log --oneline` | 每轮一个 commit，可回退（R0 规则） |

---

## 8. 变更日志

| 日期 | 轮次 | 变更 | commit |
|---|---|---|---|
| 2026-09-04 | R0 | 建档：任务切分 R0-R10 + 每轮设计档案/开工前报告模板 + git 约定 | （R0 提交后回填） |
| | | | |
