# CyberDrill（攻防演练）模块 · 任务执行档案

> **本文件是攻防演练（Red→Blue→Purple 多 Agent 演练）模块的唯一执行档案**：
> 系统全景、模块地图、核心技术原理、每轮「开工前报告」与「开工后记录」、比赛要求映射、
> 验收与实测结论，全部沉淀在此。每开一轮新任务前必须回到本文档对应小节，先讲清楚再动手。
>
> 配套文档：
> - `docs/CyberDrill-开工审查报告.md` —— 技术审查结论、验收口径、T1-T7 原始任务清单
> - `docs/ARCHITECTURE.md` —— 全系统架构仪表盘（各域实现状态）
> - 根目录 `XH-...比赛方案.pdf` —— 赛事原文（评分标准/能力维度）

---

## 0. 使用规则（每次开工前必读）

### 0.1 每轮循环工作流

1. **开工前（必做）**：回到本文档对应 Round 小节，把「开工前报告」的 5 件事讲给用户：
   ① 要交付什么（新增/改造哪个**模块**、提供什么能力） → ② 对应比赛什么要求（能力维度/评分点） → ③ 与其他模块的联系（讲**实际模块**：后端哪个功能模块、前端哪个可见按钮/面板） → ④ 模块内部逻辑（流程/契约/技术机制） → ⑤ 验收标准与实测位置。
   **等用户确认后**才动手。
2. **开工**：严格按该 Round「交付产物」实现；尽量小步、可回退。
3. **开工后（必做）**：填写该 Round「开工后记录」：交付了什么模块/能力、改动体现在项目哪里（前端哪里可见 / 内部调用链）、测试结果、git commit、实测结果、遗留问题。
4. **git 提交**：每轮至少一次提交（Conventional Commits 风格，如 `feat(cyber-drill): ...`），commit message 只描述产品变更与验证；本轮结束前工作区必须干净，以提交点作为回退锚点。
5. **版本回退同步**：如果因任何原因执行 `git reset/revert` 回退到某轮，**本文档必须同步回退到该轮「开工后记录」完成时的状态**；代码有新更新，本文档跟随更新。**文档与代码永远在同一版本**。

### 0.2 比赛要求速查（XH-202631 荣耀 · 面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术）

> 原文要点：作品须在**材料文档 + 可运行系统**两方面体现能力；可运行系统须能**接受动态注入的异常、需求变更或节点失效，并在无人干预下自主完成从高层意图到最终交付物的全链路推理与执行，展示中间决策过程与推理轨迹**。截止 2026-09-15。

| 比赛要求 | 方案原文要点 | 本模块落点 | 相关轮次 |
|---|---|---|---|
| 能力维度 a：超长程上下文连续性与记忆保持 | 跨越多轮决策流，克服注意力稀释与记忆坍缩；关键信息、中间决策、全局目标在长链推理中不丢失不漂移 | drill 多轮循环 + 跨轮事件 `carry_forward` + 收敛历史记录；R8 接入记忆子系统做跨轮决策摘要 | R1、R8 |
| 能力维度 b：动态异构拓扑与低熵通信 | 通信拓扑随任务语义动态生成稀疏路由；抑制通信冗余与噪声级联，显著降低信息熵 | 每轮 SSE 只推**增量战报**（new_steps/new_issues），不重放全量；R9 事件总线化（EventBus `/events` 可订阅） | R3、R9 |
| 能力维度 c：端-边-云异构资源自适应调度 | 依据子任务实时性要求与数据敏感等级，自动完成推理位置的动态选择与模型切分 | R10 演练各阶段 `placement` 标注，复用 scheduler 卸载规则（latency<1s→device / <5s→edge / 否则→cloud） | R10 |
| 能力维度 d：评测场景验证 | 在典型产业场景中完成可运行系统验证 | 场景 1「网络防御（红→蓝→紫完整链路）」一键闭环，可作为赛事演示主场景 | R1-R6、R11 |
| 能力维度 e：交付物 | 可运行系统无人干预全链路；展示中间决策过程与推理轨迹 | 前端轮次时间线逐轮展示红/蓝/紫决策摘要；演练记录持久化可回放（`data/drills/<drill_id>.json`） | R2、R5、R11 |
| 评分·作品完整性 40 | 感知-规划-执行-反馈闭环 / 组织架构与协作机制 / 多任务场景演示 | 一键演练闭环 = 感知（红队扫描）→规划（攻击链/响应计划）→执行（蓝队处置）→反馈（紫队评审→下一轮）；红蓝紫三层分工即"层级/分工协作机制" | R1-R6 |
| 评分·技术创新性 20 | 降噪创新 + 核心算法与底层突破 | 收敛判定算法（4 规则提前终止）、增量事件合成（避免全量重放、控制 token 消耗） | R1、R9 |
| 评分·系统性能与效率 15 | 鲁棒性 / token 与时间资源效率 / 兼容扩展 | 提前收敛减少空转轮次（省 token/时间）；增量合成避免上下文膨胀；既有红/蓝/紫 REST 端点不动（兼容性） | R1、R6 |
| 评分·应用创新性 25 | 用户体验与易用性 5 / 场景覆盖 | 前端一键"开始演练"+ 实时时间线 + 总结报告，降低使用门槛 | R5 |

### 0.3 总路线图（Phase 0-5 · Round 0-11）

| 轮次 | 任务 | 阶段 | 依赖 | 比赛维度 | 状态 |
|---|---|---|---|---|---|
| **R0** | git 仓库初始化 + 本档案建档 + 全量初始提交 | 基线 | — | 工程保障 | ✅ 本轮完成 |
| **R1** | 编排器收敛式演练内核（`run_drill` 主循环 + 证据化事件合成/收敛纯函数，红队带轮次上下文可选） | 核心 | **R1.5** → R0 | a / 完整性40 / 技术20 / 效率15 | ✅ 已完成 |
| **R1.5** | Mock Provider 按轮演化升级（让多轮收敛真实可演示） | 核心 | R0 | a / d（前置） | ✅ 已完成 |
| **R2** | Service 层透出 `run_drill` + 演练记录持久化（`data/drills/`） | 核心 | R1 | e / 回放 | ✅ 已完成 |
| **R3** | 后端 drill 路由（REST + SSE 5 端点） | 核心 | R2 | b / d | ✅ 已完成 |
| **R4** | 前端 drill 类型 + API 客户端（含 SSE 订阅） | 核心 | R3 | d | ✅ 已完成 |
| **R5** | 前端演练视图（开始/停止 + 轮次时间线 + 总结报告） | 核心 | R4 | d / e / 体验5 | ✅ 已完成 |
| **R6** | 端到端联调 + 全量回归 + 实测指南定稿 | 核心 | **R1-R5（含 R1.5）** | d | ✅ 已完成 |
| **R7** | **真实 LLM 接入 drill** + 运行时模式切换（mock/real）+ 前端徽标 | 核心升级 | R6 | d / 演示核心 | ✅ 已完成 |
| **R8** | 跨轮记忆与上下文压缩（紫队带历史决策摘要） | 延申 P1 | R7 | a（重点加分） | ✅ 已完成 |
| **R9** | 演练事件总线化 + 低熵增量推送（**复用既有 EventBus**，不新造） | 延申 P1 | R7 | b（技术分10） | ✅ 已完成 |
| **R10** | 端-边-云 placement 联动（演练阶段调度位置标注） | 延申 P2 | R9 | c | ✅ 已完成 |
| **R11** | 无人干预演示脚本 + 赛事材料文档补全收尾 | 延申 P2 | R7-R10 | d / e | ✅ 已完成 |

