# developer/specs/ — AegisOS 规范体系（Single Source of Truth）

> 本目录是 AegisOS 的**唯一规范真相源**。采用 **Spec First Development**：在规范（P0）未完成前，任何人/AI 不得编写业务代码。
> 本目录编号规范是 `developer/` 根下旧版散落文档（`API_SPEC.md`/`MESSAGE_PROTOCOL.md`/`EVENT_SPEC.md`/`ARCHITECTURE.md`/`CODING_RULES.md`/`DIRECTORY_GUIDE.md` 等）的权威来源；旧文档已删除，统一以本目录为准。

## 必读顺序

1. `AGENT.md`（根）→ 2. `00_PROJECT_SPEC.md` → 3. `03_IMPORT_SPEC.md` → 4. `11_AI_CODING_SPEC.md` → 5. 目标模块 `AGENT.md` → 6. `developer/roadmap/README.md` → 7. `protocol/` 契约 + `04_PROTOCOL_SPEC.md` → 8. `05_API_SPEC.md`

## 规范索引

| 编号 | 文件 | 内容 | 受众 |
|------|------|------|------|
| 00 | [00_PROJECT_SPEC.md](00_PROJECT_SPEC.md) | 项目规范 SSOT（目标/边界/原则/分层/生命周期/commit/review） | 全员 |
| 01 | [01_ARCHITECTURE_SPEC.md](01_ARCHITECTURE_SPEC.md) | 系统架构（分层/微内核/DDD/事件驱动/各 Runtime） | 架构 + 全员 |
| 02 | [02_DIRECTORY_SPEC.md](02_DIRECTORY_SPEC.md) | 目录规范（每目录职责/边界/可改性） | 全员 |
| 03 | [03_IMPORT_SPEC.md](03_IMPORT_SPEC.md) | Import 规范（依赖矩阵/禁循环/AI 最重要） | AI + 全员 |
| 04 | [04_PROTOCOL_SPEC.md](04_PROTOCOL_SPEC.md) | 通信协议（Message/Event/Task/Graph/...） | 契约维护者 |
| 05 | [05_API_SPEC.md](05_API_SPEC.md) | API 契约（27 接口 × Request/Response/Error/Timeout/Retry/Version） | 前后端 + Agent |
| 06 | [06_SCHEMA_SPEC.md](06_SCHEMA_SPEC.md) | 数据 Schema（Pydantic，10+ Schema） | 契约维护者 |
| 07 | [07_EVENT_SPEC.md](07_EVENT_SPEC.md) | 事件总线（8 事件/生命周期/可靠性/追踪） | Agent + 可观测 |
| 08 | [08_AGENT_SPEC.md](08_AGENT_SPEC.md) | Agent Runtime（生命周期/API/Prompt/Memory/Tool/...） | Agent 团队 |
| 09 | [09_DEVELOPMENT_SPEC.md](09_DEVELOPMENT_SPEC.md) | 开发流程（Spec→Contract→API→Impl→Test→Doc） | 全员 |
| 10 | [10_INTERFACE_BOUNDARY_SPEC.md](10_INTERFACE_BOUNDARY_SPEC.md) | 接口边界（并行开发核心：谁调谁/异步/网关/EventBus） | 前后端 + Agent |
| 11 | [11_AI_CODING_SPEC.md](11_AI_CODING_SPEC.md) | AI 编码规范（给 AI Agent：必读/范围/禁改协议 API/测试/冲突/**代码注释头 @aegis-gen**） | AI Coding Agent |
| 12 | [12_TECH_STACK_SPEC.md](12_TECH_STACK_SPEC.md) | 技术栈规范（语言/运行时/框架/库/工具链/版本约束） | 全员 |
| 13 | [plans/13_FRONTEND_BACKEND_PLAN.md](plans/13_FRONTEND_BACKEND_PLAN.md) | 前后端开发全流程计划（含后端↔智能体双向调用/DI 端口/FastAPI） | 前后端 + Agent |

## 开发阶段（P0..P7）

```
P0 Specification  ← 本目录产出（当前阶段）
   ↓
P1 Contract → P2 Protocol → P3 API → P4 Skeleton
   ↓
P5 Implementation → P6 Testing → P7 Deployment
```

## 冲突优先级

`00_PROJECT_SPEC` > `04_PROTOCOL_SPEC` ≈ `05_API_SPEC` ≈ `06_SCHEMA_SPEC` > 其余编号规范 > 各模块 `AGENT.md`

## 与现有体系的关系

- `protocol/*.py`（26 契约类型）：`04`/`06` 的实现基线；目标向 Pydantic 演进（见 `06` §12）。
- 各域 `api/__init__.py`（27 接口）：`05` 的实现基线。
- 各目录 `AGENT.md`（78 个）：`02` 的模块级细化。
- `developer/roadmap/`：阶段计划，与 `00` §7 / `09` §1 一致。
