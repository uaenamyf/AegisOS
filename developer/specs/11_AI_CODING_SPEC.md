# 11_AI_CODING_SPEC.md — AI 编码规范

> 上游：`00_PROJECT_SPEC.md`。本文件**不是给人看的，而是专门给 Claude Code / Cursor / Codex / GPT 等 AI Coding Agent 的**。
> 任何 AI Agent 在本仓库动手前，**第一步必须阅读本文件 + `AGENT.md`（根）+ `developer/specs/00_PROJECT_SPEC.md`**。
> 违反本规范的 AI 改动一律视为无效，须回滚重做。

---

## 1. AI 修改代码前必须读取的文件（Mandatory Pre-Read）

按顺序，缺一不可：

| 顺序 | 文件 | 作用 |
|------|------|------|
| 1 | `AGENT.md`（根） | 仓库总规范、必读顺序、全局铁律 |
| 2 | `developer/specs/00_PROJECT_SPEC.md` | 项目 SSOT、目标/边界/生命周期/commit/review |
| 3 | `developer/specs/03_IMPORT_SPEC.md` | 依赖矩阵、禁止 import（**AI 最易犯错**） |
| 4 | `developer/specs/11_AI_CODING_SPEC.md` | 本文件 |
| 5 | 目标模块的 `AGENT.md` | 职责/读取目录/**禁止修改目录**/接口/测试方式 |
| 6 | `developer/roadmap/README.md` | 定位当前阶段（P0..P7），不做超阶段的事 |
| 7 | `protocol/` 相关契约 + `developer/specs/04_PROTOCOL_SPEC.md` | 数据类型 |
| 8 | `developer/specs/05_API_SPEC.md` + 目标域 `api/__init__.py` | 接口签名 |
| 9 | `tooling/configs/` 相关配置 | 运行配置 |

> **铁律**：AI 永不扫描整个项目；按模块边界精准读写。修改前未读对应 `AGENT.md` 的「禁止修改目录」 = 越界违规。

---

## 2. AI 单次允许修改范围（Scope Limit）

| 限制 | 规则 |
|------|------|
| 单次最多修改模块数 | **≤ 1 个域**（如仅 `aegisos_agents/` 或仅 `backend/`）；跨域改动须拆多次并分别 Review |
| 单次最多修改文件数 | 建议 ≤ 8 个文件；超出须说明必要性 |
| 单次最多新增代码行 | 建议 ≤ 500 行；超出须拆分 |
| 禁止一次性大重构 | 重构须分步、保持行为不变、每步可测 |

> 例外：`protocol/` 契约变更属破坏性，须单独 PR + major bump + 通知依赖方，不与其他改动混在一起。

---

## 3. AI 是否允许创建新文件（File Creation）

| 场景 | 允许？ | 条件 |
|------|--------|------|
| 在目标模块「读取目录」内创建实现文件 | ✅ | 须补对应测试 |
| 新增 Agent 角色 | ✅ | 须补 `AGENT.md` + 在 `aegisos_agents.api` 注册 + 配置 |
| 新增工具 | ✅ | 须注册 `ToolSpec` + `AGENT.md` |
| 新增测试文件 | ✅（鼓励） | 放 `tests/{unit,integration,e2e,benchmarks}/` 镜像结构 |
| 新增配置 | ✅ | 放 `tooling/configs/`，密钥走环境 |
| 在「禁止修改目录」内创建 | ❌ | 越界 |
| 在 `developer/specs/` 之外造新规范 | ❌ | 规范集中于 `developer/specs/` |
| 在 `protocol/` 之外造并行数据契约 | ❌ | 破坏唯一契约 |
| 创建无关文档/README | ❌ | 根 README 由脚本生成，勿手改自动段 |

---

## 4. AI 是否允许修改协议（Protocol Mutation）

