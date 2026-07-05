# 12_TECH_STACK_SPEC.md — 技术栈规范

> 上游：`00_PROJECT_SPEC.md`。本文件是 AegisOS **唯一技术栈真相源**：语言、运行时、框架、库、工具链、版本约束与选型理由。
> 所有 AI/人类开发者只能使用本文件登记的技术；新增依赖须经评估并在此登记（见 §7）。冲突时以本文件为准。

---

## 1. 技术栈总览（按层）

| 层 | 域 | 语言/运行时 | 核心依赖 | 状态 |
|----|----|------------|----------|------|
| 契约层 | `protocol/` | Python 3.11+ | Pydantic v2（目标）；现 dataclass 基线 | 迁移中（P1） |
| 智能体域 | `agents/` | Python 3.11+ | asyncio、Pydantic | 待实现 |
| 应用层 | `backend/` | Python 3.11+ | asyncio、Pydantic、**FastAPI**、**Uvicorn**、**SQLAlchemy** | 待实现 |
| 表现层 | `frontend/` | TypeScript 5+ | React 18、Vite 5、**Zustand**、**Vitest**、**Playwright** | 待实现 |
| 基础设施 | `infrastructure/` | Python 3.11+ | asyncio | 待实现 |
| 可观测 | `observability/` | Python 3.11+ | asyncio | 待实现 |
| 数据/工具 | `data/`·`tooling/` | Python 3.11+ | — | 待实现 |
| 部署 | `infrastructure/delivery/` | — | Docker、Kubernetes、Make | 待实现 |

> Python 与 TypeScript 是**仅允许的两种主语言**：后端/Agent/基础设施/可观测/数据/工具/协议用 Python；前端用 TypeScript。

---

## 2. 语言与运行时

| 项 | 选型 | 版本约束 | 理由 |
|----|------|----------|------|
| 后端/Agent/协议等 | Python | **>=3.11** | `typing.Protocol`、`enum`、`dataclass` 成熟；asyncio 稳定 |
| 前端 | TypeScript | **>=5.0** | 类型安全；与 protocol 契约对齐 |
| 异步 I/O | `asyncio` | 标准库 | eventbus/transport/llms/gateway 长耗时 I/O |
| 类型标注 | PEP 484 | 严格 | mypy 强制 |

---

## 3. 后端 / Agent / 协议栈（Python）

| 依赖 | 版本约束 | 用途 | 落点 |
|------|----------|------|------|
| `pydantic` | **>=2.0** | 数据契约 Schema、校验、序列化 | `protocol/`（替换 dataclass）、各域请求/响应校验 |
| `asyncio` | 标准库 | 异步 I/O | eventbus/transport/llms/gateway/runtime |
| `uuid` / `time` / `json` / `dataclasses` / `enum` / `typing` | 标准库 | 契约基线（现有 dataclass 实现） | `protocol/` |
| gRPC | `grpcio` + `grpcio-tools` | 内部高性能 RPC | `aegis.protocol.v1`（Scheduler/Router/Memory/Tool Service） |
| protobuf | 随 grpcio-tools | `.proto` 生成 | 由 `protocol/` 类型生成 |
| **FastAPI** | **>=0.110** | REST/WebSocket/SSE Web 框架 + Pydantic 原生 + OpenAPI | `backend/gateway/`·`backend/controllers/` |
| **Uvicorn** | **>=0.29** | ASGI server | 后端运行时 |
| **httpx** | **>=0.27** | 异步 HTTP 客户端（测试 + 外部调用） | `tests/`·`backend/services/` |
| **SQLAlchemy** | **>=2.0** | ORM（异步引擎） | `backend/mappers/entities/`·`repositories/` |
| **aiosqlite** | **>=0.20** | 异步 SQLite 驱动（dev；生产可换 asyncpg/PostgreSQL） | `backend/mappers/` |

> 现状：`protocol/` 用 `@dataclass` + `typing.Protocol`（v1 基线）。P1 目标：迁移到 Pydantic v2 `BaseModel`（见 `06_SCHEMA_SPEC.md` §12），保持字段名/语义/导出不变，序列化改 `model_dump`/`model_validate`。

---

## 4. 前端栈（TypeScript）

| 依赖 | 版本约束 | 用途 | 落点 |
|------|----------|------|------|
| React | **>=18** | UI 框架 | `frontend/src/views/` |
| TypeScript | **>=5.0** | 类型系统 | 全前端 |
| Vite | **>=5.0** | 构建/开发服务器 | 前端工程 |
| 状态管理 | Zustand **>=4.5** | 轻量全局状态 | `frontend/src/lib/store/` |
| 图渲染 | WebGL / Canvas | 动态图可视化 | `frontend/src/views/graph/`、`canvas/` |
| 实时通信 | 原生 WebSocket + EventSource(SSE) | Agent 状态/事件流 | `frontend/src/services/realtime/` |
| **Vitest** | **>=1.6** | 前端单元测试 | `tests/frontend/` |
| **Playwright** | **>=1.40** | 前端 E2E 测试 | `tests/e2e/` |

