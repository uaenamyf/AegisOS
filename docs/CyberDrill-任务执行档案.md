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
4. **git 提交**：每轮至少一次提交（Conventional Commits 风格，如 `feat(cyber-drill): ...`），commit message 只描述产品变更与验证，不写内部工具/流程名；本轮结束前工作区必须干净，以提交点作为回退锚点。
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
| **R1** | 编排器收敛式演练内核（`run_drill` + **证据化**事件合成/收敛纯函数，红队带轮次上下文可选） | 核心 | **R1.5** → R0 | a / 完整性40 / 技术20 / 效率15 | ✅ 已完成 |
| **R1.5** | Mock Provider 按轮演化升级（让多轮收敛真实可演示） | 核心 | R0 | a / d（前置） | ✅ 已完成 |
| **R2** | Service 层透出 `run_drill` + 演练记录持久化（`data/drills/`） | 核心 | R1 | e / 回放 | ✅ 已完成 |
| **R3** | 后端 drill 路由（REST + SSE 5 端点）+ 路由挂载 | 核心 | R2 | b / d | ✅ 已完成 |
| **R4** | 前端类型 + `cyberApi` drill 客户端（含 SSE 订阅） | 核心 | R3 | d | ✅ 已完成 |
| **R5** | 前端演练视图（开始/停止 + 轮次时间线 + 总结报告） | 核心 | R4 | d / e / 体验5 | ✅ 已完成 |
| **R6** | 端到端联调 + 全量回归 + 实测指南定稿 | 核心 | **R1-R5（含 R1.5）** | d | ✅ 已完成 |
| **R7** | **真实 LLM 接入 drill** + 运行时模式切换（mock/real）+ 前端徽标 | 核心升级 | R6 | d / 演示核心 | ✅ 已完成 |
| **R8** | 跨轮记忆与上下文压缩（紫队带历史决策摘要） | 延申 P1 | R7 | a（重点加分） | ✅ 已完成 |
| **R9** | 演练事件总线化 + 低熵增量推送（**复用既有 EventBus**，不新造） | 延申 P1 | R7 | b（技术分10） | ✅ 已完成 |
| **R10** | 端-边-云 placement 联动（演练阶段调度位置标注） | 延申 P2 | R9 | c | ✅ 已完成 |
| **R11** | 无人干预演示脚本 + 赛事材料文档补全收尾 | 延申 P2 | R7-R10 | d / e | ⬜ |
> **（2026-09-04 评审修订）** 原开工审查报告方案经代码核查发现 3 处硬伤，已修订见各轮「评审记录」：
> ① **R1 收敛判定**：mock 下 `valid/consistent` 恒真会首轮"完全收敛"，多轮收敛跑不出来 → 改为**证据驱动**（锚定新资产/新步骤）+ 新增 **R1.5 mock 按轮演化**；
> ② **R3 并发**：编排器是同步的，直接 `asyncio.create_task` 会阻塞事件循环 → 改 `asyncio.to_thread`；
> ③ **R8 不发新总线**：复用既有 `CyberOrchestrator.eventbus` + `install_hooks`，不新造。

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
  - git commit：`7c3b690`（`docs(cyber-drill): 建档——任务切分与执行档案（R0）`）
  - 实测结果：`git log --oneline` 可见初始提交；工作区干净
  - 遗留问题 / 下一步：进入 R1（编排器收敛式演练内核），开工前先向用户讲清 5 件事并等确认

---

## 2. Phase 1 · 一键闭环基础版（核心交付，对应开工审查报告 T1-T7）

### R1 · 编排器收敛式演练内核（先做「批判性修订」，见下方评审记录）

- **一句话目标**：在 `CyberOrchestrator` 上新增 `run_drill` 主循环——一次调用自动跑完「红→蓝→紫」≤M 轮并提前收敛，配套纯函数（事件合成、收敛判定）保证可单测。**同时修正原方案两个会让演示跑不通的硬伤**：① mock 下收敛恒真首轮即完，② 红队每轮无演化 → 多轮收敛无法真实推进。

> **评审记录：为什么原方案要改（基于代码核查，非臆测）**
> - **硬伤 A（收敛恒真）**：`backend/mocks/cyber_provider.py` 的 `_CyberMockProvider` 返回**静态固定**响应：`Critique.valid=True`（L161）、`Reviewer.consistent=True`（L170）恒定。原方案收敛规则 1（`valid and consistent → converged`）在 mock/演示模式下**第一轮就触发**，多轮对抗→收敛的过程根本跑不出来，时间线只有一张卡片——恰恰是评委最想看的亮点。
> - **硬伤 B（无演化）**：`run_red_chain(target_range)` 只吃 `target_range`（L402），同一目标每轮得到相同结果 → `AttackChain.steps` 恒定，增量事件合成永远无新步骤，「无进展收敛」「跨轮 carry」都失去意义。
> - **修正方向（不偏离主线）**：① 收敛判定从「状态恒真」改为「**证据驱动**」——锚定本轮是否产出**新资产/新发现/新步骤**，紫队对新增量给出评价；② 给 `run_red_chain` 增加**可选** `round`/`prev_context`（红队可带上一轮紫队反馈继续探测，默认不传=原行为，**既有调用零破坏**）；③ R1.5 把 mock 升级为**按轮演化**（第 r 轮才有机会发现新资产/新步骤），使收敛循环真实可演示。三者合起来让同一套代码在 mock（聚变演示）与真实 LLM（动态演化）下都能工作。

- **比赛要求映射**：
  - 能力维度 a：多轮循环 + 逐轮事件 carry + 「上一轮紫队反馈喂下一轮红队」，跨轮上下文连续、目标不漂移；
  - 完整性 40：「感知-规划-执行-反馈」闭环一次跑通；
  - 技术创新 20 / 效率 15：证据化收敛判定（4 规则提前终止）+ 增量事件合成（不重放全量）。
