# P2 AP4 Ask 范式补全 — 测试报告

> 版本：v1.0 · 日期：2026-08-06 · 分支：`prod/AP4-human-in-the-loop/feat`

---

## 1. 测试概览

| 指标 | 数值 |
|------|------|
| **测试文件总数** | 11（新增 4 + 修改 3 + 前端 3） |
| **AP4 新增/修改测试用例** | Python 18 新增 + 前端 5 新增 |
| **全量测试** | **370 passed**（`AEGIS_USE_MOCK=1 .venv python -m pytest tests/ -q`） |
| **前端测试** | 26 passed（`frontend npx vitest run`）+ `tsc -b` 通过 |
| **Lint** | ruff 新建文件 All checks passed |
| **测试环境** | Windows 11 · Python 3.12 · pytest 9.1.1（`.venv`）· node 24 / vitest |

---

## 2. AP4 新增模块测试

### 2.1 `tests/protocol/test_human.py`（4 用例，新增）

| 测试用例 | 验证场景 |
|----------|----------|
| `test_human_question_fields` | HumanQuestion 字段（question_id/text/options/degraded/timeout） |
| `test_human_answer_fields` | HumanAnswer 字段（question_id/answer/option/by_human/degraded） |
| `test_human_question_roundtrip` | dataclass `asdict` 往返 |
| `test_new_event_types_registered` | `EventType.HumanInputRequired`/`HumanResponse` 枚举值登记 |

### 2.2 `tests/aegisos_agents/perception/test_human_responder.py`（4 用例，新增）

| 测试用例 | 验证场景 |
|----------|----------|
| `test_ask_publishes_events_and_returns_human_answer` | 发布 HumanInputRequired → 阻塞 → submit_answer 解析返回人类应答 |
| `test_ask_timeout_returns_degraded` | 超时返回 `by_human=False, degraded=True` 降级应答 |
| `test_submit_answer_unknown_question_returns_false` | 未知提问 ID 解析幂等返回 False |
| `test_pending_cleaned_after_ask` | ask 结束后 pending 清理（pending_count==0） |

### 2.3 `tests/aegisos_agents/perception/test_ask_mode.py`（4 用例，新增）

| 测试用例 | 验证场景 |
|----------|----------|
| `test_ask_returns_human_answer` | ask() 经 responder 返回人类应答 |
| `test_ask_passes_timeout_and_degraded` | timeout/degraded 透传到 HumanQuestion |
| `test_ask_confirmation_uses_confirm_reject_options` | ask_confirmation 默认 options=["确认","否决"] |
| `test_ask_confirmation_default_degraded_is_reject` | 超时默认"否决"（安全保守） |

### 2.4 三 Agent 接入 Ask（10 用例，修改）

| 测试文件 | 新增用例 | 覆盖 |
|----------|:----:|------|
| `test_ir_planner.py` | 4 | `plan_response_with_ask`：破坏性确认 / 否决降级过滤 / 无破坏不提问 / 超时降级 |
| `test_critic.py` | 3 | `critique_with_ask`：高危触发提问 / 低危不提问 / 超时默认上报 |
| `test_threat_hunt.py` | 3 | `hunt_with_ask`：低置信澄清 / 高置信不提问 / 超时取最高置信假设 |

### 2.5 `tests/backend/test_human_endpoint.py`（2 用例，新增）

| 测试用例 | 验证场景 |
|----------|----------|
| `test_respond_endpoint_unknown_question_returns_false` | `POST /api/v1/human/respond` 未知提问返回 `{"ok": false}` |
| `test_hitl_ask_resolve_roundtrip` | Agent ask → 发布事件 → submit_answer → Agent 恢复 的端到端闭环 |

### 2.6 前端（5 用例，新增）

| 测试文件 | 用例 | 覆盖 |
|----------|:----:|------|
| `human.test.ts` | 2 | respondHuman POST /human/respond + 错误返回 false |
| `sse-ontopic.test.ts` | 1 | SseManager.onTopic 命名事件订阅回调 |
| `ChatView-question.test.tsx` | 2 | 提问卡片渲染 + 点选应答回传并标记已答 |

---

## 3. 既有模块回归（零破坏）

| 测试目录 | 状态 |
|----------|:----:|
| `tests/protocol/` | ✅ 10 passed |
| `tests/aegisos_agents/perception/` | ✅ 68 passed |
| `tests/aegisos_agents/action/` | ✅ 29 passed |
| `tests/aegisos_agents/planning/` | ✅ 通过 |
| `tests/aegisos_agents/memory/` | ✅ 通过 |
| `tests/aegisos_agents/tools/` | ✅ 通过（含既有修复） |
| `tests/backend/` + `tests/e2e/` | ✅ 23 passed |

---

## 4. 顺带修复的既有问题（非 AP4 范围）

| 文件 | 修复 | 影响 |
|------|------|------|
| `aegisos_agents/tools/runtime/lifecycle.py` | `from protocol.scheduler import NodeRef` → `from protocol.message import NodeRef` | 修复错误 import，解封 tools runtime 导入 |
| `tests/aegisos_agents/tools/test_runtime.py` | `test_check_timeout` 断言顺序（start 后先 sleep 再 check） | 修复测试逻辑 bug |
| `pyproject.toml` | pytest `addopts` 加 `--import-mode=importlib` | 解决同名 `test_reflection.py` 收集冲突，`pytest tests/` 可全量 |

> **运行说明**：全量 Python 测试须 `AEGIS_USE_MOCK=1`（存在 `OPENAI_API_KEY` 时 `_create_orchestrator` 默认真实 API 模式会超时）。

---

## 5. 质量门禁

| 门禁 | 命令 | 结果 |
|------|------|:----:|
| Python 全量 | `AEGIS_USE_MOCK=1 .venv/Scripts/python.exe -m pytest tests/ -q` | ✅ 370 passed |
| 前端单测 | `cd frontend && npx vitest run` | ✅ 26 passed |
| 前端类型 | `cd frontend && npx tsc -b` | ✅ |
| Ruff | `.venv/Scripts/python.exe -m ruff check <新增文件>` | ✅ All checks passed |