| 对象 | 允许？ | 条件 |
|------|--------|------|
| `protocol/*.py` 现有字段语义/类型 | ❌（破坏性） | 须架构师确认 + major bump + CHANGELOG + 通知依赖方 |
| 新增可选字段（带默认值） | ⚠️ 须谨慎 | 须同步 `04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md` + 测试 |
| 新增 `EventType` | ⚠️ 须谨慎 | 须双登记（`protocol/event.py` + `07_EVENT_SPEC.md`）+ CHANGELOG |
| 新增契约类型 | ⚠️ 须谨慎 | 须同步 `04`/`06` + `protocol/__init__.py` 导出 + 测试 |
| 字段废弃 | ⚠️ | 先 deprecated 一个 minor，不可直接删 |

> AI 默认**不得擅自修改协议**；如确需修改，须在 PR 中显式声明「破坏性变更」并走 §7 流程。

---

## 5. AI 是否允许修改 API（API Mutation）

| 对象 | 允许？ | 条件 |
|------|--------|------|
| 域 `api/__init__.py` 既有方法签名 | ❌（破坏性） | 须 major bump + CHANGELOG + 通知依赖方 |
| 新增 `api/` 方法（可选/新接口） | ⚠️ 须谨慎 | 须同步 `05_API_SPEC.md` + `10_INTERFACE_BOUNDARY_SPEC.md` + 测试 |
| 内部实现重构（api 签名不变） | ✅ | 须保持 api 行为契约 + 测试通过 |
| 跨域内部子包 import | ❌ | 须只经 `api/`（见 `03_IMPORT_SPEC.md`） |

> AI 默认**不得擅自修改 API 签名**；新增方法须评估对既有实现的影响。

---

## 6. AI 如何生成测试（Test Generation）

- **每个公共接口必有测试**；bug 修复附**回归测试**。
- 测试位置：`tests/{unit,integration,e2e,benchmarks}/` 镜像源码结构。
- 协议/Schema：往返序列化测试（`to_dict`↔`from_dict` / `model_dump`↔`model_validate`）+ 边界值。
- API 契约：mock 实现 `api/` Protocol，验证签名与返回类型为 `protocol/` 类型。
- Agent：mock LLM/工具，验证 `receive→think→tool→reflect→respond` 生命周期 + 事件发布。
- 覆盖率：整体 ≥ 80%，关键路径 ≥ 90%。
- 命名：`test_<被测对象>_<场景>.py`；用 `pytest` + `pytest-asyncio`。
- 禁止：跳过失败测试（`pytest.skip`）掩盖问题；禁止删除他人回归测试。

---

## 7. AI 如何更新文档（Doc Sync）

| 改动类型 | 必须同步的文档 |
|----------|----------------|
| 协议变更 | `04_PROTOCOL_SPEC.md` + `06_SCHEMA_SPEC.md` |
| API 变更/新增 | `05_API_SPEC.md` + `10_INTERFACE_BOUNDARY_SPEC.md` |
| 事件变更/新增 | `07_EVENT_SPEC.md` + `protocol/event.py` |
| Agent 变更 | `08_AGENT_SPEC.md` + 对应 `AGENT.md` |
| 目录/api 结构变更 | 运行 `python3 tooling/scripts/gen_readme.py` 刷新根 `README.md` |
| 任何变更 | `developer/CHANGELOG.md` |
| 阶段完成 | `developer/roadmap/README.md` 勾选进度 |

- 文档与代码**同一 PR**提交；文档滞后 = 未完成。
- 不手改根 `README.md` 自动生成段。
- 不添加无关注释（解释 what 而非 why 的冗余注释）；意图由测试与命名表达。

---

## 8. AI 如何处理冲突（Conflict Handling）