- **与其他模块的联系**：
  - 复用既有 `run_red_chain`（L402）/`run_blue_chain`（L465）/`run_purple_review`（L516）及其变体（guardrail/handoffs/traced/goal/human-check 全部保留、语义不变）；
  - **可选增强** `run_red_chain` 签名加 `round: int = 1, prev_context: dict | None = None`（默认值保持原语义，既有调用与测试零改动）；
  - 协议契约 `protocol/cyber.py` 只读复用（`AttackChain`/`Alert`/`ResponsePlan`/`PurpleReviewResponse`）；
  - 被 R1.5 mock 演化驱动、被 R2 Service 包装、被 R3 路由经回调推送 SSE、被 R7 记忆注入扩展。
- **模块内部逻辑**：
  ```
  run_drill(target_range, max_rounds=5, on_round=None, eventbus=None) -> dict
    history     = []      # 每轮收敛判定历史（含 new_assets/new_steps/new_issues）
    prev_stream = []      # 事件流累计（跨轮 carry）
    purples     = []      # 前序紫队评审（喂下一轮红队 prev_context）
    for round in 1..max_rounds:
      event_stream = _synthesize_event_stream(chain, prev_stream, round)   # 纯函数①
      red    = run_red_chain(target_range, round=round, prev_context=折紫队摘要)  # 演化式红队
      blue   = run_blue_chain(event_stream)        # 复用，契约 list[dict]（不变）
      purple = run_purple_review(red["chain"], blue["plan"], blue["alerts"])  # 复用
      new_assets, new_steps = _diff_vs_prev(red, prev_round)   # 新增：本轮新发现
      stop, code = _evaluate_stop(purple, new_assets=new_assets, new_steps=new_steps,
                                  round=round, history=history)                # 纯函数②（证据驱动）
      on_round(round_payload)                     # 回调供上层推 SSE
      if eventbus: eventbus.publish(topic="drill.round", payload=增量)          # 每轮增量事件（为 R8 预留）
      if stop: break
    聚合 PurpleReviewResponse + 跨轮摘要（conclusion / convergence_code /
    rounds_executed / red_summary / blue_summary / purple_summary / remaining_risks）
  ```
  - 纯函数① `_synthesize_event_stream(chain, prev_stream, round)`：
    - Round 1：`AttackChain.steps` 逐条映射为事件 `{round, seq, type:"attack_step", source, target, technique, success}`；
    - Round N+1：上一轮事件全部 `carry_forward: true` 保留 + 追加本轮 `step_id` 未出现过的新步骤为增量；
    - 无新步骤 → 仅 carry；返回 `list[dict]` 副本，不改动原始链。
  - 纯函数② `_evaluate_stop(purple, new_assets, new_steps, round, history) -> (stop, code)`，**证据驱动**，满足其一即停：
    1. **无新发现收敛**：本轮红队 `new_assets==0 and new_steps==0` 且紫队 `critique.valid and review.consistent` → `converged`（真实 LLM 下=攻击面已穷尽）；
    2. **持续收敛**：紫队连续 2 轮新问题 `new_issue_count==0` 且 severity 不升高，同时已稳定（无新发现）→ `no_progress`；
    3. 轮次上限：`round >= max_rounds` → `max_rounds`；
    4. 显式中止：外部 `abort_flag` → `aborted`。
    （不再依赖恒真的 `valid/consistent` 判断，改用「是否还有新证据可挖」驱动收敛。）
