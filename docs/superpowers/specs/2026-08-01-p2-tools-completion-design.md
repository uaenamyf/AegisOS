# P2 工具层补全 — 设计文档

> 日期：2026-08-03 · 状态：设计完成 · 关联：`developer/plan.md` §3 P2

## 1. 目标

补全 `aegisos_agents/tools/` 下 2 个空模块：
- `prompts/` — Prompt 模板集中注册、版本化、变量渲染
- `runtime/` — Agent 生命周期状态机、心跳、挂起/恢复

## 2. 模块设计

### 2.1 prompts/registry.py — PromptRegistry

模板仓库：集中注册所有 Agent 的 SYSTEM_PROMPT，支持版本追踪、角色筛选、版本回滚。

```
PromptTemplate = {name, version, role, content, variables[], created_at}
register(name, content, role, variables) -> int  # 返回版本号
get(name, version=None) -> PromptTemplate
list_all() -> list[PromptTemplate]
list_by_role(role) -> list[PromptTemplate]
rollback(name, version) -> PromptTemplate
```

预置 11 个 Agent 模板（recon / vuln_correlator / exploit_planner / lateral_move / detector / triage / threat_hunt / ir_planner / forensics / critic_red / critic_blue / reviewer）。

### 2.2 prompts/renderer.py — PromptRenderer

模板渲染：`{{ var_name }}` 替换 + 变量校验。

```
render(template_content, vars) -> str
validate(template_content, vars) -> list[str]  # 返回缺失变量列表
```

### 2.3 runtime/lifecycle.py — AgentLifecycle

状态机：`Initialize → Running ⇄ Suspended → Completed/Failed`。

```
start/suspend/resume/complete/fail/heartbeat/check_timeout/status
```

复用 `protocol/heartbeat.py` Heartbeat 类型。

### 2.4 runtime/supervisor.py — RuntimeSupervisor

多 Agent 托管：spawn / suspend / resume / kill / list_active / list_suspended / stats。

## 3. 文件清单

新增 6 个 .py + 2 个 test + 3 个 doc 修改。全部纯算法，不调 LLM。
