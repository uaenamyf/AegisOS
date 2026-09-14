# Handoff — AegisOS 工作交接

> 记录时间:2026-09-12 15:17 (Asia/Shanghai)
> 交接原因:2026-09-04 旧交接已被消化;本文件按当前状态重写。

---

## 1. 项目概况

- **项目**:AegisOS —— Agent Operating System (AOS) + AI Native IDE
- **赛题**:挑战杯揭榜挂帅 + 荣耀群体智能赛题「面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术」
- **方案 PDF**:仓库根目录 `XH-202631荣耀终端股份有限公司-...比赛方案.pdf`
- **顶层结构**:frontend / backend / aegisos_agents / protocol / infrastructure / observability / data / tooling / docs / tests / developer
- **规范入口**:`developer/plan.md`(任务清单)、`developer/CHANGELOG.md`、`AGENT.md`

## 2. 当前状态(2026-09-14)

- **cyber-drill R1-R11 全部完成**;2026-09-12 追加可用性修复(CYBER-DRILL-USABILITY):
  - 阶段级 SSE `drill_stage` 事件(红/蓝/紫推进实时可见)
  - Chat 发起 → Cyber 面板接管(running 快照 + SSE 补订阅 + 终态展示)
  - 运行中 get_drill 返回实时轮次(修复 Chat 轮询误报超时)
  - 前端进度条「第 X/N 轮 · 当前阶段」
- **2026-09-14 R21 前端视图收敛(TASKMAP)**:
  - Graph + Canvas 合并为「任务图 TaskMap」(`views/taskmap/`):Chat 对话流 / Cyber 演练流
    双模式切换;点节点看 Agent 输入/输出(低代码风格);演练随新一轮整体刷新不堆叠;
    历史下拉回看;底部对话记忆条
  - Replay / Canvas / Graph 视图与路由移除(6 个导航:Chat/Task Map/Monitor/Cyber Defense/演练历史/运行配置)
  - 演练历史页新增「↗ 在任务图中查看」跳转;ChatView 快照 key 迁移为 aegis.taskmap.drill.*
  - 路由验证:三节点 online、real 模式、phase 决策 red→device/blue→edge/purple→cloud 正常;
    本地 Ollama 按用户要求不配置
- **验证基线**:Python 82 passed(路由相关)· 前端单测 50 passed · tsc/vite build 成功 ·
  Playwright 任务图 5 用例通过
- **注意**:本目录当前**不是 git 仓库**(`.git` 不存在,与 9-04 handoff 记录的 `1cd9ffe` 不符,可能仓库在别处或未初始化;待用户确认)

## 3. 下一步优先级

1. 赛事材料最终校对(README/档案/方案 PDF 一致性,截止 2026-09-15)
2. 演示视频素材(可选)——`.\tooling\scripts\drill_demo.ps1` 一键无人干预演示
3. 真实靶场/容器联调(场景 2/3 真实化,截止后可选)
4. Protocol→Pydantic 迁移 / CVE 数据集补全(长期项)

## 4. 环境事实(重要)

- 机器无独立 Python 安装,用 WindowsApps 3.13.14;uv 在 hermes/bin
- start.ps1 自动探测 Python + UTF-8 BOM(PS 5.1 无 BOM 会按 GBK 解析中文注释报错)
- 后端不带 --reload 时改代码必须重启;vite 默认绑 ::1(localhost 通,127.0.0.1 不通)
- Playwright 偶发 worker 崩溃 0xC0000409(Windows),复跑即可
- 模式相关测试注意当前 mode(ark 真实 / mock),环境态断言需对应模式

## 5. 恢复工作指引

1. 读取本文件 + `developer/plan.md` + `memory/2026-09-12-cyber-usability.md`
2. 确认 git 状态(见 §2 注意事项)
3. 演示入口:`.\tooling\scripts\drill_demo.ps1`
4. 启动方式见 `README.md` 与根目录 `start.ps1` / `start.sh`
5. 历史变更查 `developer/CHANGELOG.md`