- **落盘文件清单**：
  - `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（新增 `run_drill` + 纯函数①`_synthesize_event_stream`/②`_evaluate_stop`/`_diff_vs_prev`；`run_red_chain` 可选参数 `round/prev_context`）
  - `tests/aegisos_agents/planning/orchestrator/test_drill_convergence.py`（新建：事件合成多轮 + 证据化收敛 4 规则 + max_rounds 边界 + 真实性回归）
- **验收标准**：单测全绿；同一测试在「mock 按轮演化（R1.5）」下能真实跑出 ≥2 轮且**确实在某轮收敛**（非首轮恒收敛）；默认 5 轮，未收敛恰在 5 轮结束；`run_red_chain` 不带新参时行为与旧版完全一致（既有 `tests/e2e/test_scenario1.py` 不破）；既有 594 项 Python 回归不破。
- **实测位置**：`pytest tests/aegisos_agents/planning/orchestrator/test_drill_convergence.py`；或 REPL：`CyberOrchestrator(mock=_CyberMockProvider()).run_drill("10.0.0.0/24", max_rounds=5)` 观察返回 `rounds_executed>1` 且含 `convergence_code`。
- **风险与对策**：真实 LLM 下每轮结果天然变化大，收敛判定必须有上限兜底（规则 3）；mock 非演化时断言会退化 → 收敛测试必须挂在 R1.5 的演化 mock 上，并保留一例「非演化 mock → 规则 3 兜底 max_rounds」作回归。
- **可延申点**：R7 在循环内注入记忆摘要；R9 在每阶段标注 placement。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（新增 `run_drill` + `_synthesize_event_stream`/`_diff_chain_steps`/`_evaluate_stop` 纯函数；`run_red_chain` 增可选 `round`、`run_purple_review` 增可选 `round`）；`tests/aegisos_agents/planning/test_drill_convergence.py`（新建，9 例）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：后端编排层新增 `CyberOrchestrator.run_drill(...)`——整个多轮演练的总循环，后续被 R2 `CyberDefenseService` 包装、被 R3 drill 路由调用推 SSE；前端目前尚不可见（R5 才做 Drill tab）；`run_red_chain`/`run_purple_review` 新增可选 `round` 参数，只在 run_drill 内显式传入时注入 `[round=N]` 触发 mock 演化，默认 `None` 保持旧签名，既有调用零破坏
  - 测试结果：新增 9 例全绿；全量 `608 passed`（基线 594 + 14 新增）；既有 `tests/e2e/test_scenario1.py` 与 `tests/aegisos_agents/planning/` 全部 130 例不破；ruff 全清
  - git commit：`58e8a43`（`feat(cyber-drill): R1 收敛式演练内核 run_drill——证据驱动收敛与跨轮事件合成`）
  - 实测结果：REPL `run_drill("10.0.0.0/24")` 返回 `rounds_executed=3`、`convergence_code="converged"`（R1：1步/valid=False/1缺口 → R2：2步(新step-2)/valid=True → R3：0新增/valid=True 收敛），多轮对抗→补齐→收敛叙事真实可演示
  - 遗留问题 / 下一步：进入 R2（Service 层包装 + 演练记录持久化），沿用本轮 `on_round` 回调喂 SSE；`prev_context`（R7 记忆注入）已预留，本轮先不加

---

### R1.5 · Mock Provider 按轮演化升级（让多轮收敛真实可演示）

- **一句话目标**：把 `_CyberMockProvider` 从「静态固定响应」升级为「按轮演化」——第 r 轮才暴露 asset-r / vuln-r / step-r，且第 1 轮让紫队先判 `valid=False`（留缺口），后续轮补齐后转 `valid=True`。这样 `run_drill` 的多轮对抗→收敛、增量事件、无进展判定全部**真实触发**，演示与单测都有意义。
- **比赛要求映射**：能力维度 a/d —— 无此项，`run_drill` 多轮收敛根本跑不起来，故这是 R1 能否验收的**前置**；同时让「逐轮演化出新证据」更贴近真实攻击面扩展。
- **与其他模块的联系**：只改 `backend/mocks/cyber_provider.py`（mock 层），不动 `aegisos_agents/tools/llms/mock_provider.py` 基类；**后端 mocks 需能从请求中读轮次上下文**（`run_red_chain` 传入 `round`）。影响面：`CyberDefenseService` 默认实例（`mock=_CyberMockProvider()`）与既有测试（非演化场景）需向后兼容——演化只在该 mock 收到含 round 上下文的 prompt 时触发，否则回退旧静态响应。
- **模块内部逻辑**：
  - 为 `/backend/mocks/cyber_provider.py` 增加**轮次上下文感知**：从 `run_red_chain` 注入的 `round` 拼进 recon/correlate/exploit 的 prompt 或 request.metadata；
  - 演绎规则：`assets` 规模随 round 增长（round r 才新增 asset-r），`findings`/`steps` 增量对应；第 1 轮让 critic 返回 `valid=False + issues:[...]`（缺口：未覆盖 asset-2 风险），第 2 轮红队补齐后 critic 返回 `valid=True`；
  - 保持「前缀匹配」回退机制不变，确保未显式传 round 的既有调用仍命中旧静态 key。
- **落盘文件清单**：
  - `backend/mocks/cyber_provider.py`（改：轮次演化响应）
  - `tests/backend/mocks/test_cyber_provider_evolution.py`（新建：r1 缺资产→r2 补齐；无 round 上下文时回退静态）
- **验收标准**：轮次演化 mock 单测通过；「演化 mock」驱动 `run_drill` 能稳定跑出多轮并在第 2 轮收敛；「旧静态 key」下既有 `test_scenario1.py` 与 `CyberDefenseService` 默认行为不变。
- **实测位置**：`pytest tests/backend/mocks/test_cyber_provider_evolution.py`；并在 R1 的 `test_drill_convergence.py` 里用演化 mock 验证 `convergence_code=="converged"` 且 `rounds_executed==2`。
- **风险与对策**：改 mock 影响面广 → 严格保证「无 round 上下文→旧行为」的兼容分支；演化表显式、可预期（单测断言 asset 数递增）。
- **可延申点**：真实 LLM 模式自动获得「逐轮演化」能力（无需 mock）；可为演示版提供可调演化步长。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`backend/mocks/cyber_provider.py`（新增 `_round_from_prompt` + `_evolve_recon`/`_evolve_exploit`/`_evolve_critic`，`complete()` 按 prompt 前缀分发轮次演化）；`tests/backend/test_cyber_provider_evolution.py`（新建，5 例）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：仅后端 mock 层；既有 `POST /api/v1/attack` 等端点经 `CyberDefenseService` 默认 `_CyberMockProvider()` 无 `[round]` 标记 → 完全回退旧静态响应（前端表现不变）；演化仅在 `run_drill` 显式传轮次时触发，为多轮收敛演示提供逐轮新证据
  - 测试结果：新增 5 例全绿；全量 `608 passed`；既有 `test_scenario1.py`、`test_cyber_endpoints.py`（含 `CyberDefenseService` 默认实例）不破；ruff 全清
  - git commit：`debf047`（`feat(cyber-drill): R1.5 攻防 mock 按轮演化——多轮收敛演练可真实演示`）
  - 实测结果：`pytest tests/backend/test_cyber_provider_evolution.py` 5 例通过；无 round 时 recon 仍 2 资产、critic 仍 valid=True（兼容分支生效）
  - 遗留问题 / 下一步：与 R1 一并交付；真实 LLM 模式天然获得逐轮演化能力，无需 mock

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
  - `backend/services/cyber_defense_service.py`（新增 5 个方法：`drill`/`get_drill`/`list_drills`/`_persist_drill`/`_drill_record_path`）
  - `tests/backend/test_drill_service.py`（新建：run/get/list/落盘还原/on_round 回调/缺失返回 None）
- **验收标准**：单测通过；演练后 `data/drills/<drill_id>.json` 可还原各轮战报与总结。
- **实测位置**：`pytest tests/backend/test_drill_service.py`；REPL 调 `CyberDefenseService().drill(...)` 后查看 `data/drills/` 生成文件。
- **风险与对策**：并发写文件 → 按 drill_id 独立文件；`data/drills/` 已入 `.gitignore`（运行时产物不入版本库），回放靠磁盘文件。
- **可延申点**：R10 材料文档直接引用 `data/drills/` 样例作为交付证据。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`backend/services/cyber_defense_service.py`（新增 `drill`/`get_drill`/`list_drills`/`_persist_drill`/`_drill_record_path`，导入 `json`/`datetime`/`Path`）；`tests/backend/test_drill_service.py`（新建，6 例）；`.gitignore`（`data/drills/`）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：后端 Service 层；`drill()` 包装 R1 编排器的 `run_drill` 并把完整记录写盘；被 R3 路由调用（R3 未做前前端不可见）；`get_drill()/list_drills()` 为 SSE 断线轮询兜底与回放提供数据源
  - 测试结果：新增 6 例全绿；全量 `614 passed`（基线 608 + 6）；ruff 全清
  - git commit：`8276490`（`feat(cyber-drill): R2 Service 层透出 drill + 演练记录持久化到 data/drills`）
  - 实测结果：REPL `CyberDefenseService().drill('10.0.0.0/24')` 落盘 `data/drills/drill_10.0.0.0_24.json`（3 轮收敛，含每轮战报+总结）；`get_drill` 能还原、`list_drills` 返回元信息、缺失返回 None
  - 遗留问题 / 下一步：`status` 字段留给 R3 异步路由层管理（同步编排完成即返回，无 running 态）；进入 R3（后端 drill 路由 + SSE）

---
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
  > **并发关键（评审修订）**：现有编排器 `run_drill` 为**同步**逻辑，若直接 `asyncio.create_task` 会在事件循环里阻塞其他请求 → 用 `asyncio.to_thread(run_drill, ...)`（或 `run_in_executor`）把同步编排放到线程池，SSE 生成器用 `asyncio.Queue` + 线程→队列回调解耦；这样同时保留 FastAPI 异步响应模型。
- **实测位置**：`uvicorn backend.main:app` 起服务后：
  - `curl -X POST http://localhost:8000/api/v1/drill/start -H "X-API-Key: <key>" -H "Content-Type: application/json" -d '{"target_range":"10.0.0.0/24"}'`
  - 浏览器打开 `http://localhost:8000/api/v1/drill/<id>/stream` 看 SSE 流；FastAPI `/docs` 页面可直接调试 5 个端点。