> **（2026-09-04 评审修订）** 原开工审查报告方案经代码核查发现 3 处硬伤，已修订见各轮「评审记录」：
> ① **R1 收敛判定**：mock 下 `valid/consistent` 恒真会首轮"完全收敛"，多轮收敛跑不出来 → 改为**证据驱动**（锚定新资产/新步骤）+ 新增 **R1.5 mock 按轮演化**；
> ② **R3 并发**：编排器是同步的，直接 `asyncio.create_task` 会阻塞事件循环 → 改 `asyncio.to_thread` + 线程池；
> ③ **R8 不发新总线**：复用既有 `CyberOrchestrator.eventbus` + `install_hooks`，不新造。

---

## 1. 系统全景：模块地图 · 一条逻辑链 · 核心技术

### 1.1 大白话讲一遍：点一下「开始演练」，系统内部发生了什么

> 这一段是给评委/非技术读者看的"三句话版本"，专业细节见 1.2-1.4 与各轮小节。

打开系统，侧边栏进入 **Cyber（网络防御作战）** 页面，切到 **Drill** 标签页，输入目标网段（默认 `10.0.0.0/24`），点一下 **「开始演练」**。接下来屏幕上会**自己一帧一帧地**出现轮次卡片：

1. 第 1 轮：**红队**（攻击方）报告扫描到了哪些资产、发现了哪些漏洞、打算怎么打；**蓝队**（防守方）收到攻击事件流，给出告警和处置计划；**紫队**（裁判/复盘方）检查"攻击和防御对得上吗？还有没有漏掉的攻击面？"——发现缺口，判"不合格"。
2. 第 2 轮：红队**带着紫队上一轮的反馈**继续探测，补上新发现的攻击路径；蓝队补防御；紫队再评。这时可能判"合格"。
3. 第 3 轮：红队发现**没有新东西可挖了**，紫队也认可——系统判定"**收敛**"，提前收工，弹出**总结报告卡**（结论、跑了几轮、收敛原因、剩余风险、跨轮记忆摘要）。

这套"红→蓝→紫循环 + 提前收敛"就是整个模块的心脏。背后的关键点：

- **收敛 = 智能止损**：不是傻跑满 5 轮，而是每轮结束问一句"这轮有没有新证据？"——没有就停，省时间、省大模型的 token 费用；
- **每轮结果实时推送**：后端用 SSE（服务器推送）把每一轮战报"广播"给浏览器，所以时间线是**逐轮实时长出来**的，不是最后一次性刷出来；
- **系统真的会思考**：接入了 DeepSeek 大模型（也可以一键切回 Mock 演示模式），红蓝紫三方的"攻击计划、处置方案、评审意见"都是模型真实推理出来的，不是背台词；
- **所有轮次都存档**：整场演练落盘成 JSON，随时可以回放，评委可以点开看"中间决策过程与推理轨迹"；
- **记忆与调度**：紫队评审时带着前几轮的**压缩摘要**（不用重读全部历史，记忆不"塌方"）；每个阶段还标注了在**端/边/云**哪一层执行（体现异构资源自适应调度）。

### 1.2 模块地图（实际模块，不是文件）

#### 前端（用户看得见的模块 = 按钮 / 面板 / 标签页）

| 可视模块 | 长什么样 | 作用 | 连接的后端能力 |
|---|---|---|---|
| 侧边栏 **Cyber 入口** | 导航项 | 进入网络防御作战视图 | — |
| **LLM 模式徽标** | 头部绿点/黄点徽标 | 显示当前是"真实 LLM(deepseek-chat)"还是"Mock 演示"，**点击即可切换** | `GET/POST /api/v1/system/mode` |
| **范围栏** | 输入框 + Start Range 按钮 | 启动一个攻防会话（既有单链路能力） | 既有 attack/defense 端点 |
| **Tab 栏** | Red Team / Blue Team / Purple Review / Threat Intel / **Drill** 五个标签 | 切换各作战面板；Drill 是新增的第 5 个 | — |
| **Drill 面板**（核心新增） | 目标网段输入 + 最大轮数 + **「开始演练」/「停止」按钮** | 一键启动/中止多轮演练 | `POST /api/v1/drill/start`、`POST /api/v1/drill/{id}/abort` |
| **轮次时间线卡片** | 每轮一张卡片，可展开 | 实时展示红/蓝/紫三方决策摘要 + 🧠 记忆徽标 + 端/边/云执行位置徽标 | `GET /api/v1/drill/{id}/stream`（SSE 直播） |
| **总结报告卡** | 收敛后出现 | conclusion / convergence_code / rounds_executed / 跨轮记忆摘要区 | SSE `drill_summary` 事件 / `GET /api/v1/drill/{id}/summary` |

#### 后端（功能模块，按调用链从外到内）

