# 真实大模型演练 · drill-acd29619 · 逐轮运行记录

> 存档时间:2026-09-07 · 数据来源:本地落盘 `data/drills/drill-acd29619.json`
> 运行方式:真实 DeepSeek 大模型调用(非 mock)、Auto Drill、目标 `10.0.0.0/24`、轮次上限 5
> 结果:跑满 5 轮未收敛,`convergence_code = max_rounds`(强制到上限结束)

---

## 一、演练基本信息

| 字段 | 值 |
|---|---|
| drill_id | `drill-acd29619` |
| target_range | `10.0.0.0/24` |
| max_rounds / rounds_executed | 5 / 5 |
| convergence_code | `max_rounds`(未提前收敛,到上限强制结束) |
| 结论 | 「演练在到达停止条件时结束(见 convergence_code)」 |

**核心结论:这不是系统崩溃,而是真实大模型下跨 Agent 协作一致性未达收敛状态,系统如实记录了下来。**

---

## 二、跨 Agent 协作框架(设计原型 vs 实际实现)

### 2.1 当初设计的 WarfareMaster 框架(已定稿)

```
WarfareMaster(唯一"主")
 ├─ 持有一份共享状态 state(一个大 JSON,不是黑板)
 ├─ 委派红队链(带上上一轮紫队反馈)→ 收 assets/findings/attack_chain 写回 state
 ├─ 事件合成:攻击链步骤 → 合成攻击事件流(确定性函数,不用 LLM)→ 写回 state.events
 ├─ 委派蓝队链(输入 = state.events)→ 收 alerts/triaged/hypotheses/plan 写回 state
 ├─ 委派紫队链(输入 = state 里攻击链+防御+告警)→ 收 critique/review 写回 state
 └─ 收敛判断:critic 通过 且 review 一致 → 结束;或达最大轮数 → 结束;否则带反馈进下一轮
```

### 2.2 实际实现核查(2026-09-07)

- ✅ **骨架已实现**:`CyberOrchestrator.run_drill` 已是"主循环"式编排——每轮依次 `run_red_chain → _synthesize_event_stream(确定性事件合成) → run_blue_chain → run_purple_review → _evaluate_stop(收敛判定)`,并注入上一轮紫队反馈(`prior_rounds_summary`,R8 跨轮记忆)。
- ❌ **关键缺口:红队链内部没有执行"统一资产/链路命名"约束**。`run_red_chain` 中 recon 产出 `assets`(asset_id)后,vuln_correlator 用它关联漏洞,但 **exploit_planner 只收到 findings 的 JSON,未与资产清单/上一轮链路强绑定**。真实模型下 exploit_planner 可自由输出 `to_asset`/`from_asset`,导致:
  - 资产命名分裂:有时 `asset-001`,有时纯 IP `10.0.0.1`
  - 红队攻击链目标与蓝队告警路径不一致(蓝队 `_synthesize_event_stream` 基于红队链生成,但紫队 reviewer 比对时发现资产名对不上)

**一句话:WarfareMaster 的"共享 state"在设计上定了,但实现层没有真正把资产命名/链路作为不可变的事实源写回 state 强制各链引用,而是各链各自调用 LLM 自由生成 → 跨 agent 一致性在真实模型下无法保证。**

---

## 三、五轮逐轮讲解

### 第 1 轮(red⇄blue 一致,紫队 9 问题)

| | 内容 |
|---|---|
| 侦察(4 资产) | asset-001 `10.0.0.1` SSH/HTTP Linux public；asset-002 `10.0.0.2` HTTPS/DNS Windows internal；asset-003 `10.0.0.3` FTP/Telnet Linux public；asset-004 内部 |
| 漏洞(6 条) | 最高危 CVE-2023-23397(9.8)；CVE-2021-3156(7.8)… |
| 攻击链(6 步) | 目标"域管理员"：爆 CVE-2023-23397 偷 NTLM 哈希 → 哈希中继/传递 → 爆 CVE-2021-3156 提权 root → 横向移动… |
| 蓝队 | 告警 6 / 分诊 6 / 响应动作 8 |
| 紫队 critic | `valid=False`,问题 **9 个**：攻击步骤有效,但**缺 ATT&CK 技法编号**(如 T1187/T1557) |
| 紫队 reviewer | `consistent=True`(红蓝数据对得上 ✅) |

