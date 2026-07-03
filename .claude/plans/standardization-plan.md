# AegisOS 规范整体改造计划

## 背景与核心问题
根 `AGENT.md` 与 `developer/specs/README.md` 声明 `developer/specs/`（00–13）为唯一真相源（SSOT），"取代" `developer/` 根下约 20 个旧指南。但实测：
- **78 个模块 AGENT.md 中 77 个仍引用旧文档**（346 处），直接违背 SSOT —— 这是核心矛盾。
- `tooling/scripts/gen_readme.py` → `README.md` 的「关键文档/通信协议/开发流程」段仍指向旧文档。
- `developer/AGENT.md` 引用了不存在的 `补充.md` / `开发.md`。
- `.DS_Store` 与 `data/aegisos.db` 被 git 跟踪；根 `.gitignore` 仅含 `.claude/`。
- frontend 存在重复/分叉：`vite.config.{ts,js}`、`playwright.config.{ts,js}` 重复；`frontend-types.ts`（手写、已陈旧、**无人引用**、`ViewName` 缺 `'chat'`）与 `types.ts`（生成、正确）分叉；`gen_ts_types.py` 把前端类型硬编码进"协议生成器"（职责越界）。
- `tests/` 仅有 `AGENT.md`，无实际测试（属 roadmap P6 阶段，本次不补）。
- 跨域 import 经检查**无违规**，代码层架构边界良好 ✓。

## 已确认决策
- 旧文档：**直接删除**（20 个）。
- 范围：**文档/规范对齐 + 代码结构重构**。

## 执行步骤（分域、增量、保持行为可测，遵循 `11_AI_CODING_SPEC` §2）

### 阶段 A — 仓库卫生（低风险）
1. 扩充根 `.gitignore`：补 `.DS_Store`、`*.db`、`__pycache__/`、`*.pyc`、`.venv/`、`logs/`、`*.egg-info`、`.ruff_cache`、`.mypy_cache`、`.pytest_cache`、`frontend/node_modules`、`frontend/dist`。保留 `frontend/.gitignore`（已覆盖前端局部）。
2. `git rm --cached .DS_Store data/aegisos.db`（停止跟踪；本地保留 `aegisos.db` 供运行）。

### 阶段 B — 删除旧文档 + 根规范更新（developer 域）
3. 删除 20 个旧指南：`AGENT_GUIDE / API_SPEC / ARCHITECTURE / BACKEND_GUIDE / CODING_RULES / DEPLOY_GUIDE / DESIGN / DEVELOPER_GUIDE / DEVELOPMENT_PLAN / DIRECTORY_GUIDE / EVENT_SPEC / FRONTEND_GUIDE / MEMORY_GUIDE / MESSAGE_PROTOCOL / PROJECT_BOOTSTRAP / PROMPT_GUIDE / PYTHON_STYLE / ROUTER_GUIDE / TEST_GUIDE / TOOL_SPEC`。保留 `developer/AGENT.md`、`developer/CHANGELOG.md`、`developer/roadmap/`、`developer/specs/`。
4. 更新根 `AGENT.md`：将"旧文档保留作历史参考"改为"旧版散落文档已删除，统一以 `developer/specs/` 为准"。
5. 更新 `developer/specs/README.md`：同步"取代/历史参考"表述为"已删除"。
6. 修复 `developer/AGENT.md`：删除 `补充.md`/`开发.md` 等无效引用，读取目录/下辖子模块改指 `specs/`。

### 阶段 C — 全量 AGENT.md 引用对齐（跨域维护，用户授权）
7. 新增 `tooling/scripts/realign_agent_docs.py`（带 `@aegis-gen` 头）：扫描所有 `AGENT.md`，按映射把旧文档引用替换为 `specs/`：
   - `ARCHITECTURE.md` → `specs/01_ARCHITECTURE_SPEC.md`
   - `DIRECTORY_GUIDE.md` → `specs/02_DIRECTORY_SPEC.md`
   - `MESSAGE_PROTOCOL.md` → `specs/04_PROTOCOL_SPEC.md`
   - `API_SPEC.md` → `specs/05_API_SPEC.md`
   - `EVENT_SPEC.md` → `specs/07_EVENT_SPEC.md`
   - `CODING_RULES.md` → `specs/11_AI_CODING_SPEC.md`
   - `PYTHON_STYLE.md` → `specs/12_TECH_STACK_SPEC.md`
   - `ROUTER_GUIDE.md` → `specs/04_PROTOCOL_SPEC.md`（§16 路由）
   - `BACKEND_GUIDE.md` → `specs/05_API_SPEC.md` + `specs/10_INTERFACE_BOUNDARY_SPEC.md`
   - `FRONTEND_GUIDE.md` → `specs/plans/13_FRONTEND_BACKEND_PLAN.md`
   - 其余 `*_GUIDE` → 对应 `specs/`；`CHANGELOG.md` 引用保持不变。
   - 头注「再阅读 `developer/ARCHITECTURE.md` 相关章节」→ `specs/01_ARCHITECTURE_SPEC.md`。
   运行后抽样人工核验（`protocol/`、`backend/`、`agents/action/coder/`、`agents/planning/engine/router/` 等）。