| 功能模块 | 职责 | 与其他模块的关系 |
|---|---|---|
| **drill 路由**（接口层） | 提供 5 个端点：启动 / SSE 直播 / 状态查询 / 总结拉取 / 显式中止；管理每场演练的线程安全事件队列与中止开关 | 被前端按钮调用；调用服务层；把每轮战报推给 SSE；把增量事件发布到事件总线 |
| **服务层**（CyberDefenseService） | 包装编排器的 `run_drill`；每场演练完整落盘；支持查询与中止 | 介于路由与编排器之间；为 SSE 断线轮询兜底与回放提供数据源；默认注入记忆存储 |
| **编排器**（CyberOrchestrator） | 演练主循环 `run_drill`：每轮依次跑红→蓝→紫三链，做事件合成、收敛判定、记忆注入、placement 标注 | 复用既有红/蓝/紫链及其全部变体（guardrail/handoffs/traced/goal/human-check）；被服务层包装；被路由层经回调推送 |
| **运行时模式管理器** | mock/real 双编排器懒缓存与即时切换 | 服务层每次调用动态取当前模式的编排器；前端徽标读取/切换 |
| **模型后端**（Mock Provider / SDK Provider） | Mock：按轮演化的预置响应表；SDK：DeepSeek（OpenAI 兼容端点）真实模型 | 由运行时模式管理器按模式装配进编排器 |
| **记忆子系统**（MemoryStore + compactor） | 工作记忆/情景记忆四层存储；按 token 预算压缩生成跨轮摘要 | 编排器每轮写入并取回 `prior_rounds_summary`；摘要轨迹进总结报告 |
| **事件总线**（EventBus） | 主题发布/订阅（`/events` SSE 已存在） | 路由层每轮发布 `drill.round` 低熵增量事件，Monitor 等视图可订阅 |
| **调度器**（scheduler.schedule） | 按延迟预算 + 隐私等级在端/边/云候选池中选层 | 编排器每轮为红/蓝/紫三阶段标注执行位置 |
| **协议层**（protocol/cyber.py） | AttackChain / Alert / ResponsePlan / PurpleReviewResponse 等数据契约 | 全链路共享的"通用语言"，前端类型与后端 JSON 与之对齐 |

#### 模块关系图（专业版）

```
[前端 Drill 面板：开始/停止按钮 · 轮次时间线 · 总结报告卡]
        │  REST(start/abort)                    ▲  SSE(drill_start/round*/summary/done)
        ▼                                      │
[drill 路由] ──调用──▶ [服务层] ──调用──▶ [编排器 run_drill 主循环]
        │                                      │  每轮: 红→蓝→紫
        │  publish(drill.round 增量事件)        │  事件合成 · 收敛判定 · 记忆注入 · placement
        ▼                                      ▼
[事件总线 /events]                  [记忆子系统] ⇄ [调度器] ⇄ [模型后端 mock/real]
        ▼
[Monitor 等任意视图可订阅]
```

### 1.3 一条完整逻辑链（专业版，12 步）

1. 用户点击「开始演练」→ 前端 `cyberApi.startDrill()` 发 `POST /api/v1/drill/start`（带 `target_range`、`max_rounds`）；
2. 路由层创建 `DrillRuntime`（线程安全 `queue.Queue` + 中止 `threading.Event`），注册进内存 registry（上限 128 条防无界增长），立即返回 `201 {drill_id, status:"running"}`；
3. 后台用 `run_in_executor` 把**同步**编排逻辑丢进线程池执行（不阻塞 FastAPI 事件循环）；
4. 前端拿到 `drill_id` 后 `openDrillStream()` 建立 SSE 长连接 `GET /api/v1/drill/{id}/stream`；
5. 后台线程：`service.drill()` → `orchestrator.run_drill()`，进入多轮循环；
6. 每轮内部：红队 `run_red_chain(round)`（第 2 轮起携带轮次上下文，mock 下触发按轮演化）→ 事件合成 `_synthesize_event_stream`（首轮全量映射，后续轮 `carry_forward` 旧事件 + 按 `step_id` 去重追加新步骤）→ 蓝队 `run_blue_chain(event_stream)` → 紫队 `run_purple_review(chain, plan, alerts, prior_rounds_summary)`；
7. 收敛判定 `_evaluate_stop`：按优先级检查 中止 → 轮次上限 → 无新步骤且紫队 valid（converged）→ 连续 ≥2 轮无新步骤（no_progress）；同时 `_diff_chain_steps` 统计本轮新步骤；
8. `on_round` 回调：把本轮战报 `emit("drill_round", ...)` 进 SSE 队列，同时 `event_bus.publish(topic="drill.round", payload=增量摘要)`；
9. SSE 生成器用 `asyncio.to_thread(q.get)` 从队列取事件，按 `event: <type>\ndata: <json>\n\n` 帧格式推给浏览器；
10. 前端按事件名分发：`drill_round` → 追加轮次卡片并自动滚动；`drill_summary` → 渲染总结报告卡；`drill_done` → 恢复「开始演练」按钮；`drill_error` → 错误条；
11. 每轮结束，服务层把记录**增量落盘**到 `data/drills/<drill_id>.json`（SSE 断线时前端 2s 轮询 `getDrill` 补拉）；
12. 收敛或中止后，整场演练的完整记录可回放；R9 起 Monitor 视图还能订阅 `drill.round` 事件流看到演练心跳。

### 1.4 关键技术清单（含大白话）

| 技术 | 解决什么问题 | 大白话 |
|---|---|---|
| **SSE（Server-Sent Events）** | 每轮战报实时到达浏览器 | 后端像广播电台，把每一轮结果实时"播"给浏览器；浏览器不用反复问"有新的吗" |
| **`asyncio.to_thread` / `run_in_executor` + 线程安全队列** | 同步编排放后台线程，不阻塞异步事件循环 | 重活（跑演练）交给"外包工人"，前台服务员（事件循环）继续接客，互不耽误 |
| **事件合成 + `carry_forward`** | 跨轮上下文不丢，又不重放全量 | 蓝队既记得前面所有轮（旧事件打"续传"标记），又只看本轮新增的攻击步骤 |
| **证据驱动收敛判定（4 规则）** | 智能止损，不空转 | 每轮问"这轮挖到新东西了吗？"没有就收工，省时省钱 |
| **记忆压缩（compactor）** | 克服长链记忆坍缩 | 紫队看的是前几轮的"会议纪要摘要"，不是把整场录像重看一遍；决策保留、细节摘要 |
| **事件总线 topic 订阅** | 模块间低耦合广播 | 演练战报"上广播"，谁想听谁订阅，不打扰不相关模块 |
| **调度器 `schedule()`** | 端-边-云自适应选层 | 按"这活急不急、数据敏不敏感"自动决定在端侧/边侧/云端干 |
| **运行时模式（mock/real）** | 演示保底 + 真实推理可切换 | 有 API Key 就真思考，没有就切"背台词"演示模式，一键切换 |
| **Mock 按轮演化** | 让多轮对抗真实可演示 | 假对手也会"进步"：第一轮留漏洞、第二轮补上，戏才演得起来 |
| **落盘回放（data/drills）** | 中间决策过程可追溯 | 每场演练有"录像带"，评委随时可以回放、查验 |

