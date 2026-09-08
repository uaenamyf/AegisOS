# 攻防演练(Red-Blue-Purple 多 Agent)开工审查报告

> 本文档为**开工执行指令**。项目组读后即可按本计划落地开工。
> 落盘路线图 → `backend/routers` + `backend/services/cyber_defense_service.py` + `aegisos_agents/planning/orchestrator/cyber_orchestrator.py` + `frontend/src`。

---

## 1. 审查结论（摘要）

对当前攻防演练链路（红→蓝→紫）及前后端接口进行代码走查后，结论如下：

- **数据流主链路已存在且可用**：`CyberOrchestrator` 已实现 `run_red_chain` → `run_blue_chain` → `run_purple_review` 及多种变体（guardrail / handoffs / traced / goal / human-check），`protocol/cyber.py` 已定义完整数据契约，`backend/services/cyber_defense_service.py` 已有 `red_attack / blue_defense / purple_review`。
- **核心缺口（本次开工要补的）**：
  1. 缺少**一次点击跑完整三轮的"演练编排入口"**——现有端点均为单链路 REST 调用，需新增 `drill` 编排层及 SSE 流式战报。
  2. **"最大轮数暂定 5"的收敛循环不存在**——需要条件收敛 + 事件合成规则 + 轮次索引。
  3. **前端缺"开始演练"按钮 + 轮次时间线战报 + 收敛后总结报告展示页**。
- **无阻塞性重构**：现有 `comm_mode`（linear / bus）、guardrail/human-check 变体均保留，新增编排在其之上做收敛，不动既有 API。

**验收口径**：前端一键"开始演练" → SSE 推送 ≤N(默认 5) 轮战报 → 到达停止条件后固定产出 `PurpleReviewResponse` 总结报告并在前端展示。

---

## 2. 目标

1. **一键闭环**：从"开始演练"到"总结报告"之间全部自动推进，中间无需人工逐调用。
2. **收敛化**：默认最大轮次 `M=5`，按停止规则提前收敛（不再空转）。
3. **可观测**：每一轮通过 SSE 推送结构化战报（时间线），前端实时展示。
4. **可交付总结**：收敛后由紫队/编排器产出总结报告，前端给用户展示。
5. **可回放**：一次演练产出完整 `drill` 记录持久化，支持查询。

---

## 3. 核心设计

### 3.1 演练生命周期

```
开始演练 ──▶ Round 1 ─▶ Round 2 ─▶ … ─▶ Round ≤ M(默认5)
                    │                    │
                    │  每轮内部时序:      │
                    │  红(攻击) ─▶ 蓝(防御+告警) ─▶ 紫(评审)
                    │                    │
                    │  停止判定: 提前收敛 or 达到 M 轮
                    ▼
              总结报告(PurpleReviewResponse 聚合)  ──▶ 前端展示
```

### 3.2 收敛（停止条件，满足其一即止）

每轮紫队评审后评估，按优先级：

1. **完全收敛**：本轮紫队 `critique.valid == True` 且 `review.consistent == True` → 达标，结束。
2. **无进展收敛**：连续 2 轮紫队总结评述无实质新发现（以 `new_issue_count == 0` 且 `severity` 不升高为判定）→ 结束。
3. **轮次上限**：达到 `M = 5` → 强制结束。
4. **显式中止**：前端用户点击"停止"→ 立即结束并输出当前已收敛部分总结。

> `M` 通过可选请求字段 `max_rounds` 透传，默认 5；为空时路由层填充默认值。

### 3.3 事件合成规则（每轮的"事件流"如何生成并喂给蓝队）

现有蓝队入口 `run_blue_chain(event_stream: list[dict])` 需要"事件流"。规则：

- **Round 1**：把红队产出 `AttackChain.steps` 逐条映射为原始事件：
  ```json
  {
    "round": 1,
    "seq": <i>,
    "type": "attack_step",
    "source": "<step.from_asset>",
    "target": "<step.to_asset>",
    "technique": "<step.technique>",
    "success": <step.success>
  }
  ```
- **Round N+1**：在前一轮事件基础上**追加增量**，不重放全量旧链：
  - 保留上一轮全部事件（`carry_forward: true` 打标，保证蓝队有完整上下文记忆）。
  - 追加本轮红队新解析出的、`step_id` 未出现过的步骤为新增事件。
  - 若本轮红队无新步骤，则仅 `carry_forward`，配合收敛规则 2 触发无进展结束。
- **统一包装**：每轮最终 `event_stream` = `carried + new_events`，仍为 `list[dict]`，副本传入（不修改红队原始链），与现有 `run_blue_chain` 契约兼容。