- **风险与对策**：SSE 连接断开后任务仍在跑 → 状态/总结走 R2 磁盘与内存兜底；后台任务异常 → `drill_error` 事件 + 状态置 failed。
- **可延申点**：R8 将 drill_round 同时发布到 EventBus，Monitor 视图可订阅。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`backend/routers/drill.py`（新建：`DrillRuntime` 线程安全事件队列 + 5 端点）；`backend/routers/__init__.py`（挂载 drill）；`backend/services/cyber_defense_service.py`（`drill()` 增可选 `drill_id` 透传，保证 registry/落盘/SSE 三处 ID 一致）；`aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（`run_drill` 增可选 `drill_id` 透传）；`tests/backend/test_drill_api.py`（新建，10 例）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：新增 `/api/v1/drill/*` 5 端点（带 `X-API-Key` 鉴权，走既有网关前缀）；SSE `GET /api/v1/drill/{id}/stream` 实时推 `drill_start→drill_round*→drill_summary→drill_done`；前端目前尚不可见（R4/R5 才接前端）；内部调用链：路由 → `service.drill()` → `orchestrator.run_drill()` → 红蓝紫链；SSE 生成器从 `queue.Queue` 消费（`asyncio.to_thread` 解耦，不阻塞事件循环）
  - 测试结果：新增 10 例全绿（start 201/stream 生命周期/404 各端点/summary 收敛码/abort）；全量 `624 passed`（上轮 614 + 10）；ruff 全清
  - git commit：`b09bb2e`（`feat(cyber-drill): R3 drill 路由——REST+SSE 5 端点（to_thread 并发 + 事件队列）`）
  - 实测结果：TestClient 冒烟——start 201 返回 `drill-<uuid>`；队列事件 `[drill_start, drill_round×3, drill_summary, drill_done]` 无重复；get 返回 done+3 轮；summary 返回 convergence_code=converged；abort 200；未知 id 全 404
  - 遗留问题 / 下一步：进入 R4（前端类型 + cyberApi drill 客户端 + SSE 订阅）；R8 将 drill_round 发布到 EventBus 已预留（`_run` 内 emit 点）

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
- **可延申点**：R9 后可在 Monitor 视图复用同一订阅封装。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`frontend/src/protocol/types.ts`（新增 drill 类型族：StartDrillRequest/Response、DrillRound/Record、DrillSummaryResponse、DrillEventName/Event）；`frontend/src/services/api/cyber.ts`（新增 startDrill/getDrill/getDrillSummary/abortDrill/openDrillStream）；`frontend/src/services/api/__tests__/cyber.drill.test.ts`（新建，8 例）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：类型与 API 方法在 `@/protocol/types` 与 `@/services/api/cyber`；openDrillStream 用 EventSource 连 `/api/v1/drill/{id}/stream?api_key=…`（EventSource 无法带 Header，走后端 Query 兜底鉴权），按 `event:` 名分发 5 类事件，返回关闭函数；UI 尚不可见（R5 视图消费）
  - 测试结果：vitest 新增 8 例全绿（mock apiClient 断言路径/编码 + mock EventSource 断言 URL、事件分发、畸形载荷忽略、close）；全量前端 4 文件 32 tests 全过；`tsc -b` 类型检查通过（`tsc --noEmit` 与 composite 项目冲突 TS6305，改用 build 模式验证）
  - git commit：`9b4f2f0`（`feat(cyber-drill): R4 前端 drill 类型 + cyberApi 客户端（SSE 订阅封装）`）
  - 实测结果：`npm test` 全绿（32 passed）；`npx tsc -b` exit 0；R5 可直接 `cyberApi.startDrill()` 起演练、`openDrillStream()` 收战报
  - 遗留问题 / 下一步：进入 R5（前端 Drill 演练视图：开始/停止 + 轮次时间线 + 总结报告）

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
- **可延申点**：R8 总结报告加「跨轮记忆摘要」区；R10 轮次卡加执行位置徽标。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`frontend/src/views/cyber/CyberDrillPanel.tsx`（新建：开始/停止 + SSE 轮次时间线 + 总结卡 + 断线轮询兜底）；`frontend/src/views/cyber/CyberView.tsx`（TABS 追加 Drill + 渲染分支）；`frontend/src/index.css`（drill 面板/轮次卡/徽标/总结样式）；`frontend/src/services/api/cyber.ts`（`openDrillStream` 加可选 `onError` 回调通道——SSE 断开后通知面板走 `getDrill` 轮询）；`frontend/src/views/cyber/__tests__/CyberDrillPanel.test.tsx`（新建 6 例）；`frontend/src/views/cyber/__tests__/cyber-views.test.tsx`（tab 断言 4→5 + cyberApi mock 补 drill 方法 + Drill tab 切换例）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：侧边栏 Cyber → 新增 `Drill` tab；面板一键「开始演练」→ `cyberApi.startDrill` → `openDrillStream` 订阅 SSE（EventSource + query api_key）→ 逐轮卡片实时追加（红 findings/new_steps、蓝 triaged/plan actions、紫 valid/issues/convergence_code，可展开）→ 收敛后总结卡（conclusion/code/rounds）；「停止」→ `abortDrill`；SSE 断开 → `onError` → `getDrill` 2s 轮询补拉；卸载时关流+停轮询
  - 测试结果：新增 7 例（面板 6 + Drill tab 1）；全量前端 5 文件 39 passed（上轮 32 + 7）；`tsc -b` 通过；eslint 全清
  - git commit：`fdce5a7`（`feat(cyber-drill): R5 前端 Drill 演练视图——开始/停止 + SSE 轮次时间线 + 总结报告`）
  - 实测结果：单测覆盖开始→逐轮时间线→总结→停止→断线兜底全链路；修复一个真实闭包 bug——`handleStreamError` 在 `setDrillId` 前渲染创建、捕获旧 `drillId=null` 导致断线轮询永不触发，改用 `drillIdRef` 镜像解决（测试暴露）
  - 遗留问题 / 下一步：进入 R6（端到端联调 + 全量回归 + 实测指南定稿）

---

### R6 · 端到端联调 + 全量回归 + 实测指南定稿

- **一句话目标**：把 R1-R5 串起来跑通完整演示链路，全量回归，并把「实测指南」定稿写进本档案。
- **比赛要求映射**：能力维度 d —— 可运行系统的完整验证；系统性能与效率 15 —— 回归证明鲁棒性/兼容性。
- **与其他模块的联系**：覆盖 backend（R1、R1.5、R2、R3）、frontend（R4-R5）、tests（全量）、docs（本档案实测指南区）。
- **模块内部逻辑**：按 `start.ps1` 启动 → 前端 Drill tab 完整跑一次演练 → 逐条核对开工审查报告 §5 验收表 → `pytest` 全量 + 前端测试 + `tsc`/build → 修复联调中暴露的小问题。
- **落盘文件清单**：可能的小修 bug；本档案「实测指南」区定稿；必要时 `README.md` 补演示入口说明。
- **验收标准**：开工审查报告 §5 六条验收全勾；Python 全量 + 前端测试全绿。
- **实测位置**：完整路径 = 后端 `uvicorn backend.main:app`（或 `start.ps1`）→ 浏览器 `http://localhost:5173` → Cyber → Drill tab。
- **风险与对策**：联调暴露跨层字段不一致 → 以 `protocol/cyber.py` 与 R3 契约为基准对齐，优先改前端/路由层，不动协议层。
- **可延申点**：为 R7-R10 提供稳定基线。

- **开工确认**：[x] 用户已确认（日期：2026-09-04）
- **开工后记录**：
  - 改动文件清单：`backend/routers/drill.py`（小修：`GET /drill/{id}` 补 `rounds_executed`/`convergence_code` 字段——联调暴露的跨层不一致）；`docs/CyberDrill-开工审查报告.md`（§5 六条验收打勾 + R6 联调验收附注）；本档案（R6 记录 + 实测指南区定稿 + changelog）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：`GET /api/v1/drill/{id}` 响应补齐前端 `DrillRecord` 契约所需字段（R5 面板断线轮询兜底读取 `rec.rounds`/`rec.summary`/`rec.convergence_code`）；实测指南 §7 定稿完整演示链路
  - 测试结果：后端全量 `624 passed`（上轮 624，无回归）；前端全量 5 文件 `39 passed`；`tsc -b` exit 0；ruff 全清
  - git commit：`9888236`（`fix(cyber-drill): R6 联调小修——GET /drill/{id} 补 rounds_executed/convergence_code + 验收报告打勾`）
  - 实测结果：真实 HTTP 端到端（uvicorn 起服）——验收 1 `start` 201 + SSE `drill_start→drill_round×3→drill_summary→drill_done` 完整；验收 2 `rounds_executed=3`/`convergence_code=converged`（≤5 提前收敛）；验收 4 `summary` 200 + `data/drills/` 落盘可回放；验收 5 `abort` 200；验收 6 既有 attack/defense/purple 端点 200 全过
  - 遗留问题 / 下一步：核心路线 R1-R6 全部完成；经复盘将真实 LLM 接入提升为 R7（用户拍板：默认真实调用 + 前端模式切换），跨轮记忆顺延为 R8

---

### R7 · 真实 LLM 接入 drill + 运行时模式切换（mock/real）+ 前端徽标

> **（2026-09-04 复盘修订）** 原 R7 为「跨轮记忆」，经复盘发现 R1-R6 全部跑在 mock 预置响应上、真实推理从未验证——这恰是比赛原文「无人干预自主全链路推理」的灵魂。用户拍板：**真实 LLM 接入提升为 R7（默认真实调用）**，跨轮记忆顺延为 R8。

- **一句话目标**：drill 链路接真实 LLM（DeepSeek），运行时可在 mock / real 间切换，前端头部徽标可视化当前模式并支持点击切换；默认真实调用。
- **比赛要求映射**：能力维度 d —— 可运行系统的真实自主推理闭环；「默认 mock 白做了」→ 双模式可切换，mock 作保底演示。
- **与其他模块的联系**：
  - `backend/core/runtime_mode.py`（新建）——运行时模式单例，懒缓存双编排器，切换即时生效；
  - `backend/routers/system.py`（新建）——`GET/POST /api/v1/system/mode`；
  - `backend/services/cyber_defense_service.py` —— 显式注入优先、否则动态跟随运行时模式；
  - `backend/core/composition.py` —— 共享编排器改走 `runtime_mode.get_orchestrator()`；
  - `aegisos_agents/tools/llms/sdk_provider.py` —— 既有双模式 Provider（DeepSeek 走 OpenAI 兼容端点）；
  - 前端 `systemApi` + `LlmModeBadge`（CyberView 头部）。
- **模块内部逻辑**：
  ```
  .env（gitignore 保护）：OPENAI_BASE_URL=https://api.deepseek.com/v1
    OPENAI_API_KEY=sk-…  OPENAI_DEFAULT_MODEL=deepseek-chat  AEGIS_USE_MOCK=false
  runtime_mode.init()  → 有 Key 且未强制 mock → real；否则 mock（无 Key 自动降级）
  GET /system/mode     → {mode, model, provider, has_key, available}
  POST /system/mode    → {mock|real} 切换（无 Key 时 real 返回 400 INVALID_MODE）
  service 每次调用经 get_orchestrator() 取当前模式编排器（mock=预置响应表 / real=SDK Model）
  前端 LlmModeBadge：绿点+“真实 LLM deepseek-chat” / 黄点+“Mock 模式”，点击切换
  ```
- **落盘文件清单**：
  - `backend/core/runtime_mode.py`（新建）
  - `backend/routers/system.py`（新建）
  - `backend/services/cyber_defense_service.py`（改：动态编排器）
  - `backend/core/composition.py`（改：共享编排器走 runtime_mode）
  - `backend/main.py`（改：挂载 system 路由 + lifespan 初始化）
  - `conftest.py`（改：测试强制 mock + 中和 .env 的 tracing 开关）
  - `tests/backend/test_system_mode.py`（新建）
  - `frontend/src/protocol/types.ts`、`services/api/system.ts`（新建）、`views/cyber/LlmModeBadge.tsx`（新建）、`CyberView.tsx`、`index.css`、`__tests__/LlmModeBadge.test.tsx`（新建）、`cyber-views.test.tsx`
  - `tooling/configs/.env`（新建，gitignore 保护，不进版本库）
- **验收标准**：`GET /system/mode` 返回 real（有 Key）；POST 可切换且切换后 drill 行为改变；前端徽标显示并切换；测试环境强制 mock 无回归。
- **实测位置**：`GET /api/v1/system/mode` 返回 `{mode: real, model: deepseek-chat}`；真实 LLM 连通性冒烟（DeepSeek 返回 LLM_OK）；前端 Cyber 页头部徽标。
- **风险与对策**：真实模型不收敛/超时 → mock 一键切回；`.env` 的 `OPENAI_AGENTS_DISABLE_TRACING=true` 会全局禁用 SDK tracing 导致组合测试失败 → conftest 先设 false 中和（_load_dotenv 不覆盖已有变量）；Key 泄漏 → .env 已 gitignore。
- **可延申点**：R8 跨轮记忆在真实链路上验证；演示材料以真实演练截图作证据。

- **开工确认**：[x] 用户已确认（日期：2026-09-04，含 DeepSeek Key 与「默认真实」指令）
- **开工后记录**：
  - 改动文件清单：`runtime_mode.py` / `system.py` / `cyber_defense_service.py` / `composition.py` / `main.py` / `conftest.py` / `test_system_mode.py` / `types.ts` / `system.ts` / `LlmModeBadge.tsx` / `CyberView.tsx` / `index.css` / `LlmModeBadge.test.tsx` / `cyber-views.test.tsx` / `tooling/configs/.env`（gitignored）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：Cyber 页头部徽标（绿点真实 LLM / 黄点 Mock，可点击切换）；后端 `/api/v1/system/mode` GET/POST；service 每次调用动态取编排器（切换即时生效）
  - 测试结果：后端全量 `627 passed`（624 + system mode 3）；前端全量 6 文件 `43 passed`；`tsc -b` exit 0；eslint 0 error；ruff 全清
  - git commit：`54f45de`（`feat(cyber-drill): R7 真实 LLM 接入——运行时模式切换（mock/real）+ 前端徽标`）
  - 实测结果：uvicorn 起服后 `GET /system/mode` → `{mode: real, model: deepseek-chat, provider: deepseek}`；POST mock/real 往返切换 200；真实 LLM 连通性冒烟（DeepSeek `LLM_OK`）；前端 build 通过
  - 遗留问题 / 下一步：真实多轮演练完整跑一遍（成本/时间可控时）；进入 R8 跨轮记忆（原 R7 顺延）

---

## 3. Phase 2 · 超长程上下文连续性与记忆保持（能力维度 a）

### R8 · 跨轮记忆与上下文压缩（紫队带历史决策摘要）

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

- **开工确认**：[x] 用户已确认（日期：2026-09-05）
- **开工后记录**：
  - 改动文件清单：
    - `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（改）——`run_drill` 新增 `memory` / `memory_budget` 可选参数；`run_purple_review` 新增 `prior_rounds_summary` 可选参数；新增 `_store_round_memory` 辅助（写 decision 决策包 + normal 细节包 → `MemoryStore.compress` 压缩 → 生成下轮摘要）；round_data 条件性携带 `prior_rounds_summary`，summary 新增 `memory_trace`
    - `backend/services/cyber_defense_service.py`（改）——`drill` 透传 `memory` / `memory_budget`，默认注入服务持有 `_memory`（零破坏）
    - `frontend/src/protocol/types.ts`（改）——`DrillRound.prior_rounds_summary`、`DrillSummaryResponse.memory_trace` + `DrillMemoryTraceEntry`
    - `frontend/src/views/cyber/CyberDrillPanel.tsx`（改）——轮次卡记忆徽标 🧠 mem（title 含摘要）、总结报告「跨轮记忆摘要」区
    - `frontend/src/index.css`（改）——`badge--info` + `.cyber-drill__memory*` 样式
    - `tests/aegisos_agents/planning/test_drill_memory.py`（新）——R8 单测 5 个
    - `tests/backend/test_drill_service.py`（改）——新增默认启用记忆 / 自定义注入 2 个测试
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
    - 前端 Drill tab：每轮卡片出现 🧠 mem 徽标（第 2 轮起）；总结报告新增「Cross-Round Memory（跨轮记忆摘要）」区逐轮展示摘要
    - 内部：`run_drill` 循环内每轮 purple 后调用 `_store_round_memory`；下一轮 `run_purple_review(..., prior_rounds_summary=...)` 注入 critic/reviewer prompt；Service `drill` 默认携带记忆
  - 测试结果：后端全量 `pytest` 634 passed（新增 7 个）；前端 `tsc -b` 通过 + `vitest` 43 passed；既有 drill/memory 测试零破坏
  - git commit：`0959d05` feat(cyber-drill): R8 跨轮记忆与上下文压缩——紫队带历史决策摘要
  - 实测结果：mock 实测 3 轮收敛；第 2 轮摘要含第 1 轮结论（"攻击链未覆盖内部资产 asset-3（10.0.0.15:redis 高危入口）"）；`memory_trace` 每轮一条（stored_task_id / compressed_count / next_round_summary）；`memory_budget=10` 时 6 包压成 4 包（3 decision 保留 + 1 digest 溯源 :detail）——决策保留 + 细节压缩生效
  - 遗留问题 / 下一步：摘要语义质量依赖 compactor，真实 LLM 模式抽检未做（mock 已验证字段链路）；下一步 R9「演练事件总线化 + 低熵增量推送」（能力维度 b）

---

## 4. Phase 3 · 动态异构拓扑与低熵通信（能力维度 b）

### R9 · 演练事件总线化 + 低熵增量推送（EventBus 联动）

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

- **开工确认**：[x] 用户已确认（日期：2026-09-05）
- **开工后记录**：
  - 改动文件清单：
    - `protocol/event.py`（改）——`EventType` 新增 `DrillRound = "drill.round"`（枚举值即总线 topic）
    - `backend/routers/drill.py`（改）——`DrillRuntime.__init__` 新增 `event_bus` 可选参数（None 时取全局 composition 单例）；`on_round` 回调发布低熵增量事件（round / drill_id / new_steps / new_issues / valid / converged / carry_forward_count / prior_summary，不含全量链/计划）
    - `tests/backend/test_drill_events.py`（新）——R9 单测 4 个（发布 / 低熵 payload / carry 增量 / API 级可达）
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
    - `GET /api/v1/events?stream=drill.round` 可订阅演练轮次事件（0.5s 轮询、按 topic 过滤）；Monitor/任意视图可接入
    - 内部：`DrillRuntime._run` 的 on_round 回调里 `event_bus.publish(Event(event_type=EventType.DrillRound, ...))`；事件总线复用既有 composition 全局单例，未新造总线
  - 测试结果：后端全量 `pytest` 638 passed（新增 4 个）；前端未改动无需回归
  - git commit：`72d3d13` feat(cyber-drill): R9 演练事件总线化——drill.round 低熵增量事件可订阅
  - 实测结果：API 级实测 3 轮事件全部发布（round 1/2/3）；carry_forward_count 0→1→2（首轮全量、后续只推增量）；第 2 轮起 prior_summary 携带 R8 跨轮摘要（"攻击链未覆盖内部资产 asset-3（10.0.0.15:redis 高危入口）"）——事件总线与跨轮记忆联动
  - 遗留问题 / 下一步：R9 可延申点——placement 信息并入 drill.round（与 R10 联动）；下一步 R10「演练阶段 placement 联动」（能力维度 c）

---

## 5. Phase 4 · 端-边-云异构资源自适应调度（能力维度 c）

### R10 · 演练阶段 placement 联动（调度位置标注）

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
- **实测位置**：Drill tab 轮次卡片上的 placement 徽标；展开详情看卸载理由。
- **风险与对策**：调度器为 mock 语义 → 标注真实调度结果即可，不强求真实异构节点（与项目"演示版跳过真实端边云"一致）。
- **可延申点**：与 `infrastructure/nodes/` 真实节点注册联动（演示版不做）。

- **开工确认**：[x] 用户已确认（日期：2026-09-05）
- **开工后记录**：
  - 改动文件清单：
    - `aegisos_agents/planning/orchestrator/cyber_orchestrator.py`（改）——新增 R10 模块常量（`_DRILL_MODEL_POOL` 三层候选池 / `_DRILL_PHASE_FEATURES` 各阶段任务特征 / `_DRILL_TIER_SEMANTICS` 层级语义）；新增 `_phase_placements()` 辅助（构造 Task → 调 `scheduler.schedule()` → 得 tier/model_id/reason，调度异常回退云侧）；round_data 注入 `phase.{red,blue,purple}`
    - `frontend/src/protocol/types.ts`（改）——`DrillPhasePlacement` / `DrillRoundPhases` 类型，`DrillRound.phase` 可选字段
    - `frontend/src/views/cyber/CyberDrillPanel.tsx`（改）——轮次卡三阶段 tier 徽标（device/edge/cloud 配色），title 含卸载理由
    - `frontend/src/index.css`（改）——`.badge--tier*` 三色徽标样式 + `.cyber-drill__placement`
    - `tests/aegisos_agents/planning/test_drill_placement.py`（新）——R10 单测 4 个
  - 改动体现在项目哪里 / 前端哪里可见 / 内部调用位置：
    - 前端 Drill tab 轮次卡：red/blue/purple 三枚 tier 徽标（device 绿 / edge 黄 / cloud 蓝），悬停看卸载理由（如"攻击链实时生成（超低延迟） → 端侧·超低延迟/本地隐私"）
    - 内部：`run_drill` 每轮 `round_data["phase"] = self._phase_placements()`；复用既有 `scheduler.schedule()` 五步策略 + `Task` 契约 + `Tier` 语义，未新造调度逻辑
  - 测试结果：后端全量 `pytest` 642 passed（新增 4 个）；前端 `tsc -b` + `vitest` 43 passed；既有 drill 测试零破坏
  - git commit：`79f963c` feat(cyber-drill): R10 演练阶段 placement 联动——端-边-云自适应调度标注
  - 实测结果：3 轮演练各阶段稳定——red→device（device_firewall，超低延迟）、blue→edge（edge_gateway，低延迟）、purple→cloud（cloud_gpu，高算力），卸载理由语义清晰，跨轮稳定
  - 遗留问题 / 下一步：演示版用候选池非真实节点（档案风险对策已声明）；下一步 R11「无人干预演示脚本 + 赛事材料文档补全」（能力维度 d/e，截止 2026-09-15）

---

## 6. Phase 5 · 评测场景与交付物收尾（能力维度 d/e）

### R11 · 无人干预演示脚本 + 赛事材料文档补全

- **一句话目标**：输出一份"一键演示脚本"（无人干预跑完整 drill），并把攻防模块的设计/验收结论补进赛事材料文档，形成交付闭环。
- **比赛要求映射**：能力维度 d/e —— 可运行系统验证 + 材料文档交付。
- **与其他模块的联系**：汇总 R1-R10 成果；更新 `docs/`（含本档案）、`README.md`、必要时 `developer/CHANGELOG.md` 与赛事方案对应章节引用。
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
| 事件流 | 后端运行中 | `GET /api/v1/events?stream=drill.round` | drill 增量战报（R9 后） |
| 数据落盘 | 演练结束后 | `data/drills/<drill_id>.json` | 各轮战报 + 总结（R2） |
| 测试 | 命令行 | `pytest`（Python 全量）、前端测试命令、`npm run build` | 回归结果（R6） |
| git | 命令行 | `git log --oneline` | 每轮一个 commit，可回退（R0 规则） |

---

## 8. 变更日志

| 日期 | 轮次 | 变更 | commit |
|---|---|---|---|
| 2026-09-04 | R0 | 建档：任务切分 R0-R10 + 每轮设计档案/开工前报告模板 + git 约定 + 仓库初始化 | `7c3b690` |
| 2026-09-04 | 修订 | 评审修订：①新增 R1.5 mock 按轮演化；②R1 收敛改证据驱动；③R3 并发改 asyncio.to_thread；④R8 复用既有 EventBus；⑤补齐 R2 行 | `9bde203` |
| 2026-09-04 | R1.5 | mock 按轮演化（asset-3/step-2/紫队缺口补齐），无 round 回退静态零破坏 | `debf047` |
| 2026-09-04 | R1 | 收敛式演练内核 `run_drill` + 证据驱动收敛 + 跨轮事件合成；全量 608 passed | `58e8a43` |
| 2026-09-04 | R2 | Service 层透出 drill + 演练记录持久化 `data/drills/`；全量 614 passed | `8276490` |
| 2026-09-04 | R3 | drill 路由 REST+SSE 5 端点（to_thread 并发 + 事件队列）；全量 624 passed | `b09bb2e` |
| 2026-09-04 | R4 | 前端 drill 类型 + cyberApi 客户端（SSE 订阅封装）；前端 vitest 32 passed、tsc -b 通过 | `9b4f2f0` |
| 2026-09-04 | R5 | 前端 Drill 演练视图（开始/停止 + SSE 轮次时间线 + 总结报告）；前端 vitest 39 passed、tsc -b/eslint 通过 | `fdce5a7` |
| 2026-09-04 | R6 | 端到端联调 + 六条验收全勾 + 联调小修（GET /drill/{id} 补字段）；后端 624/front 39/tsc 全绿 | `9888236` |
| 2026-09-04 | R7 | 真实 LLM 接入 drill + 运行时模式切换（mock/real）+ 前端徽标；后端 627/front 43 全绿；DeepSeek 连通性冒烟通过 | `54f45de` |
| 2026-09-05 | R8 | 跨轮记忆与上下文压缩（紫队带历史决策摘要）；后端 634/front 43 全绿；mock 实测 3 轮收敛携带前轮摘要 | `0959d05` |
| 2026-09-05 | R9 | 演练事件总线化（drill.round 低熵增量事件可订阅）；后端 638 全绿；API 实测 3 轮事件 + carry 增量 + 跨轮摘要联动 | `72d3d13` |
| 2026-09-05 | R10 | 演练阶段 placement 联动（red→device / blue→edge / purple→cloud 三阶段标注）；后端 642 全绿；前端 43 全绿 | `79f963c` |
| | | | |
| | | | |
| | | | |
| | | | |