---

## 2. Phase 1 · 一键闭环基础版（核心交付，对应开工审查报告 T1-T7）

### R1 · 编排器收敛式演练内核（含「批判性修订」）

- **大白话目标**：给系统装一个"自动对抗循环器"——一次调用自动跑完「红→蓝→紫」最多 5 轮，每轮结束判定"还有没有新证据"，没有就提前收工；配套两个可单测的纯函数（事件合成、收敛判定），保证逻辑可验证、可回归。
- **专业定位**：在编排器上新增 `run_drill` 主循环，作为整个多轮演练的总入口；同时修正原方案两个会让演示跑不通的硬伤。

> **评审记录：为什么原方案要改（基于代码核查，非臆测）**
> - **硬伤 A（收敛恒真）**：Mock Provider 返回**静态固定**响应——紫队批判 `valid=True`、评审 `consistent=True` 恒定。原收敛规则"valid and consistent → 收敛"在演示模式下**第一轮就触发**，多轮对抗→收敛的过程根本跑不出来，时间线只有一张卡片——恰恰是评委最想看的亮点。
> - **硬伤 B（无演化）**：红队攻击链只吃 `target_range`，同一目标每轮得到相同结果 → 攻击步骤恒定，增量事件合成永远无新步骤，「无进展收敛」「跨轮 carry」都失去意义。
> - **修正方向（不偏离主线）**：① 收敛判定从"状态恒真"改为"**证据驱动**"——锚定本轮是否产出**新步骤/新发现**，紫队对新增量给出评价；② 给红队增加**可选**轮次上下文参数（红队可带上一轮紫队反馈继续探测，默认不传=原行为，**既有调用零破坏**）；③ R1.5 把 mock 升级为**按轮演化**。三者合起来让同一套代码在 mock（聚变演示）与真实 LLM（动态演化）下都能工作。

- **怎么做到的（核心技术）**：
  1. **多轮主循环**：`run_drill(target_range, max_rounds=5, on_round, abort, drill_id, memory, memory_budget)` —— 每轮依次执行 红队攻击 → 事件合成 → 蓝队防御 → 紫队评审 → 新步骤比对 → 收敛判定 → `on_round` 回调上报；
  2. **事件合成纯函数** `_synthesize_event_stream(chain, prev_stream, round)`：第 1 轮把攻击链步骤逐条映射为事件 `{round, seq, type:"attack_step", source, target, technique, success}`；第 N+1 轮把上一轮事件全部打 `carry_forward: true` 保留（蓝队有完整上下文），再按 `step_id` 去重追加本轮新步骤为增量——**只增量、不重放**；
  3. **证据驱动收敛纯函数** `_evaluate_stop`，按优先级满足其一即停：
     - ① 显式中止（用户点「停止」）→ `aborted`；
     - ② 达到轮次上限 M → `max_rounds`；
     - ③ 本轮**无新步骤**且紫队 `valid` → `converged`（攻击面已穷尽、攻防自洽）；
     - ④ **连续 ≥2 轮无新步骤** → `no_progress`（红队挖不出新证据，避免空转）；
  4. **红队带上下文**：`run_red_chain` 增加可选 `round` 参数（默认不传=旧行为，零破坏）。
- **模块间关系**：
  - 后端：**编排器**（新增 `run_drill`）位于调用链核心，向下复用既有**红/蓝/紫三链**（guardrail / handoffs / traced / goal / human-check 变体全部保留、语义不变），向上被**服务层**包装、被**路由层**经回调推 SSE；与**协议层**数据契约只读复用；
  - 前端：本轮尚不可见（R5 才做 Drill 面板）。
- **工作流/逻辑链**：`run_drill` 内部每轮 = 红（演化式攻击）→ 事件合成 → 蓝（处置+告警）→ 紫（评审+缺口）→ 比对出新步骤 → 判定是否收敛 → 回调上报 → 下一轮。
- **验收与实测**：新增 9 例单测全绿；全量 `608 passed`；既有 `test_scenario1.py` 与编排层全部 130 例不破；REPL 实测 `run_drill("10.0.0.0/24")` 返回 `rounds_executed=3`、`convergence_code="converged"`（第 1 轮 1 步 / valid=False / 1 缺口 → 第 2 轮新 step-2 / valid=True → 第 3 轮 0 新增 / valid=True 收敛）——多轮对抗→补齐→收敛的叙事真实可演示。
- **git**：`58e8a43`（`feat(cyber-drill): R1 收敛式演练内核 run_drill——证据驱动收敛与跨轮事件合成`）
- **遗留问题 / 下一步**：`prev_context`（R7 记忆注入）已预留；进入 R1.5（mock 演化，R1 验收前置）。

### R1.5 · Mock Provider 按轮演化升级（让多轮收敛真实可演示）

- **大白话目标**：让"假对手"（Mock）会进步——第 1 轮故意留漏洞让紫队挑出来，第 2 轮红队补上缺口转合格。这样多轮对抗→收敛的过程才"演得出来"。
- **专业定位**：R1 的验收前置；没有它，`run_drill` 的多轮收敛、增量事件、无进展判定全部无法真实触发。
- **怎么做到的（核心技术）**：
  1. **轮次上下文感知**：Mock 从红队请求里读取轮次（`round` 拼进 prompt/request.metadata），第 r 轮才暴露 asset-r / vuln-r / step-r——资产与发现随轮次增长；
  2. **紫队缺口剧本**：第 1 轮 critic 返回 `valid=False + issues`（如"未覆盖 asset-2 风险"），第 2 轮红队补齐后返回 `valid=True`；
  3. **兼容回退**：保持"前缀匹配"回退机制——未显式传轮次的既有调用仍命中旧静态 key，行为与旧版完全一致。
- **模块间关系**：**模型后端**（Mock Provider）是"大脑"的一种实现，由**运行时模式管理器**装配进**编排器**；演化只在该 mock 收到含轮次上下文的请求时触发，否则回退旧静态响应——既有 attack/defense/purple 端点与默认服务实例**零感知**。
- **工作流/逻辑链**：`run_drill` 第 2 轮起传 `round` → Mock 按轮演化出新资产/新步骤 → 紫队对新增量评价 → 缺口补齐转 `valid=True` → 收敛判定有真实依据。
- **验收与实测**：新增 5 例全绿；全量 `608 passed`；无 round 上下文时 recon 仍 2 资产、critic 仍 valid=True（兼容分支生效）。
- **git**：`debf047`（`feat(cyber-drill): R1.5 攻防 mock 按轮演化——多轮收敛演练可真实演示`）
- **遗留问题 / 下一步**：真实 LLM 模式天然获得"逐轮演化"能力，无需 mock；与 R1 一并交付后进入 R2。