### 3.4 轮次数据契约（SSE 战报事件 `drill_round`）

```jsonc
{
  "type": "drill_round",
  "round": 2,
  "max_rounds": 5,
  "status": "running",            // running | converged | no_progress | aborted | max_rounds
  "phase": {
    "red":   {"ok": true,  "steps": 4,  "new_steps": 1},
    "blue":  {"ok": true,  "alerts": 6, "triaged": 4, "plan": {...}},
    "purple":{"ok": true,  "critique": {...}, "review": {...},
              "converged": false, "new_issue_count": 0}
  },
  "event_id": "drill_0001-2"
}
```

事件流（SSE `event:` 名）：
- `drill_start`（演练开始，附带 `drill_id`、`max_rounds`）
- `drill_round`（每轮战报，见上）
- `drill_summary`（收敛后的总结报告，即最终 `PurpleReviewResponse` 聚合）
- `drill_error`（任一轮异常，携带阶段与错误信息，演练中止）
- `drill_done`（收尾，附带 `drill_id`）

### 3.5 总结报告

收敛时由编排层调用紫队已输出的 `critique + review`，聚合出总结报告（沿用 `PurpleReviewResponse` 结构，内容含跨轮摘要）：

```
{
  "conclusion":        "<跨轮总结>",
  "convergence_code":  "converged|no_progress|max_rounds|aborted",
  "rounds_executed":   N,
  "max_rounds":        5,
  "red_summary":       {链头、命中技术数、新步骤数按轮聚合},
  "blue_summary":      {告警总数、处置动作数按轮聚合},
  "purple_summary":    {总体 valid/consistent、issue 计数},
  "remaining_risks":   []  // 未收敛项
}
```

---

## 4. 任务清单（按依赖顺序）

### T1 后端：编排器新增收敛式演练入口
路径：`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`

新增公开方法：
- `run_drill(target_range: str, max_rounds: int = 5, on_round: Callable|None = None) -> dict`
  - 内部 `for round in 1..max_rounds`：按 3.3 合成 `event_stream` → `run_red_chain` → `run_blue_chain` → `run_purple_review`。
  - 每轮结束调用 `on_round(round_payload)`（用于上层推 SSE），再按 3.2 判停止。
  - 复用既有 `comm_mode` 分支逻辑；不修改既有 `run_*_chain` 语义。
- 收敛判定/事件合成拆为纯函数以便单测：
  - `_synthesize_event_stream(chain, prev_stream, round)`
  - `_evaluate_stop(critique, review, round, history) -> (stop: bool, code: str)`

### T2 后端：Service 层透出 drill
路径：`backend/services/cyber_defense_service.py`

新增：
- `run_drill(target_range, max_rounds=5, event_callback=None) -> dict`：包装编排器 `run_drill`，`event_callback` 逐个产出轮次/汇总/错误事件。
- 演练记录持久化：每次演练存 `data/drills/<drill_id>.json`，包含按轮战报与最终总结。

### T3 后端：新增 drill 路由（REST + SSE）
路径：`backend/routers/drill.py`（新建）

- `POST /api/v1/drill/start`：body `{target_range?, max_rounds?=5}` → `201 {drill_id, status: 'running', max_rounds}`；后台启动演练任务。
- `GET /api/v1/drill/{drill_id}/stream`：`text/event-stream` SSE（仿 `backend/routers/stream.py` 的 `StreamingResponse` + `_event_to_sse`），逐事件推 3.4 战报。
- `GET /api/v1/drill/{drill_id}`：拉取已发生轮次与当前状态（轮询兜底，SSE 断开时用）。
- `GET /api/v1/drill/{drill_id}/summary`：返回最终总结报告（若未收敛则 `409` + 当前中间态）。
- `POST /api/v1/drill/{drill_id}/abort`：显式中止（对应收敛规则 4）。

接线：在 `backend/routers/__init__.py` 增加 `drill` 并 `router.include_router(drill.router)`；`backend/main.py` 已挂载 `infra_router` 于 `/api/v1`，**需确认 drill 与既有汇合前缀一致**（当前 `router` 由 `routers/__init__` 输出，挂载点需并入）。

### T4 前端：键入 + API 服务
路径：`frontend/src/protocol/types.ts`、`frontend/src/services/api/cyber.ts`

- 类型新增：`DrillStatusResult`、`DrillRoundEvent`、`DrillSummaryResponse`、`StartDrillRequest`、`StartDrillResponse`。
- `cyberApi` 新增：
  - `startDrill(body)` → `POST /drill/start`
  - `openDrillStream(drillId, onEvent)` → 基于 `EventSource`/fetch-stream 订阅 SSE，`onEvent` 分发 `drill_start/round/summary/error/done`
  - `getDrill(drillId)`、`getDrillSummary(drillId)`、`abortDrill(drillId)`

