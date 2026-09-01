# Tooling 工程支撑层（域根） — AGENT.md

> 本文件是 `tooling/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
工程支撑层：统一管理全项目的配置（configs）与构建/测试/部署脚本（scripts）。为所有模块提供单一配置源与一键化自动化脚本。

## 读取目录（允许读）
- `developer/`（规范，确定配置 schema 与脚本约定）
- `protocol/`（契约，配置中引用的类型）
- `infrastructure/delivery/deployment/`（部署与脚本协同）

## 禁止修改目录
- `frontend/`、`backend/`、`aegisos_agents/`、`aegisos_agents/planning/engine/`、`aegisos_agents/action/execution/`、`infrastructure/`、`observability/`、`data/` 的业务源码
- `protocol/` 类型定义
- `developer/` 规范文档

## 输出
- `tooling/configs/` 环境与各模块配置（environments/aegisos_agents/models/prompts/各模块 yaml）
- `tooling/scripts/` setup/build/test/deploy 等自动化脚本

## 依赖
- `developer/` 规范
- `infrastructure/delivery/deployment/` 部署目标

## 接口
`load(env) -> Config`；`make setup/build/test/deploy`；详见 `developer/specs/09_DEVELOPMENT_SPEC.md`。

## 测试方式
`pytest tests/tooling/`，校验配置加载与脚本可执行性，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/tooling/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/`（自身即配置源；环境差异通过 `tooling/configs/environments/` 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md` 与 `developer/specs/07_EVENT_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。


## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/09_DEVELOPMENT_SPEC.md
- **API 边界**：tooling/api/ — from tooling.api import ...
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（靶场编排/评测脚本）