### R2 · 服务层透出 drill + 演练记录持久化

- **大白话目标**：给演练加"录音机"——每场演练完整存档成 JSON，随时可查询、可回放；SSE 万一断线，前端也能靠这份存档把缺的轮次补回来。
- **专业定位**：服务层包装 `run_drill`，把"跑完即丢"的演练变成"可追溯的交付物"，对应能力维度 e（中间决策过程与推理轨迹的可回放证据）。
- **怎么做到的（核心技术）**：
  1. `service.drill(...)` 包装编排器：透传 `on_round` 回调、`abort` 开关、`drill_id`，保证 registry / 落盘 / SSE 三处 ID 一致；
  2. **增量落盘**：每轮结束把 `{drill_id, target_range, max_rounds, status, created_at, rounds:[...], summary:{...}}` 写进 `data/drills/<drill_id>.json`——JSON 结构与 SSE 战报契约同构，落盘即"回放源"；
  3. `get_drill / list_drills` 提供查询；按 drill_id 独立文件，天然支持并发演练；运行时产物目录不入版本库（`.gitignore` 保护）。
- **模块间关系**：**服务层**是路由与编排器之间的"翻译官 + 档案员"；数据源同时服务 **SSE 断线轮询兜底**与**赛后回放**；R8 的跨轮记忆也挂在服务层默认注入。
- **工作流/逻辑链**：路由请求 → `service.drill()` → 编排器每轮回调 → 服务层追加 events + 写盘 → `get_drill` 还原 / `list_drills` 列元信息。
- **验收与实测**：新增 6 例全绿；全量 `614 passed`；REPL 实测 3 轮收敛演练落盘 JSON，`get_drill` 可还原、缺失返回 None。
- **git**：`8276490`（`feat(cyber-drill): R2 Service 层透出 drill + 演练记录持久化到 data/drills`）
- **遗留问题 / 下一步**：`status` 运行态交给 R3 异步路由层管理；进入 R3（后端 drill 路由 + SSE）。

### R3 · 后端 drill 路由（REST + SSE 直播）

- **大白话目标**：给演练开 5 个"门"：**开始**（启动一场演练）、**直播**（SSE 实时看每一轮）、**查询**（看进行到哪了）、**总结**（拿收敛报告）、**停止**（随时叫停）。
- **专业定位**：对外接口层，能力维度 b 的落点——SSE 每轮只推**增量战报**（本轮新步骤数、新问题数、各阶段摘要），不推全量链，体现低熵推送。
- **怎么做到的（核心技术）**：
  1. **5 端点契约**：`POST /drill/start`(201) · `GET /drill/{id}/stream`(text/event-stream) · `GET /drill/{id}`(轮询兜底) · `GET /drill/{id}/summary`(未收敛 409) · `POST /drill/{id}/abort`；
  2. **并发模型（评审修订②）**：编排器是**同步**逻辑，直接 `asyncio.create_task` 会阻塞事件循环 → 用 `run_in_executor` 把同步编排丢线程池，SSE 生成器用线程安全 `queue.Queue` + `asyncio.to_thread(q.get)` 消费，既保留 FastAPI 异步响应模型，又不阻塞其他请求；
  3. **事件生命周期**：`drill_start → drill_round* → drill_summary → drill_done`，任一轮异常推 `drill_error` 后收尾；SSE 帧格式 `event: <type>\ndata: <json>\n\n` 与既有 stream 路由一致；
  4. **中止开关**：`abort_evt`（`threading.Event`）跨线程可见，配合收敛规则①在下一轮边界停止；内存 registry 上限 128 条防无界增长。
- **模块间关系**：**路由层**（新增 drill 路由）继承既有网关的统一前缀与鉴权，向下调**服务层**；SSE 生成器消费 `DrillRuntime` 队列；R9 将在这里把每轮事件发布到**事件总线**（已预留 emit 点）。
- **工作流/逻辑链**：`start` 建 runtime + 注册 + 后台线程跑 → 前端连 `/stream` → 线程每轮 `emit` → SSE 生成器推帧 → `done` 收尾；断线后 `get` 走落盘兜底。
- **验收与实测**：新增 10 例全绿（start 201 / stream 生命周期 / 404 / summary 收敛码 / abort）；全量 `624 passed`；TestClient 冒烟——事件序列 `[drill_start, drill_round×3, drill_summary, drill_done]` 无重复、get 返回 done+3 轮、summary 返回 converged。
- **git**：`b09bb2e`（`feat(cyber-drill): R3 drill 路由——REST+SSE 5 端点（to_thread 并发 + 事件队列）`）
- **遗留问题 / 下一步**：进入 R4（前端类型 + API 客户端 + SSE 订阅封装）。

### R4 · 前端类型 + drill API 客户端

- **大白话目标**：给前端装好"遥控器"——开始、订阅直播、查询、拿总结、停止这 5 个动作都封装成现成函数，还配好"说明书"（类型定义）。
- **专业定位**：前端的数据通道层，把后端契约翻译成 TypeScript 类型，为 R5 视图铺路。
- **怎么做到的（核心技术）**：
  1. `cyberApi` 新增 `startDrill / openDrillStream / getDrill / getDrillSummary / abortDrill`；
  2. **SSE 订阅封装** `openDrillStream(drillId, onEvent)`：用 `EventSource` 连接 `/api/v1/drill/{id}/stream`（浏览器 EventSource 无法带自定义 Header，走 query 传 key 兜底鉴权），按 `event:` 名分发 5 类事件到回调，返回关闭函数；
  3. `getDrill / getDrillSummary` 走普通 GET，作为 SSE 断线兜底；类型字段与后端战报 JSON 严格对齐（round/max_rounds/status/phase{red,blue,purple}/event_id）。
- **模块间关系**：**API 客户端**是 **Drill 面板**（R5）与后端之间的唯一数据通道；**协议层**契约为唯一事实源，前端类型注解锚定之。
- **验收与实测**：vitest 新增 8 例全绿（mock API 客户端断言路径/编码 + mock EventSource 断言 URL、事件分发、畸形载荷忽略、close）；前端全量 4 文件 32 tests 通过；`tsc -b` 类型检查通过。
- **git**：`9b4f2f0`（`feat(cyber-drill): R4 前端 drill 类型 + cyberApi 客户端（SSE 订阅封装）`）
- **遗留问题 / 下一步**：进入 R5（前端 Drill 演练视图）。

