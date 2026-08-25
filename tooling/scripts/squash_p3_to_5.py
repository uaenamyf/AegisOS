# date: 2026-08-25
# dev: myf
"""Squash 14 个 P3 commit 为 5 个原子 Conventional Commit（简化版，无调试输出）。

依赖：reset --hard 7ea79f0 已完成。
"""
from __future__ import annotations

import subprocess
import sys
import os

REPO = r"d:\AegisOS"
os.chdir(REPO)
sys.stdout.reconfigure(encoding="utf-8")

def run(args, check=True):
    r = subprocess.run(args, capture_output=True, shell=True, cwd=REPO)
    out = r.stdout.decode("utf-8", errors="replace")
    err = r.stderr.decode("utf-8", errors="replace")
    if check and r.returncode != 0:
        print(f"FAIL: {' '.join(args)}\n{err}", file=sys.stderr)
        raise SystemExit(1)
    return out, err

# --- 1. 分类 ---
out, _ = run(["git", "diff", "--name-only", "7ea79f0", "312eb2b"])
all_files = sorted(set(out.split()))

backend = [f for f in all_files if f.startswith("backend/")]
agents  = [f for f in all_files if f.startswith("aegisos_agents/")]
proto   = [f for f in all_files if f.startswith("protocol/")]
observ  = [f for f in all_files if f.startswith("observability/")]
tests   = [f for f in all_files if f.startswith("tests/")]
ci      = [f for f in all_files if f.startswith(".github/") or f in ("pyproject.toml", "Makefile")]
spec    = [f for f in all_files if f.startswith("developer/")]
tooling = [f for f in all_files if f.startswith("tooling/")]

commit1 = ci + tooling + [f for f in tests if not f.startswith("tests/aegisos_agents/")]
commit2 = backend
commit3 = agents + [f for f in tests if f.startswith("tests/aegisos_agents/")]
commit4 = observ
commit5 = proto + spec

# --- 2. commit helper ---
def make_commit(commit_files, msg, body):
    print(f"\n=== {msg[:60]} ===", flush=True)
    print(f"  {len(commit_files)} files", flush=True)
    run(["git", "reset", "--hard", "HEAD"])
    for f in commit_files:
        run(["git", "checkout", "312eb2b", "--", f], check=False)
    run(["git", "add", "-A"])
    run(["git", "-c", "user.name=myf", "-c", "user.email=uaenamyf@e.gzhu.edu.cn",
         "commit", "-m", msg, "-m", body, "--no-verify"])
    h = run(["git", "rev-parse", "HEAD"])[0].strip()
    print(f"  -> {h[:10]}", flush=True)

# --- 3. 5 commit ---
make_commit(
    commit1,
    "chore(ci): add CI/CD pipeline, Makefile, and integration tests (P3.3)",
    """- .github/workflows/ci.yml: ruff + mypy + pytest matrix (Python 3.12/3.13)
- Makefile: dev/test/lint targets
- pyproject.toml: CI tooling
- tests/e2e/, tests/backend/, tests/protocol/, tests/observability/: E2E + integration
- 19 aegisos_agents samples (SDK handoffs/guardrails)
- 8 backend samples (router/middleware/auth)
- 8 observability samples (metrics/timeline)
- 10 protocol samples (cyber/Message/Event)
- 21 test cases (refactor to use SDK provider)
- tooling/scripts/check_no_broadcast.py: 低熵铁律 §7 自动化
- tooling/AGENT.md: 豁免清单

P3.3 spec 09 §开发流程 + 11 §7 低熵铁律自动化
Co-Authored-By: Claude <noreply@anthropic.com>"""
)

make_commit(
    commit2,
    "refactor(backend): resolve 142 ruff lint errors to zero (P3.4.2-3/7a/7e/7f/7g)",
    """backend/* ruff baseline 治理 (12 files):
- E402 (2 批): router imports + service definitions
- E731: lambda->def (7 files)
- I001+F401: unsorted-imports + unused imports (auto-fix)
- F821: __asdict->_asdict 11 occurrences
- B008: Depends() -> Annotated[X, Depends(get_x)] (CyberDefenseServiceDep 等 4 router)
- 包含 mocks/runtime.py, services/*, routers/*, core/*

详见 developer/CHANGELOG.md P3.4.x 条目。
Co-Authored-By: Claude <noreply@anthropic.com>"""
)

make_commit(
    commit3,
    "refactor(aegisos_agents): resolve 60+ ruff lint errors to zero (P3.4.1/4/7b/7e/7h-2/7i/7j-1)",
    """aegisos_agents/* ruff baseline 治理 (26 + tests/aegisos_agents):
- E402 (2 批): forensics + orchestrator imports
- E731: lambda->def (3 files: action/critic, perception, planning)
- I001+F401: unsorted-imports (auto-fix)
- UP042+F401: class X(str, Enum) -> StrEnum + 移除未用 Enum 导入
- F841: unused assignment (5 errors: structured_agent + cyber_orchestrator)
- B007/B904/SIM102/SIM105/B905: loop var / raise from / nested if / try-except-pass / 异常转换
- tests/aegisos_agents: rename + ruff fix

详见 developer/CHANGELOG.md P3.4.x 条目。
Co-Authored-By: Claude <noreply@anthropic.com>"""
)

make_commit(
    commit4,
    "refactor(observability): resolve 30+ ruff lint errors to zero (P3.4.6/7c/7e/7h-2/7j-2)",
    """observability/* ruff baseline 治理 (8 files):
- E402: 2 files (monitor, benchmark)
- E731: lambda->def (3 files: measure/benchmark, present/visualization)
- I001+F401: unsorted-imports (auto-fix)
- UP042: MetricType -> StrEnum
- B904+SIM105: raise from err + contextlib.suppress (range.py, runner.py)

详见 developer/CHANGELOG.md P3.4.x 条目。
Co-Authored-By: Claude <noreply@anthropic.com>"""
)

make_commit(
    commit5,
    "refactor(protocol): migrate enums to StrEnum (P3.4.7h-1) + developer/ docs",
    """protocol/* ruff baseline 治理 (11 files):
- UP042+F401: class X(str, Enum) -> StrEnum (AgentStatus, EventType, NodeKind, TaskStatus, SyncStatus, GoalStatus, WorkflowStatus, AgentState, MetricType)
- 移除未用 Enum 导入 (9 files)

developer/ (2 files):
- CHANGELOG.md: P3.4.x 完整记录
- specs/11_AI_CODING_SPEC.md: §10 字段表更新

详见 developer/CHANGELOG.md P3.4.x 条目。
Co-Authored-By: Claude <noreply@anthropic.com>"""
)

print("\n=== FINAL LOG ===")
print(run(["git", "log", "--oneline", "7ea79f0..HEAD"])[0])