## 下辖子模块
- **tooling/api/** 公共接口层：其他模块通过 `from tooling.api import ...` 调用本域能力，不直接访问内部子包，实现解耦。
- `tooling/configs/` 配置：环境覆盖、模块配置、Agent/模型/Prompt 配置（单一配置源）
- `tooling/scripts/` 脚本：环境初始化、一键构建、测试运行、部署

---

## 📋 模块实现详解

> 原 `tooling/MODULE.md` 内容，已合并至此。

### 目录结构

```
tooling/
├── api/
│   └── __init__.py        ✅ 2 个 Protocol 接口定义
├── configs/
│   ├── backend.yaml       ✅ 后端配置
│   └── gateway.yaml       ✅ 网关配置
└── scripts/
    ├── gen_readme.py          ✅ README 自动生成
    ├── gen_ts_types.py        ✅ TS 类型自动生成
    ├── realign_agent_docs.py  ✅ AGENT.md 对齐
    └── add_agent_crossrefs.pl ✅ 批量添加交叉引用（Perl）
```

### 已实现

| 接口 | 方法 | 说明 |
|------|------|------|
| `ConfigAPI` | `get(key)` · `set(key, value)` · `load(profile)` | 配置管理 |
| `ScriptAPI` | `run(name, args)` · `list()` · `result(run_id)` | 脚本执行 |

### 工具脚本

##### `check_no_broadcast.py` — 低熵广播静态检测（spec 04 §16 / 11 §7 铁律守卫）

```bash
python3 tooling/scripts/check_no_broadcast.py --strict
```

**功能**：
- 4 类违规模式 AST 检测（全 `graph.nodes` 遍历 / 全 capabilities 遍历 / 全 message 推送 / 全 heartbeat 广播）
- 合法豁免（`active_subgraph` / `router.route` / 测试 fixture）
- `--strict` 模式：违规即非零退出（CI 必跑）
- 默认模式：警告不 fail

**CI 集成**：P3.3 阶段 `make broadcast-check` / `.github/workflows/ci.yml` lint job 必跑

##### `gen_readme.py` — README 自动生成

```bash
python3 tooling/scripts/gen_readme.py
```

**功能**：
- 遍历项目目录树
- 统计：顶层域数 · 总目录 · 总文件 · AGENT.md 数 · Python 文件数 · Markdown 文件数 · API 接口数 · protocol 契约类型数
- 生成目录树块
- 生成统计表

### P3.3 CI/CD 流水线（spec 09 §开发流程 + 11 §7 低熵铁律自动化）

> **三作业并行**（PR/Push 到 `main`/`prd` 自动触发）：lint + typecheck + test。详见 `.github/workflows/ci.yml`。

#### 作业 1 — `lint`（ruff + 低熵铁律）
- `ruff check . --output-format=github`：baseline 模式 `continue-on-error` 汇报不 fail（142 既有错误待 P3.4 治理）
- `python tooling/scripts/check_no_broadcast.py --strict`：违规即红 CI（spec 04 §16 / 11 §7 守卫）
- 安装：`pip install --upgrade pip ruff`

#### 作业 2 — `typecheck`（mypy strict）
- 路径：`protocol aegisos_agents backend --ignore-missing-imports`（与 Makefile `typecheck` 目标对齐）
- 安装：`pip install -e ".[dev]"`

#### 作业 3 — `test`（pytest 矩阵）
- Python 3.12 / 3.13 矩阵（`fail-fast: false`）
- 环境变量：`AEGIS_USE_MOCK=true` 零外部依赖

#### CI 优化
- `concurrency.cancel-in-progress: true` PR 多 commit push 节流
- `actions/cache@v4` 按 `pyproject.toml` hash 缓存 pip
- `permissions: contents: read` 默认最小权限
- `actions/upload-artifact@v4` 失败时上传 pytest logs（保留 7 天）

#### Makefile 目标映射

| 目标 | 等价 CI 步骤 | 用途 |
|------|------------|------|
| `make lint` | `ruff check .` | 本地 lint（baseline 报 142 错不 fail） |
| `make broadcast-check` | `check_no_broadcast.py --strict` | 本地低熵铁律（违规即 fail） |
| `make typecheck` | `mypy protocol aegisos_agents backend` | 本地类型检查 |
| `make test` | `pytest` | 本地测试（435 passed） |
| `make check` | `lint + broadcast-check + test` | **一键复现 CI**（推荐 PR 前跑） |
| `make ci` | 提示信息 | 指向 `.github/workflows/ci.yml` |
| `make format` | `ruff format + ruff check --fix` | 本地自动修复（仅格式化 + 简单 fix） |

#### 本地复现命令
```bash
# 提交前：跑一遍 make check = 模拟完整 CI
make check

# 仅跑低熵铁律（CI 必 fail 项）
make broadcast-check

# 仅看 ruff baseline 现状
ruff check . 2>&1 | Measure-Object -Line  # 144 行 ≈ 142 错误
```

#### P3.4 待办（不在 P3.3 commit 范围）
- ruff baseline 142 错误分类治理：
  - 74 × E402（module import 顺序）
  - 14 × E731（lambda → def）
  - 11 × F821（undefined name）
  - 9 × B008（FastAPI `Depends` in default）
  - 9 × B007（loop control variable not used）
  - 散点：UP/RET/SIM/C4/StrEnum 等
- `pyproject.toml` `extend-exclude` 已排除：`.claude` `.github` `agents` `api` `docs` `frontend` Makefile
- 治理完成后改 CI：`continue-on-error: true` 去掉，ruff 严格 fail

##### `gen_ts_types.py` — TypeScript 类型自动生成

```bash
python3 tooling/scripts/gen_ts_types.py
# 或
npm run gen:types
```

**功能**：
- 读取 `protocol/*.py` 的 `@dataclass` 类
- 将 Python 类型映射为 TypeScript 类型（`str → string`, `int → number`, `list → array`, `dict → Record`）
- 将 `Enum` 映射为 TS 联合类型
- 输出到 `frontend/src/protocol/types.ts`（36 个类型）

##### `realign_agent_docs.py` — AGENT.md 对齐

```bash
python3 tooling/scripts/realign_agent_docs.py
```

**功能**：
- 扫描全仓库 `AGENT.md` 文件
- 检查交叉引用是否与实际目录结构一致
- 自动修正引用路径

##### `add_agent_crossrefs.pl` — 批量添加交叉引用

```bash
perl tooling/scripts/add_agent_crossrefs.pl
```

**功能**：Perl 脚本，批量在各模块 AGENT.md 中添加「交叉引用（去哪里找）」段。

### 配置文件

#### `backend.yaml`

```yaml
backend:
  cors:
    origins:
      - http://localhost:5173
      - http://127.0.0.1:5173
```

#### `gateway.yaml`

网关路由配置。

### 当前状态

- ✅ `check_no_broadcast.py` — 全广播违规 CI 校验脚本
- ✅ `sandbox.ps1` — 本地沙箱 config/up/down 编排
- 🔲 Docker 镜像和沙箱真实启动验证