### R5 · 前端演练视图（Drill 面板：开始/停止 + 轮次时间线 + 总结报告）

- **大白话目标**：把演练"画面"做出来——一个「开始演练」按钮、逐轮长出来的时间线卡片、收敛后的总结报告卡、随时能「停止」。
- **专业定位**：能力维度 e 的前端呈现（时间线逐轮展示红/蓝/紫决策摘要 = "展示中间决策过程与推理轨迹"）+ 应用创新·体验 5 分（一键闭环、实时可视化、降低使用门槛）。
- **怎么做到的（核心技术）**：
  1. **面板状态机**：`idle / running / done / aborted / error` 五态，驱动按钮文案与禁用逻辑；
  2. **SSE 事件驱动 UI**：`drill_start` 清空时间线；`drill_round` 追加轮次卡片（红 findings/new_steps、蓝 alerts/triaged、紫 valid/issues/convergence_code，可展开详情，自动滚动到最新）；`drill_summary` 渲染总结卡（conclusion / convergence_code / rounds_executed / red-blue-purple 统计 / remaining_risks）；`drill_done` 恢复按钮；`drill_error` 错误条；
  3. **断线兜底**：SSE `onError` → `getDrill` 2s 轮询补拉已发生轮次；卸载时关流 + 停轮询；
  4. **实测修掉一个真实闭包 bug**：`handleStreamError` 在 `setDrillId` 之前的渲染里创建、捕获旧 `drillId=null` 导致断线轮询永不触发——改用 `drillIdRef` ref 镜像解决（测试暴露）。
- **模块间关系**：**Drill tab** 追加在既有 **Cyber 视图**的 Tab 栏第 5 位（Red/Blue/Purple/Threat 四面板不动，回归风险最小）；面板复用全局 store 的 `cyberLoading/cyberError` 模式；数据完全来自 R4 的 **API 客户端**。
- **工作流/逻辑链**：点「开始演练」→ `startDrill` → 拿 `drill_id` → `openDrillStream` 订阅 → 事件分发更新 `rounds[]/summary` → 收敛后总结卡 + 按钮复位；「停止」→ `abortDrill` → 编排器下一轮边界中止并输出已收敛部分。
- **验收与实测**：新增 7 例（面板 6 + Drill tab 1）；前端全量 5 文件 `39 passed`；`tsc -b` 通过；eslint 全清。
- **git**：`fdce5a7`（`feat(cyber-drill): R5 前端 Drill 演练视图——开始/停止 + SSE 轮次时间线 + 总结报告`）
- **遗留问题 / 下一步**：进入 R6（端到端联调 + 全量回归 + 实测指南定稿）。

### R6 · 端到端联调 + 全量回归 + 实测指南定稿

- **大白话目标**：把 R1-R5 拼起来的整条链路从头到尾真实跑一遍，确认"点按钮 → 逐轮战报 → 总结报告"完整通，并把操作指南写定。
- **专业定位**：能力维度 d（可运行系统的完整验证）+ 系统性能与效率 15（回归证明鲁棒性/兼容性）。
- **怎么做到的（核心技术）**：真实 HTTP 端到端（uvicorn 起服）走完「开工审查报告 §5 六条验收」；联调暴露一处**跨层字段不一致**——`GET /drill/{id}` 缺 `rounds_executed/convergence_code`（前端断线轮询要读），按"前端/路由层对齐协议层、不动协议层"原则小修；全量回归 + 实测指南定稿。
- **模块间关系**：本轮是**全链路缝合**——后端（路由/服务/编排器）与前端（Drill 面板/API 客户端）第一次以真实 HTTP + 真实浏览器行为打通，验证所有模块间契约（REST 字段、SSE 事件名、JSON 结构）一致。
- **验收与实测**：六条验收全勾——① start 201 + SSE `drill_start→drill_round×3→drill_summary→drill_done` 完整；② `rounds_executed=3`/`converged`（≤5 提前收敛）；④ summary 200 + 落盘可回放；⑤ abort 200；⑥ 既有 attack/defense/purple 端点 200 全过；后端全量 `624 passed`、前端 `39 passed`、`tsc -b` exit 0。
- **git**：`9888236`（`fix(cyber-drill): R6 联调小修——GET /drill/{id} 补 rounds_executed/convergence_code + 验收报告打勾`）
- **遗留问题 / 下一步**：核心路线 R1-R6 完成；复盘将"真实 LLM 接入"提升为 R7（用户拍板：默认真实调用 + 前端模式切换），跨轮记忆顺延为 R8。

---

## 3. Phase 2 · 超长程上下文连续性与记忆保持（能力维度 a）

### R7 · 真实 LLM 接入 drill + 运行时模式切换（mock/real）+ 前端徽标

> **（2026-09-04 复盘修订）** 原 R7 为「跨轮记忆」，经复盘发现 R1-R6 全部跑在 mock 预置响应上、真实推理从未验证——这恰是比赛原文「无人干预自主全链路推理」的灵魂。用户拍板：**真实 LLM 接入提升为 R7（默认真实调用）**，跨轮记忆顺延为 R8。

- **大白话目标**：让系统"真的会思考"——红蓝紫三方的攻击计划、处置方案、评审意见由 **DeepSeek 大模型**真实推理出来，而不是背台词；同时保留 Mock 演示模式，前端头部一个徽标就能看到当前模式、点击即可切换。
- **专业定位**：能力维度 d 的核心——可运行系统的真实自主推理闭环；"默认 mock 白做了"→ 双模式可切换，mock 作保底演示。
- **怎么做到的（核心技术）**：
  1. **运行时模式管理器**（进程内单例）：按当前模式**懒创建并缓存两个编排器**（mock 与 real 各一个）——切换模式只换引用，不重建 11 个 Agent；
  2. **默认模式决策**：显式 `AEGIS_USE_MOCK=true` → mock；否则有 `OPENAI_API_KEY` → real（默认真实 LLM）；否则回落 mock（无 Key 不崩溃）；`set_mode` 同步环境变量防止 SDK/Provider 内部行为不一致（实测 500 的坑）；
  3. **真实模型走 OpenAI 兼容端点**：`OPENAI_BASE_URL=https://api.deepseek.com/v1` + `deepseek-chat`，复用既有 SDK Provider；
  4. **前端徽标**：绿点+"真实 LLM deepseek-chat" / 黄点+"Mock 模式"，点击调 `POST /api/v1/system/mode` 切换，`GET` 返回 `{mode, model, provider, has_key, available}`。
