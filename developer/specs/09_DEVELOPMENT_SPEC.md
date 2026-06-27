# 09_DEVELOPMENT_SPEC.md — 开发流程规范

> 上游：`00_PROJECT_SPEC.md`。本文件是 Cursor / Claude Code 等 AI 最先看的开发规范。
> **核心流程（铁律）**：所有开发必须遵循 `Specification → Contract → API → Implementation → Test → Document`。
> 在规范（P0）未完成前，任何人/AI 不得编写业务代码。

---

## 1. 开发总流程（Spec First）

```
P0 Specification  （规范：developer/specs/00..11）
   ↓
P1 Contract       （契约：protocol/ 类型可序列化往返）
   ↓
P2 Protocol       （协议：Message 信封 + Event + 动态路由）
   ↓
P3 API            （接口：29 个 api/ Protocol 签名冻结）
   ↓
P4 Skeleton       （骨架：各域空实现 + DI 注入 + 配置 + Makefile）
   ↓
P5 Implementation （实现：Memory→Router→Scheduler→Planner+Agents）
   ↓
P6 Testing        （测试：协议往返 + API 契约 + E2E + 基准，覆盖率≥80%）
   ↓
P7 Deployment     （部署：Docker/K8s/CI、端边云、开箱可部署）
```

单次功能开发的标准链路：
```
Specification → Contract → API → Implementation → Test → Document → Commit
```
> **代码注释头**：凡 AI 生成/修改的代码必须加 `@aegis-gen` 注释头（date/dev/change），详见 `11_AI_CODING_SPEC.md` §10。测试代码同样要求。

---

## 2. 质量门禁（Definition of Done）

提交前必须全绿：
```bash
ruff format && ruff check --fix && mypy && pytest
```
- 覆盖率：整体 ≥ 80%；关键路径（protocol/router/scheduler/memory/eventbus/planner）≥ 90%。
- 公共接口必有测试；bug 修复附回归测试。
- **AI 生成/修改的代码必须加 `@aegis-gen` 注释头**（`date`/`dev`/`change`），见 `11_AI_CODING_SPEC.md` §10；缺失视为未完成。
- 新增/变更 API 同步 `05_API_SPEC.md`；新增/变更事件同步 `07_EVENT_SPEC.md`；变更协议同步 `04_PROTOCOL_SPEC.md`。
- 更新 `developer/CHANGELOG.md`。

---

## 3. Commit 流程

格式：`<type>(<scope>): <subject>`（详见 `00_PROJECT_SPEC.md` §13）。

```
1. 读目标模块 AGENT.md（职责/禁止修改目录）
2. 读 protocol/ 契约 + tooling/configs/ 配置
3. 实现 → 运行质量门禁 → 更新文档与 CHANGELOG
4. git add <仅相关文件> → commit（不提交密钥）
```

- scope = 受影响域（agents/backend/frontend/protocol/infra/observ/...）。
- 破坏性变更：`break!(scope): ...` + major bump + 通知依赖方。
- 不提交密钥/凭据；不在 commit message 写敏感信息。
- 目录结构/api 变动后运行 `python3 tooling/scripts/gen_readme.py` 刷新根 README。

---

## 4. Code Review

- 契约符合性：复用 `protocol/` 类型？走 `Message` 信封？只经 `api/` 跨域？
- 边界符合性：是否越界？读过目标 `AGENT.md`？
- 低熵通信：是否全广播？路由是否链式？
- Import 合规：符合 `03_IMPORT_SPEC.md`？无循环？无跨域内部 import？
- 测试：公共接口有测试？回归测试？覆盖率达标？
- 文档同步：API/Event/Protocol 变更同步规范 + CHANGELOG？
- 安全：密钥泄露？日志脱敏？工具沙箱 + 权限？
- AI 合规：符合 `11_AI_CODING_SPEC.md`？

---

## 5. Documentation（文档）

- 规范：`developer/specs/`（SSOT）。
- 模块边界：各目录 `AGENT.md`。
- 阶段计划：`developer/roadmap/P*/README.md`。
- API/Event/Protocol/Schema 变更同步对应编号规范。
- 根 `README.md` 由 `tooling/scripts/gen_readme.py` 自动生成（勿手改自动段）。
- 文档资产：`docs/{api,architecture,guides,assets}/` + `docs/examples/`。

---

## 6. Test（测试）

