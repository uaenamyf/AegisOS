# developer/ 模块实现文档

> 规范层（项目大脑）— specs（SSOT 唯一真相源） · roadmap（P0-P7 阶段计划） · CHANGELOG。

📁 模块规范：[`AGENT.md`](AGENT.md) · 项目 SSOT：[`specs/00_PROJECT_SPEC.md`](specs/00_PROJECT_SPEC.md)

---

## 目录结构

```
developer/
├── CHANGELOG.md            ✅ 变更记录
├── specs/                  ✅ 15 个规范文件（唯一真相源）
│   ├── 00_PROJECT_SPEC.md      项目 SSOT
│   ├── 01_ARCHITECTURE_SPEC.md 系统架构
│   ├── 02_DIRECTORY_SPEC.md    目录规范
│   ├── 03_IMPORT_SPEC.md       Import 规范
│   ├── 04_PROTOCOL_SPEC.md     通信协议
│   ├── 05_API_SPEC.md          API 契约
│   ├── 06_SCHEMA_SPEC.md       数据 Schema
│   ├── 07_EVENT_SPEC.md        事件总线
│   ├── 08_AGENT_SPEC.md        Agent Runtime
│   ├── 09_DEVELOPMENT_SPEC.md  开发流程
│   ├── 10_INTERFACE_BOUNDARY_SPEC.md  接口边界
│   ├── 11_AI_CODING_SPEC.md    AI 编码规范
│   ├── 12_TECH_STACK_SPEC.md   技术栈
│   └── plans/
│       ├── 13_FRONTEND_BACKEND_PLAN.md    前后端全流程
│       ├── 14_CYBERDEFENSE_SOLUTION_PLAN.md 赛事总体方案
│       └── 15_CYBERDEFENSE_TASKS.md       赛事实施任务清单
└── roadmap/                ✅ P0-P7 阶段计划
    ├── README.md              阶段总览（含进度勾选）
    ├── P0/                    ✅ 完成
    ├── P1/                    ✅ 完成
    ├── P2/                    ✅ 完成
    ├── P3/                    ✅ 完成
    ├── P4/                    ✅ 完成
    ├── P5/                    ✅ 完成（编排器待补）
    ├── P6/                    ✅ 部分完成（攻防视图待补）
    └── P7/                    🔲 未开始
```

---

## 规范体系（specs/）

### 必读优先级

```
00 > 04 ≈ 05 ≈ 06 > 其余编号 > 各模块 AGENT.md
```

### 规范索引

| 编号 | 文件 | 核心内容 |
|------|------|---------|
| 00 | [`00_PROJECT_SPEC.md`](specs/00_PROJECT_SPEC.md) | 项目目标/边界/原则/分层/生命周期/commit/review |
| 01 | [`01_ARCHITECTURE_SPEC.md`](specs/01_ARCHITECTURE_SPEC.md) | 分层/微内核/DDD/事件驱动/各 Runtime |
| 02 | [`02_DIRECTORY_SPEC.md`](specs/02_DIRECTORY_SPEC.md) | 每目录职责/边界/可改性 |
| 03 | [`03_IMPORT_SPEC.md`](specs/03_IMPORT_SPEC.md) | 依赖矩阵/禁循环（**AI 最重要**） |
| 04 | [`04_PROTOCOL_SPEC.md`](specs/04_PROTOCOL_SPEC.md) | Message/Event/Task/Graph/低熵稀疏§16/异构选举/端边云/§18 Cyber |
| 05 | [`05_API_SPEC.md`](specs/05_API_SPEC.md) | 27 接口 × Request/Response/Error/Timeout/Retry/Version |
| 06 | [`06_SCHEMA_SPEC.md`](specs/06_SCHEMA_SPEC.md) | 数据 Schema（dataclass，§12 待迁 Pydantic）/§14 CyberSchema |
| 07 | [`07_EVENT_SPEC.md`](specs/07_EVENT_SPEC.md) | 8 事件/生命周期/可靠性/追踪 |
| 08 | [`08_AGENT_SPEC.md`](specs/08_AGENT_SPEC.md) | Agent 生命周期/API/Prompt/Memory/Tool |
| 09 | [`09_DEVELOPMENT_SPEC.md`](specs/09_DEVELOPMENT_SPEC.md) | Spec→Contract→API→Impl→Test→Doc |
| 10 | [`10_INTERFACE_BOUNDARY_SPEC.md`](specs/10_INTERFACE_BOUNDARY_SPEC.md) | 接口边界：谁调谁/异步/网关/EventBus |
| 11 | [`11_AI_CODING_SPEC.md`](specs/11_AI_CODING_SPEC.md) | AI 必读/范围/禁改协议 API/测试/`@aegis-gen` §10 |
| 12 | [`12_TECH_STACK_SPEC.md`](specs/12_TECH_STACK_SPEC.md) | 语言/运行时/框架/库/工具链/版本 |

### 计划文档（specs/plans/）

| 编号 | 文件 | 内容 |
|------|------|------|
| 13 | [`13_FRONTEND_BACKEND_PLAN.md`](specs/plans/13_FRONTEND_BACKEND_PLAN.md) | 前后端全流程：双向调用/DI 端口/FastAPI |
| 14 | [`14_CYBERDEFENSE_SOLUTION_PLAN.md`](specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md) | 赛事总体方案：架构/角色/算法/3 场景/评分对齐 |
| 15 | [`15_CYBERDEFENSE_TASKS.md`](specs/plans/15_CYBERDEFENSE_TASKS.md) | 实施任务清单：Phase A-H，核心算法 TDD |

---

## roadmap（P0-P7）

| 阶段 | 名称 | 状态 |
|------|------|------|
| P0 | 项目初始化 | ✅ 完成 |
| P1 | Protocol | ✅ 完成 |
| P2 | Memory | ✅ 完成（10 子模块待补） |
| P3 | Router | ✅ 完成 |
| P4 | Scheduler | ✅ 完成 |
| P5 | Planner + Agents | ✅ 完成（编排器/runtime 集成待补） |
| P6 | Frontend | ✅ 部分完成（攻防视图待补） |
| P7 | Deployment | 🔲 未开始 |

详见：[`roadmap/README.md`](roadmap/README.md)

---

## CHANGELOG

[`CHANGELOG.md`](CHANGELOG.md) 记录每次会话的变更，按阶段标记（如 `[P6]`）。