- **模块间关系**：**运行时模式管理器**夹在**服务层**与**编排器**之间——服务层每次调用经 `get_orchestrator()` 取当前模式的编排器，切换即时生效；**前端徽标**是模式状态的"仪表盘 + 遥控器"。
- **工作流/逻辑链**：启动初始化模式 → 服务层取编排器 → drill 全链路自动走对应大脑；徽标点击 → `POST /system/mode` → 全局切换 → 下一次演练即用新模式。
- **验收与实测**：后端全量 `627 passed`（+system mode 3）；前端全量 6 文件 `43 passed`；`tsc -b` exit 0；实测 `GET /system/mode` → `{mode: real, model: deepseek-chat, provider: deepseek}`；POST mock/real 往返切换 200；真实 LLM 连通性冒烟（DeepSeek `LLM_OK`）。
- **git**：`54f45de`（`feat(cyber-drill): R7 真实 LLM 接入——运行时模式切换（mock/real）+ 前端徽标`）
- **遗留问题 / 下一步**：真实多轮演练完整跑一遍（成本/时间可控时）；进入 R8 跨轮记忆。

### R8 · 跨轮记忆与上下文压缩（紫队带历史决策摘要）

- **大白话目标**：给系统加"记忆"——紫队评审时手里有一份前几轮的**会议纪要摘要**，不用把前几轮全部重读一遍；总结报告里还能看到"记忆轨迹"。
- **专业定位**：直接命中能力维度 a（跨越多轮决策流、克服注意力稀释与记忆坍缩）+ 技术创新 20 的"核心算法与底层突破"展示。
- **怎么做到的（核心技术）**：
  1. **每轮写记忆**：每轮紫队评审结束后，把该轮 critique/review 要点打包成决策包（`MemoryPacket(kind="decision")`）写入工作记忆 + 情景记忆（复用既有四层记忆存储，不新造）；
  2. **按预算压缩**：`MemoryStore.compress(session_id, budget)` 在工作记忆栈上按 token 预算压缩——**决策保留 + 最近保留 + 其余 digest**（实测 `budget=10` 时 6 包压成 4 包：3 个 decision 保留 + 1 个 digest 带 `:detail` 溯源）；
  3. **摘要注入下一轮**：生成的 `prior_rounds_summary` 文本注入下一轮紫队 critic/reviewer 的 prompt（`[prior_rounds_summary]` 片段），实现跨轮上下文连续性；
  4. **记忆轨迹**：总结报告新增 `memory_trace`（每轮一条：`stored_task_id / compressed_count / next_round_summary`），决策过程可审计。
- **模块间关系**：**编排器**每轮与**记忆子系统**交互（写→压→取）；**服务层**默认注入记忆存储（零破坏）；**前端 Drill 面板**轮次卡出现 🧠 mem 徽标（第 2 轮起）+ 总结报告「Cross-Round Memory（跨轮记忆摘要）」区逐轮展示摘要。
- **工作流/逻辑链**：第 r 轮 purple 完成 → `_store_round_memory` 写决策包 → `compress` 生成摘要 → 第 r+1 轮 `run_purple_review(..., prior_rounds_summary=...)` 注入 → 循环直至收敛 → summary 带 `memory_trace`。
- **验收与实测**：后端全量 `634 passed`（+7）；前端 `43 passed`；mock 实测 3 轮收敛，第 2 轮摘要含第 1 轮结论（"攻击链未覆盖内部资产 asset-3（10.0.0.15:redis 高危入口）"），`memory_trace` 每轮一条。
- **git**：`0959d05`（`feat(cyber-drill): R8 跨轮记忆与上下文压缩——紫队带历史决策摘要`）
- **遗留问题 / 下一步**：摘要语义质量依赖 compactor，真实 LLM 模式抽检未做（mock 已验证字段链路）；下一步 R9「演练事件总线化 + 低熵增量推送」（能力维度 b）。

---

## 4. Phase 3 · 动态异构拓扑与低熵通信（能力维度 b）

### R9 · 演练事件总线化 + 低熵增量推送（EventBus 联动）

- **大白话目标**：让演练战报"上广播"——别的模块（比如监控页）也能订阅到演练心跳；而且每轮只广播"新增了什么"，不重复广播全部内容，通信量最小化。
- **专业定位**：能力维度 b（架构与交互降噪创新，技术分 10）——抑制通信冗余、信息熵显著降低。
- **怎么做到的（核心技术）**：
  1. **主题发布**：drill 路由每轮 `on_round` 时 `event_bus.publish(topic="drill.round", payload=...)`；
  2. **低熵 payload**：只含 `round / drill_id / new_steps / new_issues / valid / converged / carry_forward_count / prior_summary`——**不含**全量 AttackChain/ResponsePlan（实测 `carry_forward_count` 0→1→2：首轮全量、后续只推增量）；
  3. **复用既有总线**（评审修订③）：直接复用全局 composition 的 EventBus 单例 + `/events` SSE 端点（0.5s 轮询、按 topic 过滤），**不新造总线**；
  4. **与 R8 联动**：第 2 轮起 `prior_summary` 携带跨轮记忆摘要进事件流，事件总线与记忆子系统打通。
- **模块间关系**：**路由层** ⇄ **事件总线**：演练事件成为系统级可订阅资源；**Monitor 等任意视图**可通过 `/api/v1/events?stream=drill.round` 接入，前端复用既有 SSE 订阅基建。
- **工作流/逻辑链**：演练每轮结束 → 路由发布 `drill.round` 增量事件 → 总线按 topic 分发 → 订阅方（Monitor/任意视图）收到心跳。
- **验收与实测**：后端全量 `638 passed`（+4）；前端未改动无需回归；API 级实测 3 轮事件全部发布，payload 为增量摘要。
- **git**：`72d3d13`（`feat(cyber-drill): R9 演练事件总线化——drill.round 低熵增量事件可订阅`）
- **遗留问题 / 下一步**：placement 信息并入 drill.round（与 R10 联动）；进入 R10（演练阶段 placement 联动，能力维度 c）。

---

## 5. Phase 4 · 端-边-云异构资源自适应调度（能力维度 c）

### R10 · 演练阶段 placement 联动（调度位置标注）

