#!/usr/bin/env python3
# @aegis-gen
# date: 2026-07-03
# dev: Claude Code (glm-5.2)
# change: 新建 realign_agent_docs.py，把模块 AGENT.md 中旧 developer/*.md 指南引用重定向到 developer/specs/ SSOT
"""Repoint old `developer/*.md` guide references in module AGENT.md files to
the `developer/specs/` SSOT.

The 20 root-level `developer/*.md` guides were deleted in favor of the numbered
`developer/specs/` specs (00-13). This script rewrites every remaining
`developer/<OLD>.md` reference inside module `AGENT.md` files to its successor
spec path, so the docs stop pointing at deleted files.

Run:  python3 tooling/scripts/realign_agent_docs.py
Scope: all `**/AGENT.md` EXCEPT the repo-root `AGENT.md` (handled manually).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# old guide  ->  successor spec (relative paths as they appear in AGENT.md)
MAPPING: dict[str, str] = {
    "developer/AGENT_GUIDE.md": "developer/specs/08_AGENT_SPEC.md",
    "developer/API_SPEC.md": "developer/specs/05_API_SPEC.md",
    "developer/ARCHITECTURE.md": "developer/specs/01_ARCHITECTURE_SPEC.md",
    "developer/BACKEND_GUIDE.md": "developer/specs/10_INTERFACE_BOUNDARY_SPEC.md",
    "developer/CODING_RULES.md": "developer/specs/11_AI_CODING_SPEC.md",
    "developer/DEPLOY_GUIDE.md": "developer/specs/09_DEVELOPMENT_SPEC.md",
    "developer/DESIGN.md": "developer/specs/01_ARCHITECTURE_SPEC.md",
    "developer/DEVELOPER_GUIDE.md": "developer/specs/09_DEVELOPMENT_SPEC.md",
    "developer/DEVELOPMENT_PLAN.md": "developer/specs/09_DEVELOPMENT_SPEC.md",
    "developer/DIRECTORY_GUIDE.md": "developer/specs/02_DIRECTORY_SPEC.md",
    "developer/EVENT_SPEC.md": "developer/specs/07_EVENT_SPEC.md",
    "developer/FRONTEND_GUIDE.md": "developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md",
    "developer/MEMORY_GUIDE.md": "developer/specs/08_AGENT_SPEC.md",
    "developer/MESSAGE_PROTOCOL.md": "developer/specs/04_PROTOCOL_SPEC.md",
    "developer/PROJECT_BOOTSTRAP.md": "developer/specs/00_PROJECT_SPEC.md",
    "developer/PROMPT_GUIDE.md": "developer/specs/08_AGENT_SPEC.md",
    "developer/PYTHON_STYLE.md": "developer/specs/12_TECH_STACK_SPEC.md",
    "developer/ROUTER_GUIDE.md": "developer/specs/04_PROTOCOL_SPEC.md",
    "developer/TEST_GUIDE.md": "developer/specs/09_DEVELOPMENT_SPEC.md",
    "developer/TOOL_SPEC.md": "developer/specs/08_AGENT_SPEC.md",
    # NOTE: developer/CHANGELOG.md is intentionally NOT mapped (still active).
}

ROOT_AGENT_MD = ROOT / "AGENT.md"


def find_module_agent_mds() -> list[Path]:
    out: list[Path] = []
    for dp, _, files in os.walk(ROOT):
        if ".git" in dp or ".venv" in dp or ".claude" in dp or "__pycache__" in dp:
            continue
        if "node_modules" in dp:
            continue
        for f in files:
            if f == "AGENT.md":
                p = Path(dp) / f
                if p.resolve() == ROOT_AGENT_MD.resolve():
                    continue  # root AGENT.md handled manually
                out.append(p)
    return sorted(out)


def realign(path: Path) -> tuple[bool, dict[str, int]]:
    src = path.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    new = src
    for old, spec in MAPPING.items():
        n = new.count(old)
        if n:
            counts[old] = n
            new = new.replace(old, spec)
    if new != src:
        path.write_text(new, encoding="utf-8")
        return True, counts
    return False, counts


def main() -> None:
    files = find_module_agent_mds()
    changed = 0
    total_replacements = 0
    per_old: dict[str, int] = {}
    for p in files:
        did, counts = realign(p)
        if did:
            changed += 1
            for old, n in counts.items():
                per_old[old] = per_old.get(old, 0) + n
                total_replacements += n
            print(f"  updated {p.relative_to(ROOT)}  {counts}")
    print()
    print(f"Scanned {len(files)} module AGENT.md files (excluded root AGENT.md).")
    print(f"Changed {changed} files, {total_replacements} reference replacements.")
    if per_old:
        print("Per old-doc:")
        for old in sorted(per_old):
            print(f"  {old:42s} -> {MAPPING[old]:48s} x{per_old[old]}")


if __name__ == "__main__":
    main()
