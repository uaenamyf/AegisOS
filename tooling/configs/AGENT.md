# Tooling/Configs 配置 — AGENT.md

> 本文件是 `tooling/configs/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `tooling/AGENT.md` 与 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
全项目配置中心：环境覆盖（dev/staging/prod）、各模块配置、Agent/模型/Prompt 配置。是单一配置源，隶属 tooling/ 工程支撑层。

## 配置架构（优先级高 → 低）
1. **环境变量**（`AEGIS_*` / `VITE_*`）— shell 或 CI/CD 注入
2. **`.env`**（`tooling/configs/.env`）— 本地开发，不提交 git
3. **`defaults.yaml`**（`tooling/configs/defaults.yaml`）— 全项目默认值 SSOT
4. **代码默认值**（`settings.py` dataclass 默认值）— 最后回退

### 核心文件
| 文件 | 用途 |
|------|------|
| `settings.py` | Python 统一配置加载器，导出 `settings` 单例 |
| `defaults.yaml` | 全项目默认值 SSOT（backend/frontend/cors/auth/db/log/rate_limit/trace/frontend_env）|
| `.env.example` | 环境变量模板（提交 git），`cp .env.example .env` 后使用 |
| `.env` | 本地环境覆盖（不提交 git）|
| `backend.yaml` | 旧后端配置（已合并入 defaults.yaml，保留向后兼容）|
| `gateway.yaml` | 旧网关配置（已合并入 defaults.yaml，保留向后兼容）|

## 读取目录（允许读）
- developer/
- protocol/

## 禁止修改目录
- 所有业务子系统源码
- frontend/

## 输出
- `tooling/configs/settings.py` — 统一配置加载器（Python 单例 `settings`）
- `tooling/configs/defaults.yaml` — 全项目默认值 SSOT
- `tooling/configs/.env.example` — 环境变量模板（提交 git）
- `frontend/src/config/index.ts` — 前端统一配置入口（`config` 单例）
- `frontend/.env` — 前端 Vite 环境变量
- `tooling/configs/environments/` — 环境覆盖（dev/staging/prod，规划中）
- `tooling/configs/agents/` — Agent 配置（规划中）
- `tooling/configs/models/` — 模型配置（规划中）
- `tooling/configs/prompts/` — Prompt 配置（规划中）

## 依赖
- developer/ 规范

## 接口
- **Python 后端**：`from tooling.configs.settings import settings` → `settings.backend.host` / `settings.cors.origins` / `settings.auth.default_key` / `settings.database.url` 等
- **前端**：`import { config } from "@/config"` → `config.apiBaseUrl` / `config.wsUrl` / `config.apiKey` 等
- **脚本/Makefile**：环境变量 `AEGIS_BACKEND_PORT` / `AEGIS_FRONTEND_PORT` 等

### 禁止
- 后端代码直接 `os.environ` / 硬编码端口/密钥/URL
- 前端代码直接硬编码 `"http://localhost:8000"` / `"aegis-dev-key"`
- 必须经 `settings` 或 `config` 统一读取

## 测试方式
`pytest tests/tooling/configs/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/configs/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`aegisos_agents/tools/prompts/configs/`（版本化管理，变更需经 aegisos_agents/perception/reflection 评估）。

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