- **大白话目标**：给演练每个阶段"盖章"——红队标"端侧执行"、蓝队标"边侧"、紫队标"云端"，轮次卡片上直接看得到，悬停还能看到为什么这么放。
- **专业定位**：能力维度 c——依据子任务实时性与敏感度自动选择推理位置；复用既有 scheduler 卸载规则，把"端-边-云自适应调度"落到攻防场景演示上。
- **怎么做到的（核心技术）**：
  1. **每阶段任务特征**：为红/蓝/紫三阶段定义任务特征（延迟预算 + 隐私等级 + 所需能力）——如红队攻击链实时生成（超低延迟）、紫队评审高算力需求；
  2. **复用调度器**：构造 `Task` → 调 `schedule(task, 三层候选池, required_capability)` → 得 `{tier, model_id, reason}`；调度异常防御性回退云侧；
  3. **写进战报**：每轮 `round_data["phase"] = {red, blue, purple}`，前端三色徽标（device 绿 / edge 黄 / cloud 蓝）展示 + title 带卸载理由。
- **模块间关系**：**编排器**每轮调用**调度器**；**前端轮次卡**是 placement 的可视化出口；演示版用候选池标注（与项目"演示版跳过真实端边云"一致），不新造调度逻辑。
- **工作流/逻辑链**：`run_drill` 每轮 → `_phase_placements()` 按阶段特征构造任务 → `schedule()` 选层 → 注入 round_data → SSE 推送 → 前端徽标渲染。
- **验收与实测**：后端全量 `642 passed`（+4）；前端 `43 passed`；实测 3 轮演练各阶段稳定——red→device（device_firewall，超低延迟）、blue→edge（edge_gateway，低延迟）、purple→cloud（cloud_gpu，高算力），卸载理由语义清晰、跨轮稳定。
- **git**：`79f963c`（`feat(cyber-drill): R10 演练阶段 placement 联动——端-边-云自适应调度标注`）
- **遗留问题 / 下一步**：演示版用候选池非真实节点（已声明）；进入 R11「无人干预演示脚本 + 赛事材料文档补全」（能力维度 d/e，截止 2026-09-15）。

---

## 6. Phase 5 · 评测场景与交付物收尾（能力维度 d/e）

### R11 · 无人干预演示脚本 + 赛事材料文档补全

- **大白话目标**：做一条"一键演示"命令——评委在命令行敲一下，系统自动启动、自动跑完整场演练、自动输出总结和存档路径，全程不需要人点任何按钮。
- **专业定位**：能力维度 d/e 的交付闭环——可运行系统无人干预全链路验证 + 材料文档对齐。
- **怎么做到的（核心技术）**：
  1. **演示脚本**：探测 Python 环境 → 自动启动 uvicorn（默认 mock，`-UseRealModel` 切真实模型）→ `POST /drill/start` → 轮询至收敛 → 输出总结/跨轮记忆/落盘路径 → 自动停掉自启后端（`-KeepRunning` 保留）；后端日志重定向到独立日志文件；
  2. **材料收尾**：README 新增「CyberDrill 攻防演练演示」章节（一键用法 + 手动演示 + R1-R11 能力落点表），CHANGELOG 汇总 R8-R11，本档案实测指南补最终版。
- **模块间关系**：脚本串联 **R3 drill 端点 + R9 事件流端点**，依赖 **R2 落盘**与 **R7 运行时模式**——是全部轮次成果的"总装线"。
- **验收与实测**：脚本实测 3 场演练全部无人干预跑通——`rounds_executed=3`、`convergence=converged`、`memory_trace=3 rounds`、落盘 JSON 存在、自动停后端、退出码 0；默认 mock 模式（真实 LLM 400 问题已规避，`-UseRealModel` 可选）。
- **git**：`1cd9ffe`（`docs(demo): R11 无人干预演示脚本 + 赛事材料收尾`）
- **遗留问题 / 下一步**：终端中文乱码可 `chcp 65001` 或 Windows Terminal（数据本身 UTF-8 完好）；可选延申——录制演示视频素材。

---

## 7. 实测指南（总览）

> 启动方式以项目既有 `start.ps1` / `start.sh` 为准（前端 Vite + 后端 uvicorn）。以下为攻防演练链路实测路径。

| 层 | 怎么启动 | 在哪测 | 看什么 |
|---|---|---|---|
| 一键演示 | `powershell -ExecutionPolicy Bypass -File tooling/scripts/drill_demo.ps1` | 命令行 | 无人干预全流程：自动起后端 → 发演练 → 收敛 → 总结/记忆轨迹/落盘路径（R11） |
| 后端 | `uvicorn backend.main:app`（或 start.ps1） | `http://localhost:8000/api/v1/...`（需 `X-API-Key`，见 `.env.example`） | R3 五个 drill 端点；`/docs` 页面直接调试 |
| 前端 | `npm run dev` | `http://localhost:5173` → 侧边栏 Cyber → **Drill tab** | 开始/停止按钮、轮次时间线、总结报告（R5）、🧠 mem 徽标（R8）、tier placement 徽标（R10）、LLM 模式徽标（R7） |
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
| 2026-09-04 | R4 | 前端 drill 类型 + API 客户端（SSE 订阅封装）；前端 vitest 32 passed、tsc -b 通过 | `9b4f2f0` |
| 2026-09-04 | R5 | 前端 Drill 演练视图（开始/停止 + SSE 轮次时间线 + 总结报告）；前端 vitest 39 passed、tsc -b/eslint 通过 | `fdce5a7` |
| 2026-09-04 | R6 | 端到端联调 + 六条验收全勾 + 联调小修（GET /drill/{id} 补字段）；后端 624/front 39/tsc 全绿 | `9888236` |
| 2026-09-04 | R7 | 真实 LLM 接入 drill + 运行时模式切换（mock/real）+ 前端徽标；后端 627/front 43 全绿；DeepSeek 连通性冒烟通过 | `54f45de` |
| 2026-09-05 | R8 | 跨轮记忆与上下文压缩（紫队带历史决策摘要）；后端 634/front 43 全绿；mock 实测 3 轮收敛携带前轮摘要 | `0959d05` |
| 2026-09-05 | R9 | 演练事件总线化（drill.round 低熵增量事件可订阅）；后端 638 全绿；API 实测 3 轮事件 + carry 增量 + 跨轮摘要联动 | `72d3d13` |
| 2026-09-05 | R10 | 演练阶段 placement 联动（red→device / blue→edge / purple→cloud 三阶段标注）；后端 642 全绿；前端 43 全绿 | `79f963c` |
| 2026-09-05 | R11 | 无人干预演示脚本 drill_demo.ps1 + README/CHANGELOG/实测指南收尾；脚本实测 3 场全自动跑通 | `1cd9ffe` |