### T5 前端：演练视图（开始按钮 + 时间线 + 总结报告）
路径：`frontend/src/views/CyberDrillView.tsx`（新建）

- **头部**：`开始演练` 按钮（输入 `target_range`、`最大轮数` 可选，默认 5）；演练进行中按钮变 `停止`。
- **轮次时间线战报**：垂直时间线，每轮一张卡片：
  - 轮次号、状态徽标（running/converged/no_progress/max_rounds/aborted）。
  - 红/蓝/紫三段摘要（steps、alerts、converged、new_issue_count）。
  - 未收敛时支持展开查看该轮 critique/review 详情。
  - 直播流更新：SSE 到达 `drill_round` 增量追加，滚动到最新。
- **总结报告区**：收到 `drill_summary` 后渲染 `3.5` 结构卡片（结论、收敛码、按轮统计、剩余风险）。查看历史：从 `getDrillSummary` 回填。

### T6 前端：路由与入口接入
路径：`frontend/src/App.tsx` / 路由表 + 导航

- 注册 `/cyber-drill` 路由，导航入口"攻防演练"。

### T7 测试
路径：`tests/`

- 编排函数单测：事件合成（Round1 / 追加 / 无新步骤 carry）、收敛判定 4 规则、`max_rounds` 边界。
- API 集成：`start` → SSE 可订阅 → `summary` 可拉取；mock 编排器（沿用现有 mock 服务）。
- 前端：演练视图交互（开始→时间线→总结）冒烟。

---

## 5. 验收标准

- [x] `POST /drill/start` 返回 drill_id，SSE 流从 `drill_start` 到 `drill_done` 完整推送。
- [x] 默认 5 轮，未达成收敛时恰在 5 轮结束；达成收敛时提前结束（≤5）。
- [x] 事件合成为增量追加，不破坏既有 `run_blue_chain` 契约。
- [x] 每次演练持久化可回放，`GET /drill/{id}` 可还原各轮战报。
- [x] 前端点击"开始演练"实时渲染轮次时间线，收敛后展示总结报告；"停止"可中止。
- [x] 既有红/蓝/紫 REST 端点（`/attack`、`/defense`、`/defense/purple-review` 等）行为不变，回归通过。

> R6 联调验收：六条全部勾选（2026-09-04）。HTTP 实测 `POST /drill/start` → SSE `drill_start→drill_round×3→drill_summary→drill_done`；`GET /drill/{id}` 返回 rounds_executed=3/convergence_code=converged；`GET /drill/{id}/summary` 200；`POST /drill/{id}/abort` 200；既有 attack/defense/purple 端点 200。

---

## 6. 非目标（本次不做）

- 不改动 `protocol/cyber.py` 现有模型字段（直接复用 `AttackChain`/`Alert`/`ResponsePlan`）。
- 不重写既有 `run_*_chain` 各变体（guardrail/handoffs/traced/goal/human-check 保留）。
- 不做蓝/红队的策略性升级，仅做收敛编排。
- 不做权限/多租户隔离（沿用现有后端鉴权约定）。

---

## 7. 参考锚点（已核实）

| 锚点 | 位置 |
| --- | --- |
| 编排器红/蓝/紫主方法 | `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（`run_red_chain` L445 / `run_blue_chain` L576 / `run_purple_review` L681；变体 L759/826/876/915/1182/1487/1509/1533/1735/1781） |
| 协议模型 | `protocol/cyber.py`：`AttackStep` L75 / `AttackChain` L104 / `Alert` L133 / `DefenseAction` L164 / `ResponsePlan` L191 / `ThreatIntel` L218 |
| Service 层 | `backend/services/cyber_defense_service.py`（`red_attack` L125 / `blue_defense` L176 / `purple_review` L235） |
| 已有 REST 路由 | `backend/routers/attack.py`、`defense.py`、`threat.py`；`drill.py` 需新建 |
| SSE 先例 | `backend/routers/stream.py`（`StreamingResponse` + `_event_to_sse` L61） |
| 前端 API 服务 | `frontend/src/services/api/cyber.ts`（`cyberApi` 现有 9 方法） |
| 前端类型 | `frontend/src/protocol/types.ts`（`RangeResponse` L250 / `RedAttackResponse` L264 / `BlueDefenseResponse` L270 / `PurpleReviewResponse` L277） |
| 前端框架 | React + Vite（`frontend/src/App.tsx`、`views/layout.tsx`） |

---

_版本：2026-09-04 · 最大轮数默认 5 · 状态：待开工_