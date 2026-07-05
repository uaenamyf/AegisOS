# 03_IMPORT_SPEC.md — Import 规范

> 上游：`00_PROJECT_SPEC.md`、`02_DIRECTORY_SPEC.md`。本文件是 **AI 开发最重要的一份规范**：明确「谁能 import 谁」。
> 违反本文件的 import 一律视为编译/CI 错误，须立即修复。

---

## 1. 依赖方向铁律

依赖严格自上而下，`protocol/` 是唯一被全局依赖的层：

```
frontend  →  backend  →  aegisos_agents  →  protocol
                       ↘          ↗
   observability  →  infrastructure  →  protocol
   data / tooling  →  protocol
   tests  →  任何被测域 api/ + protocol
```

- 箭头 `A → B` 表示 **A 可以 import B 的 `api/` 与 `protocol`**。
- `protocol/` **零反向依赖**：不得 import 任何业务域。
- `developer/` **不被任何运行时代码 import**。

---

## 2. 依赖矩阵（允许 ✅ / 禁止 ❌）

| 调用方 ↓ \ 被调方 → | protocol | aegisos_agents.api | backend.api | infra.api | observ.api | data.api | tooling.api | 任意域内部 |
|---------------------|----------|------------|-------------|-----------|------------|----------|-------------|-----------|
| `frontend/` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `backend/` | ✅ | ✅ | 自用 | ✅ | ✅ | ✅ | ✅ | ❌ |
| `aegisos_agents/` | ✅ | 自用 | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `infrastructure/` | ✅ | ❌ | ❌ | 自用 | ❌ | ❌ | ❌ | ❌ |
| `observability/` | ✅ | ❌（订阅事件） | ❌ | ❌ | 自用 | ❌ | ❌ | ❌ |
| `data/` | ✅ | ❌ | ❌ | ❌ | ❌ | 自用 | ❌ | ❌ |
| `tooling/` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 自用 | ❌ | ❌ |
| `protocol/` | 自身 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `tests/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 仅被测域 api/ |

> 说明：
> - `aegisos_agents/` ↔ `backend/`：`backend` 调 `aegisos_agents.api`（应用层编排智能体）；`aegisos_agents` 不得反向调 `backend`。
> - `observability/` 订阅事件走 EventBus（`aegisos_agents.api.EventBusAPI` 或直接订阅 Event 流），不直接 import aegisos_agents 内部。
> - `frontend` 只与 `backend` 交互，绝不直连 `aegisos_agents`/`infrastructure`。

---

## 3. 禁止的 Import（Forbidden）

| # | 禁止项 | 理由 |
|---|--------|------|
| F1 | import 任意域的**内部子包**（非 `api/`） | 破坏 API 解耦 |
| F2 | 在 `protocol/` 之外定义/导入并行数据契约 | 破坏唯一契约 |
| F3 | `protocol/` import 任何业务域 | 零反向依赖 |
| F4 | 运行时代码 import `developer/` | 规范层不参与运行时 |
| F5 | `aegisos_agents` import `backend` | 逆向依赖 |
| F6 | `frontend` import `aegisos_agents`/`infrastructure` | 须经 backend |
| F7 | 循环 import（任何形式） | 见 §4 |
| F8 | 业务层裸 `import json` 跨模块传 dict | 须走 `Message` 信封 + `protocol` 类型 |
| F9 | import 未在 `tooling/configs` 登记的三方库 | 依赖须经评估并记录 |
| F10 | 跨 `AGENT.md`「禁止修改目录」的 import | 越界 |

---

## 4. 循环依赖（Circular Dependency）

- **绝对禁止**任何形式的循环 import（模块级/包级）。
- 若 A 与 B 双向需要：引入 `protocol/` 中的共享契约类型，或经 `api/` 接口 + DI 注入打破环。
- EventBus 是天然解耦点：生产者发布事件、消费者订阅，二者不互相 import。
- CI 须有循环依赖检测（如 `pydeps`/`grimp` 静态检查）。

---

## 5. API Import 规范（跨域）

跨域调用**唯一合法形式**：

```python
from {domain}.api import XxxAPI   # ✅ 只导入 Protocol 接口
```

- 接口参数/返回值**必须**使用 `protocol/` 类型。
- **禁止**：`from {domain}.internal_pkg import something`。
- 实现由各域内部通过 DI 注入到接口；调用方只持有接口，便于 mock。
- `api/` 签名变更 = 破坏性变更（major bump + CHANGELOG + 通知依赖方）。
- **DI 端口（DIP 例外，不算逆向）**：`aegisos_agents/api/ports.py` 定义的反向端口（`PersistencePort`/`SessionPort`/`TaskUpdatePort`）由 aegisos_agents 域消费（`from aegisos_agents.api.ports import ...`，同域 ✅），由 backend 实现（`from aegisos_agents.api.ports import PersistencePort`，正向 ✅）。这是依赖反转（DIP），**不构成** `agents → backend` 逆向依赖。组合根 `backend/composition.py` 负责注入。详见 `plans/13_FRONTEND_BACKEND_PLAN.md` §3.2、`10_INTERFACE_BOUNDARY_SPEC.md` §5。

---

## 6. Internal Import 规范（域内）

- 域内部模块间可自由 import，**但仅限该域内部**。
- 仍须避免域内循环 import；必要时用接口/事件解耦。
- 域内部重构不影响他域（只要 `api/` 签名不变）。

---

## 7. Plugin Import 规范（插件）

- 插件（Agent 角色 / 工具 / LLM 适配 / 记忆后端 / 节点 / 视图）**实现**内核定义的接口（`api/` Protocol）。
- 插件通过**注册表**接入，不被业务代码硬 import；内核通过注册表按名加载。
- 插件可 import `protocol/`；可 import 本域 `api/` 以接入；**禁止** import 他域内部。
- 工具声明 `ToolSpec`；Agent 声明 `Agent`（capabilities）；由 `aegisos_agents/action/execution/tools/` 与 `aegisos_agents/api/AgentRegistryAPI` 统一注册。

---

## 8. Relative vs Absolute Import 规范

| 规则 | 说明 |
|------|------|
| **跨域 import** | 必须 **Absolute**：`from protocol import Message`、`from aegisos_agents.api import MemoryAPI` |
| **域内 import** | 优先 **Absolute**（基于包根）；短距离同级可用 **Relative（≤1 层，仅 `from . import` 或 `from .module import`）** |
| **禁止** | 跨包的深层 relative（`from ....x import y`），可读性差且易破坏 |
| **禁止** | 拼接字符串动态 import 跨域模块（反射跨域调用绕过 api 解耦） |

示例：
```python
# ✅ 跨域绝对
from protocol import Message, Task, Plan
from aegisos_agents.api import MemoryAPI, RuntimeAPI

# ✅ 域内绝对
from aegisos_agents.memory.retrieval import Retriever

# ✅ 域内短距离 relative
from .eventbus import EventBus

# ❌ 禁止
from aegisos_agents.memory.internal_index import _Helper   # 跨域内部
from ....protocol import Message                   # 深层 relative
```

---

## 9. 校验与执行

- **CI 静态检查**：依赖方向矩阵 + 循环检测 + 禁止内部 import（建议 `grimp`/`pydeps` + 自定义规则）。
- **mypy**：确保 `api/` 接口类型一致，禁止 `Any` 跨域传递（payload 除外，须 `protocol` 类型标注）。
- **ruff**：import 排序与未使用 import 检测。
- 违反本规范的 PR **不予合并**。