| 冲突类型 | 处理 |
|----------|------|
| 与他域 `api/` 契约冲突 | **契约优先**：以 `05_API_SPEC.md`/`04_PROTOCOL_SPEC.md` 为准；AI 不得单方改契约 |
| 与他域实现冲突 | 经 `api/` 解耦，不改他域内部；必要时提 issue 协调 |
| Import 冲突（循环/跨域内部） | 按 `03_IMPORT_SPEC.md` 用接口/事件打破；不改依赖方向 |
| Git merge 冲突 | AI 须保留双方有效改动，不得静默删除他方代码；冲突解决后跑质量门禁 |
| 规范间冲突 | 优先级：`00` > `04`≈`05`≈`06` > 其余编号规范 > `developer/` 根旧文档 > 模块 `AGENT.md` |
| 测试与实现冲突 | 以测试反映的契约为准；若实现正确则修正测试，须说明理由 |

---

## 9. AI 禁止事项（Hard Don'ts）

1. ❌ 扫描整个项目后大范围改动（须按模块边界精准读写）。
2. ❌ 越界修改目标 `AGENT.md` 的「禁止修改目录」。
3. ❌ 在 `protocol/` 之外造并行数据结构。
4. ❌ 跨模块裸 JSON / `dict` 传递（须走 `Message` 信封 + `protocol` 类型）。
5. ❌ 跨域 import 内部子包（须经 `api/`）。
6. ❌ 引入循环依赖。
7. ❌ 全广播通信（须低熵链式路由）。
8. ❌ 提交密钥/凭据；日志记录敏感载荷。
9. ❌ 擅自修改 `api/` 签名或 `protocol/` 字段语义（破坏性须声明 + 走流程）。
10. ❌ 跳过质量门禁（`ruff format && ruff check --fix && mypy && pytest`）。
11. ❌ 删除/跳过他人回归测试。
12. ❌ 手改根 `README.md` 自动生成段。
13. ❌ 添加未在 `tooling/configs` 登记的三方依赖。
14. ❌ 做超阶段（roadmap）的开发。
15. ❌ AI 首次创建文件不加文件头注释（文件说明 + date + dev，见 §10.1）。
16. ❌ AI 增改函数/方法/接口时不加变更注释（date + dev + changelog + 代码注释，见 §10.2）。

---

## 10. 代码注释与 docstring 规范（强制）

> **凡 AI 创建文件或增改函数/方法/接口，必须加注释头；凡 Python 模块、类、公开函数/方法必须有 docstring。** 晦涩难懂的代码行须加行内注释。缺失注释的代码一律视为未完成，须补全方可提交。

### 10.1 文件头注释（首次创建文件）

> **AI 首次创建任一代码文件时，必须在文件顶部写注释头：先说明该文件做什么，再标注 `date` 和 `dev`。**

**Python 示例**（参考 `backend/main.py`）：
```python
# date: 2026-06-27
# dev: myf
"""AegisOS 后端 FastAPI 应用入口。

本模块负责创建并配置 FastAPI 应用实例，包括：日志初始化、CORS 跨域、
Trace ID 中间件、健康检查/网关/WebSocket 路由挂载、统一错误响应格式化。
"""
```

**TypeScript 示例**：
```typescript
// date: 2026-06-27
// dev: myf
/**
 * 会话管理 API 服务 — 封装与后端 /api/session 端点的交互。
 */
```

| 字段 | 必填 | 格式 | 说明 |
|------|:----:|------|------|
| `date` | ✅ | `YYYY-MM-DD`（ISO 8601） | 文件创建日期 |
| `dev` | ✅ | git 用户名或人类名 | 开发人员；以 `git config user.name` 为准，如 `myf`、`张三`；**禁写** AI 工具名/模型名 |
| 文件说明 | ✅ | docstring 或块注释 | 一段话说明该文件职责与核心功能 |

### 10.2 变更注释（增改函数/方法/接口）

> **AI 后续对已有文件的函数、方法、接口进行新增或修改时，必须在改动处正上方写变更注释头：标注 `date`、`dev`、`changelog`，并为生成的代码添加注释以保证可读性。**