| 类型 | 位置 | 内容 |
|------|------|------|
| Unit | `tests/unit/` | 镜像源码结构；单模块逻辑 |
| Integration | `tests/integration/` | 跨模块经 `api/` 集成 |
| E2E | `tests/e2e/` | 端到端：goal→plan→route→schedule→execute→result |
| Fixtures | `tests/fixtures/` | 共享夹具 |
| Benchmarks | `tests/benchmarks/` | 性能基准 |

- 协议往返测试：每个 `protocol/` 类型 `to_dict`↔`from_dict`（或 `model_dump`↔`model_validate`）。
- API 契约测试：mock 实现 `api/` Protocol，验证签名稳定。
- 失败可重试/回滚的走 `Task.retry`/`Task.rollback` 字段。

---

## 7. Benchmark（基准）

- 位置：`tests/benchmarks/` + `observability/measure/benchmark/`（`BenchmarkAPI.run`）。
- 度量：端到端延迟、Token 成本、通信熵、吞吐、资源占用。
- 对齐赛题评分（`observability/measure/evaluation/`）。

---

## 8. Changelog

- 位置：`developer/CHANGELOG.md`。
- 每次提交相关变更即更新；按版本/阶段记录。
- 破坏性变更显式标注 + 影响域 + 迁移指引。
- 每完成一阶段在 `developer/roadmap/README.md` 勾选进度。

---

## 9. 分支模型

| 分支 | 用途 | 命名 |
|------|------|------|
| `main` | 稳定主线 | — |
| `project/<domain>-feat/<name>` | 功能开发 | 如 `project/backend-feat/init` |
| `project/<domain>-fix/<name>` | 缺陷修复 | — |
| `release/<vX.Y>` | 发布准备 | — |
| `hotfix/<vX.Y.Z>` | 紧急修复 | — |

- 功能/修复分支从 `main` 切出；合并前经 Review + 质量门禁。
- 并行开发：前端/后端/Agent 三团队在统一契约下独立推进（见 `10_INTERFACE_BOUNDARY_SPEC.md`）。

---

## 10. Feature / Bug Fix / Release / Hotfix

### Feature
`branch → Specification→Contract→API→Implementation→Test→Document → PR → Review → merge`

### Bug Fix
`branch → 复现测试（回归）→ 修复 → 验证 → PR → Review → merge`

### Release
`main → release/<vX.Y> → 质量门禁全绿 + 基准 + 文档 → tag vX.Y → 部署`

### Hotfix
`main → hotfix/<vX.Y.Z> → 修复+回归测试 → merge main & release → tag vX.Y.Z`

---

## 11. Agent 开发流程（agents/）

```
1. 读 developer/specs/00..11 + roadmap 定位阶段
2. 读目标模块 AGENT.md（职责/读取目录/禁止修改目录）
3. 读 protocol/ 契约（Agent/Task/MemoryPacket/ToolCall/...）+ agents/api 接口
4. 读 tooling/configs/agents/*.yaml 配置
5. 实现：按统一生命周期 + 统一接口（receive→think→tool→reflect→respond）
6. 经 EventBus 发事件（AgentStart/Finish/ToolCall/...）
7. 运行 tests/ → 更新 CHANGELOG → commit
```
- Agent 永不扫描整个项目；按模块边界精准读写。

---

## 12. Backend 开发流程（backend/）

```
1. 读 specs + 目标 AGENT.md + protocol/ + backend/api 接口
2. gateway → controllers → services → mappers 分层实现
3. 对外 /api/v1/... 经 gateway；透传 X-Trace-Id/X-Session-Id/X-Task-Id
4. 跨域只经 agents.api/infrastructure.api/observability.api/data.api
5. 质量门禁 → 测试 → 文档 → commit
```

---

## 13. Frontend 开发流程（frontend/）

```
1. 读 specs + 目标 AGENT.md + backend/api 接口（前端契约来源）
2. controllers → services → mappers → views 分层实现
3. 只调 backend.api（REST/WS/SSE），不直连 agents/infrastructure
4. 实时：WebSocket（双向）+ SSE（单向事件流）
5. 质量门禁（tsc/lint/test）→ 文档 → commit
```

---

## 14. 并行开发保证

- 前端/后端/Agent 三团队（或三个 AI）在统一契约（`protocol/` + `api/`）下独立开发。
- 接口边界由 `10_INTERFACE_BOUNDARY_SPEC.md` 强约束，低冲突集成。
- 契约（`api/` 签名）冻结后，各方并行实现，集成时只对契约。