### 阶段 D — README 生成器修正与重生成（tooling 域）
8. 修正 `tooling/scripts/gen_readme.py`：
   - 「关键文档」段改指 `specs/`（01/04/02/05/11）+ `specs/README.md`。
   - 「通信协议」段 `MESSAGE_PROTOCOL.md` → `specs/04_PROTOCOL_SPEC.md`。
   - 「开发流程」段"读取 developer/ 规范"→"读取 `developer/specs/`（00_PROJECT_SPEC 等）+ roadmap/"。
   - 追加 `@aegis-gen` 头。
9. 运行 `python3 tooling/scripts/gen_readme.py` 重生成 `README.md`。

### 阶段 E — frontend 代码结构重构（frontend 域，tsc + build 验证）
10. 删除重复编译配置：`frontend/vite.config.js`、`frontend/playwright.config.js`（保留 `.ts`；技术栈为 TS）。
11. 删除死文件 `frontend/src/protocol/frontend-types.ts`（无人引用且已陈旧）。
12. 重构 `tooling/scripts/gen_ts_types.py`：移除硬编码"Frontend-specific types"块 —— 协议生成器只产出 `protocol` 契约类型。把这些前端本地类型改为手维护：重建 `frontend/src/protocol/frontend-types.ts`（正确版：`ViewName` 含 `'chat'`，统一用 `Record<string, unknown>`）。
13. 新增 `frontend/src/protocol/index.ts` 桶导出两者；更新受影响导入（约 10 处：`App.tsx`、`controllers/{interaction,routes}.ts`、`mappers/{apimappers/client,store}.ts`、`services/{api/sessions,realtime/sse,realtime/ws,session/index}.ts`、`views/layout/Sidebar.tsx`）：前端本地类型改从 `@/protocol/frontend-types` 引入，`protocol` 契约类型仍从 `@/protocol/types`。
14. 验证：`cd frontend && npx tsc -b`（无类型错误）`&& npm run build`（构建通过）。

### 阶段 F — 收尾
15. 更新 `developer/CHANGELOG.md`：记录本次"规范整体改造"。
16. 质量门禁：Python 侧 `ruff format && ruff check --fix && mypy protocol agents backend`；TS 侧 `tsc -b && vite build`。

## 不在本次范围
- `tests/` 补齐（roadmap P6）。
- `agents/perception|planning|memory|tools` 等空骨架的实现（roadmap 后续阶段）。
- `.claude/skills/` 为本地 gitignored 工具，不并入 checked-in specs；其方法论（计划→审查→收尾）已用于本任务执行。

## 风险与缓解
- frontend 类型重构触及 ~10 文件 → 以 `tsc -b` + `vite build` 为验收门禁，漏改即编译报错可定位。
- 删除旧文档不可逆 → 已确认；内容已在 `specs/` 覆盖。
- AGENT.md 批量替换 → 脚本替换 + 抽样人工核验，避免误伤正文。

## 变更清单（预计）
- 删除：20 旧指南 + `vite.config.js` + `playwright.config.js` + 旧 `frontend-types.ts` + 取消跟踪 `.DS_Store`/`aegisos.db`。
- 新增：`tooling/scripts/realign_agent_docs.py`、新 `frontend/src/protocol/frontend-types.ts`、`frontend/src/protocol/index.ts`。
- 修改：根 `AGENT.md`、`developer/AGENT.md`、`developer/specs/README.md`、`tooling/scripts/gen_readme.py`、`tooling/scripts/gen_ts_types.py`、`.gitignore`、77 个模块 `AGENT.md`、重生成 `README.md`、`developer/CHANGELOG.md`、~10 个 frontend 导入文件。
