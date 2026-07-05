# Roadmap — 系统级开发计划总览

> AegisOS 按 P0..P7 分阶段推进。每个阶段目录 `developer/roadmap/P{n}/` 含详细文档。Agent 据此定位「现在做哪一步、下一步是什么」。本文件隶属 `developer/` 规范层。

## 阶段总览
```
P0 项目初始化
  -> P1 Protocol
  -> P2 Memory
  -> P3 Router
  -> P4 Scheduler
  -> P5 Planner + Agents
  -> P6 Frontend
  -> P7 Deployment
```

| 阶段 | 名称 | 目标 | 完成标准 | 详见 |
|------|------|------|----------|------|
| P0 | 项目初始化 | 搭建骨架与开发规范 | 可运行空壳 + 文档就位 | developer/roadmap/P0/README.md |
| P1 | Protocol | 定义通信协议 | 协议可序列化往返 | developer/roadmap/P1/README.md |
| P2 | Memory | 记忆子系统 | 可读写检索 + 压缩 | developer/roadmap/P2/README.md |
| P3 | Router | 动态图路由 | 动态路由可计算 | developer/roadmap/P3/README.md |
| P4 | Scheduler | 调度器 | 任务可调度执行 | developer/roadmap/P4/README.md |
| P5 | Planner+Agents | 规划器与 Agent | 群体完成端到端任务 | developer/roadmap/P5/README.md |
| P6 | Frontend | AI Native IDE | 可视化可交互 | developer/roadmap/P6/README.md |
| P7 | Deployment | 部署交付 | 开箱可部署 | developer/roadmap/P7/README.md |

## 阶段输出路径（分层后）
- P0: 分层目录骨架 + developer/ + 全部 AGENT.md
- P1: `protocol/*.py`
- P2: `agents/memory/`（12 子模块）
- P3: `agents/planning/engine/topology/` + `agents/planning/engine/router/`
- P4: `agents/planning/engine/scheduler/`
- P5: `agents/planning/engine/planner/` + `agents/`（角色 + runtime）
- P6: `frontend/` + `backend/`
- P7: `infrastructure/delivery/deployment/` + `tooling/scripts/`

## 每阶段统一字段
目标 / 输入 / 输出 / 接口 / 测试 / 风险 / 完成标准。

## 当前进度
- [x] P0 目录结构（同域聚合分层）与 AGENT.md 体系
- [x] P1 Protocol 实现（cyber.py 8 类型 + memory/graph/scheduler 字段扩展，6 测试）
- [x] P2 Memory 实现（compression/compactor.py + recall/recaller.py，7 测试；其余 10 子模块待补）
- [x] P3 Router 实现（topology 活跃子图 + router Top-K 稀疏路由 + election 异构选举，10 测试）
- [x] P4 Scheduler 实现（端边云三层调度 device/edge/cloud + 多模型兼容层 model_router，13 测试）
- [~] P5 Planner + Agents 实现（11 红蓝紫 Agent + 神经符号闭环已完成 23 测试；planner/orchestrator/workflow/eventbus 编排器待补；B3 runtime 集成待补；E13 e2e 测试待补）
- [~] P6 Frontend 实现（5 视图占位 + Chat 联调已完成；攻防视图 G1-G3 + 后端攻防端点 F 待补）
- [ ] P7 Deployment 实现

## 赛事作品对齐（XH-202631 荣耀·超长程群体智能）

> 赛事作品以 AegisOS 为底座，落地「面向超长程网络攻击防御的动态异构群体智能协同推理引擎」。总体方案见 `developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md`，可执行任务清单见 `plans/15_CYBERDEFENSE_TASKS.md`。各阶段映射：

| roadmap | 赛事作品扩展 |
|---------|------------|
| P1 Protocol | 新增 `protocol/cyber.py` 攻防类型（Asset/AttackChain/Alert/DefenseAction/...） |
| P2 Memory | 12 子模块 + 超长程压缩/唤醒（ATT&CK/CVE/向量/情景） |
| P3 Router | 低熵稀疏路由（Top-K，非全广播）+ 动态异构选举 |
| P4 Scheduler | 调度 + 端边云卸载（云大模型/端小模型） |
| P5 Planner+Agents | 红蓝紫 Agent 角色 + 神经-符号协同推理闭环 |
| P6 Frontend | 5 视图（攻击链 DAG/防御看板/时序回放）+ 后端攻防端点 |
| P7 Deployment | Docker 沙箱靶场 + Neo4j/Qdrant + 3 场景演示 + 5 维度评测 |

- 截止：2026-09-15 提交；增量交付，每阶段可演示；优先跑通场景 1（网络防御）。

> 维护规则：每完成一阶段在 `developer/CHANGELOG.md` 记录，并勾选此处。