**Python 示例**：
```python
# date: 2026-07-05
# dev: myf
# changelog: 新增 retrieve 方法，支持向量+关键词混合检索
def retrieve(query: dict) -> list:
    """检索与 query 相关的记忆片段。"""
    ...
```

**TypeScript 示例**：
```typescript
// date: 2026-07-05
// dev: myf
// changelog: 新增 createSession 方法，调用后端创建会话端点
export async function createSession(): Promise<Session> {
  ...
}
```

| 字段 | 必填 | 格式 | 说明 |
|------|:----:|------|------|
| `date` | ✅ | `YYYY-MM-DD`（ISO 8601） | 改动日期 |
| `dev` | ✅ | git 用户名或人类名 | 开发人员；以 `git config user.name` 为准；**禁写** AI 工具名/模型名 |
| `changelog` | ✅ | 一句话祈使/陈述 | 本次改了什么（做了什么） |

> 多人/AI 接续修改同一段时，**追加**新注释头于上方，**不删除**既有注释头，形成改动历史栈（最新在上）。

### 10.3 docstring 覆盖范围

| 元素 | 是否必须 docstring | 说明 |
|------|:------------------:|------|
| 模块（文件级） | ✅ | 文件顶部三引号 docstring，说明文件职责 |
| class | ✅ | 说明类的用途，含 `Attributes` 段列出公开属性 |
| 公开函数/方法（`public`，非 `_` 前缀） | ✅ | Google 风格，含 `Args`/`Returns`/`Raises`（按需） |
| 私有函数/方法（`_` 前缀） | 推荐 | 简短说明即可 |
| `__init__` | ✅ | 说明构造参数 |
| 常量/枚举 | 推荐 | 行内注释说明含义 |
| 晦涩代码行 | ✅ | 行内注释（`# ...`）解释 why |

### 10.4 docstring 风格

统一使用 **Google 风格**（与 Sphinx / napoleon 兼容）：

```python
"""检索与 query 相关的记忆片段。

通过向量相似度 + 关键词匹配 + 图遍历混合检索，返回 Top-K 记忆。

Args:
    query: 查询字典，含 `text`（str）和 `session_id`（str）。
    top_k: 返回记忆条数上限，默认 5。

Returns:
    list[MemoryPacket]: 按相关度降序排列的记忆列表。

Raises:
    ValueError: 当 query 为空或 top_k <= 0 时。
"""
```

### 10.5 行内注释规则

- **解释 why，而非 what**：代码本身已表达 what，注释应说明**为什么**这样做。
- **晦涩逻辑必须注释**：算法步骤、正则匹配、位运算、降级/回退逻辑、魔法数字等。
- **简单直观的代码不需要注释**：避免冗余（如 `i += 1  # i 加 1`）。
- **注释语言用中文**。

---

## 11. AI 标准作业流程（SOP）

```
1. 读必读文件（§1）
2. 定位当前 roadmap 阶段，确认任务不超阶段
3. 确认目标模块 AGENT.md 的「读取目录/禁止修改目录/接口/测试」
4. 确认依赖契约（protocol/ + api/ + configs/）
5. 实现（单次 ≤1 域，遵循 Spec→Contract→API→Implementation→Test→Document）
   — 首次创建文件：文件头注释（文件说明 + date + dev，见 §10.1）
   — 增改函数/方法/接口：变更注释（date + dev + changelog + 代码注释，见 §10.2）
   — 为所有模块/类/公开函数添加 docstring + 晦涩代码行内注释（见 §10.3-10.5）
6. 生成/更新测试（§6）
7. 运行质量门禁至全绿
8. 同步文档与 CHANGELOG（§7）
9. 目录/api 变动 → 刷新根 README
10. git add <仅相关文件> → commit（§00 §13 格式）
```

> AI 每次提交须能在 PR 描述中回答：「我读了哪些规范？我改了哪个域？是否触及协议/API？是否同步了文档与 CHANGELOG？」