> 前端不引入重型框架（如 Next.js SSR）；纯 SPA，经 `backend.core` 通信。前端契约 = `backend.api` 对外接口 + `protocol` 类型（生成 TS 类型）。

---

## 5. 数据序列化与通信

| 项 | 选型 | 说明 |
|----|------|------|
| 默认序列化 | JSON + Schema 校验 | 跨模块/跨网默认 |
| 高性能通道（可选） | MessagePack / protobuf | 大载荷/低带宽；gRPC 用 protobuf |
| 消息信封 | `protocol/message.py` 的 `Message` | 跨模块唯一信封，禁止裸 JSON |
| 传输协议 | REST(HTTP) · WebSocket · SSE · gRPC | 见 `05_API_SPEC.md` §0 |
| gRPC 命名空间 | `aegis.protocol.v1` | `.proto` 由 `protocol/` 类型生成，单一可信源 |

---

## 6. 工具链与质量门禁

| 工具 | 用途 | 命令 |
|------|------|------|
| `ruff` | 格式化 + lint | `ruff format && ruff check --fix` |
| `mypy` | 静态类型检查 | `mypy` |
| `pytest` | 测试框架 | `pytest` |
| `pytest-asyncio` | 异步测试 | 随 pytest |
| `pytest-cov` | 覆盖率 | 整体 ≥80%，关键路径 ≥90% |
| `Make` | 任务编排 | `make setup/test/build/deploy` |
| 依赖管理 | `pyproject.toml`（PEP 621） | Python 依赖声明（P4 建立） |
| 前端构建 | Vite + `tsc` | `npm run build` / `tsc --noEmit` |
| 前端 lint | ESLint + Prettier（建议） | 前端质量门禁 |
| **`gen_ts_types.py`** | Pydantic → TypeScript 类型生成 | `python3 tooling/scripts/gen_ts_types.py`（或 `npm run gen:types`）；CI 强制产物与提交一致 |

**质量门禁（DoD，提交前必绿）**：
```bash
ruff format && ruff check --fix && mypy && pytest
```

---

## 7. 依赖管理规则

1. 新增三方依赖须评估必要性，记录于部署文档，并在本文件登记。
2. Python 依赖声明在 `pyproject.toml`；前端依赖在 `package.json`。
3. **禁止**使用未登记的三方库（CI 校验 lockfile 一致）。
4. **禁止**引入与现有职责重复的库（如另造 dataclass/序列化/路由框架）。
5. 版本约束：用 `>=` 下限 + 必要时 `<` 上限；锁定在 lockfile（`uv.lock`/`poetry.lock`/`package-lock.json`）。
6. 密钥/凭据走环境变量或 `tooling/configs/`，不入依赖、不入代码。

---

## 8. 部署与基础设施

| 项 | 选型 | 用途 |
|----|------|------|
| 容器 | Docker | 镜像化 |
| 编排 | Kubernetes | 云侧编排 |
| CI/CD | GitHub Actions（建议） | 自动质量门禁 + 构建 + 部署 |
| 配置 | YAML（`tooling/configs/`） | environments/agents/models/prompts |
| 端边云 | 离线优先 + 向量时钟同步 | `infrastructure/nodes/{edge,cloud}`、`SyncPacket` |
| 入口 | `backend/gateway/` | 鉴权 + 限流 + 协议适配 |

---

## 9. 可观测栈

| 项 | 用途 | 落点 |
|----|------|------|
| 事件流 | 监控/回放/评估的数据源 | EventBus → `observability/inspect/` |
| 指标 | 延迟/Token/熵/覆盖率 | `observability/measure/` |
| 回放 | 确定性回放 | `observability/inspect/replay/` |
| 可视化 | 图表/图谱/面板 | `observability/present/visualization/`、`frontend/src/views/` |
| 日志 | 脱敏日志 + trace_id | 各模块日志位置（见 `AGENT.md`） |

> 不预设具体 APM 厂商；可观测以自研事件流 + 指标 API 为准，外部 exporter 后续按需接入并在本文件登记。

---

## 10. 版本与兼容

- Python：跟随上游稳定版，下限 3.11。
- Pydantic：v2（不兼容 v1 API；迁移在 P1 完成）。
- 协议/Schema/API 的版本与兼容见 `00` §11、`04` §14、`05` §5。
- 依赖升级：minor 自由；major 须评估破坏性 + CHANGELOG。