### 第 2 轮(红蓝开始不一致 ❌)

| | 内容 |
|---|---|
| 改打法 | 走 asset-001 → 横向 → asset-003；5 步,新增 0 步 |
| 紫队 critic | `valid=False`,9 问题(仍是缺技法编号) |
| 紫队 reviewer | **`consistent=False` 首次出现**:红队攻击链最终目标是 asset-003,但蓝队告警走的是另一条到域控制器的路径 → 红蓝对不上 |

### 第 3 轮(资产命名分裂 ⚠️)

| | 内容 |
|---|---|
| 资产 ID 异常 | agent 内部记忆混乱,资产直接以**纯 IP** 标识(`10.0.0.1`)而非 `asset-001` |
| 攻击链(6 步) | CVE-2018-15473 枚举 SSH 用户 → 有效凭据登录 → CVE-2021-3449(TLS 中间人)→ CVE-2018-0171… |
| 蓝队 | 告警 12 / 分诊 12 / 响应 14 |
| 紫队 critic | `valid=False`,9 问题 |
| 紫队 reviewer | `consistent=False`:红队用 IP、蓝队响应计划仍出现旧名 `asset-001`,命名体系分裂 |

### 第 4 轮(持续不一致)

| | 内容 |
|---|---|
| 攻击链 | Samba RCE(CVE-2017-7494)→ Heartbleed 泄凭据(CVE-2014-0160)→ glibc 提权(CVE-2015-7547)…目标 asset-005 |
| 紫队 critic | `valid=False`,问题增至 **10 个** |
| 紫队 reviewer | `consistent=False`:告警路径(asset-002→DC)与攻击链(asset-001→003)仍两套 |

### 第 5 轮(到上限强制结束)

| | 内容 |
|---|---|
| 攻击链 | Log4Shell(CVE-2021-44228)→ 路径穿越提权 → Zerologon(CVE-2020-1472) |
| 紫队 critic | `valid=False`,8 问题 |
| 紫队 reviewer | `consistent=False` |

---

## 四、为什么没收敛?根因

1. **表面原因(critic 反馈)**:每个攻击步骤都缺 ATT&CC 技法编号(真实模型未稳定输出结构化 T1xxx),紫队永远不批 valid。
2. **深层原因(reviewer 暴露)**:第 2~5 轮 `consistent=False`——红队攻击链与蓝队告警**资产命名/攻击路径不一致**,两个 agent 未共用同一事实源。
3. **对照`_evaluate_stop` 收敛判据**(`converged` 需"本轮无新步骤**且**紫队 valid";`no_progress` 需"连续≥2 轮无新步骤")——本场红队第 3、4、5 轮仍有新增攻击、紫队一直 False,所以两个提前收敛路径都走不通,只能 `max_rounds` 兜底。

---

## 五、与 mock 运行的差异(答辩需知)

| | mock(此前已演示) | 真实大模型(本次) |
|---|---|---|
| 资产/链路 | 写死、红蓝紫完美对齐 | LLM 每次输出略异 |
| 技法编号 | 天然带 T1110 | 不稳定输出,常缺 |
| 收敛 | 3 轮内 2→1→0 完美收敛 | 5 轮未收敛(consistency 问题) |
| 展示价值 | "收敛算法"演示 | "决策轨迹可观测 + 真实协作一致性问题"披露 |

> 答辩定位:mock 用于演示"收敛算法"闭环;真实运行用于展示系统**诚实记录每一次 agent 输入输出**(可观测性),同时如实呈现真实 LLM 协作的挑战。

---

*待办建议(见 `攻防优化任务线-执行档案.md` 与沟通):落地 WarfareMaster 共享 state 的"事实源强约束"——统一资产命名、链路与事件流作为 state 唯一事实,红/蓝/紫各链强制引用而非各自生成。*