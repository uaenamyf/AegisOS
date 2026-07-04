#!/usr/bin/env python3
# @aegis-gen
# date: 2026-07-03
# dev: myf
# change: 新建 realign_agent_docs.py，把模块 AGENT.md 中旧 developer/*.md 指南引用重定向到 developer/specs/ SSOT
"""将模块 AGENT.md 中旧的 `developer/*.md` 指南引用重定向到 `developer/specs/` SSOT。

背景：仓库根目录下原有的 20 份 `developer/*.md` 指南已被删除，
取而代之的是编号化的 `developer/specs/`（00-13）规范文档。
本脚本扫描所有模块级 `AGENT.md`（不含仓库根 AGENT.md），
将其中遗留的 `developer/<OLD>.md` 引用改写为对应的后继规范路径，
避免文档指向已删除的文件。

Run:  python3 tooling/scripts/realign_agent_docs.py
Scope: 所有 `**/AGENT.md`，但不包含仓库根 `AGENT.md`（后者手动维护）。
"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根目录（tooling/scripts/ 往上两级）
ROOT = Path(__file__).resolve().parent.parent.parent

# 旧指南路径 -> 后继规范路径（均以 AGENT.md 中出现的相对路径形式表示）
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
    # 说明：developer/CHANGELOG.md 仍在使用，故有意不映射。
}

# 仓库根 AGENT.md 路径，用于在扫描时排除
ROOT_AGENT_MD = ROOT / "AGENT.md"


# 需在遍历时跳过的目录名片段（避免进入无关或体积庞大的目录）
_SKIP_DIR_HINTS = (".git", ".venv", ".claude", "__pycache__", "node_modules")


def find_module_agent_mds() -> list[Path]:
    """递归查找所有模块级 AGENT.md 文件。

    遍历项目根目录，跳过 `.git` / `.venv` / `.claude` / `__pycache__` /
    `node_modules` 等目录，并排除仓库根 `AGENT.md`（后者由人工维护）。

    Returns:
        按路径排序后的 `Path` 列表，每个元素为一个模块级 AGENT.md。
    """
    out: list[Path] = []
    for dp, _, files in os.walk(ROOT):
        # 跳过版本控制、虚拟环境、缓存等无关目录
        if any(hint in dp for hint in _SKIP_DIR_HINTS):
            continue
        for f in files:
            if f == "AGENT.md":
                p = Path(dp) / f
                # 排除仓库根 AGENT.md（该文件由人工维护，不在脚本作用域内）
                if p.resolve() == ROOT_AGENT_MD.resolve():
                    continue
                out.append(p)
    return sorted(out)


def realign(path: Path) -> tuple[bool, dict[str, int]]:
    """对单个 AGENT.md 文件执行引用重写。

    遍历 `MAPPING`，将文件中出现的每个旧路径替换为后继规范路径，
    并记录每个旧路径被替换的次数。若文件内容发生变化则写回磁盘。

    Args:
        path: 目标 AGENT.md 文件路径。

    Returns:
        元组 `(changed, counts)`：
        - changed: 文件是否被修改（True 表示已写回）。
        - counts: 旧路径到替换次数的映射；仅包含实际被替换的旧路径。
    """
    src = path.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    new = src
    for old, spec in MAPPING.items():
        n = new.count(old)  # 统计该旧路径在当前内容中的出现次数
        if n:
            counts[old] = n
            new = new.replace(old, spec)  # 全量替换为新规范路径
    if new != src:
        path.write_text(new, encoding="utf-8")  # 内容有变化才写回，避免无谓 IO
        return True, counts
    return False, counts


def main() -> None:
    """脚本入口：扫描并重写所有模块级 AGENT.md 引用，最后输出统计摘要。

    会打印：每个被修改文件的相对路径与替换明细、扫描文件总数、
    被修改文件数、替换总数，以及按旧路径分组的替换明细表。
    """
    files = find_module_agent_mds()
    changed = 0  # 被修改的文件计数
    total_replacements = 0  # 替换引用总数
    per_old: dict[str, int] = {}  # 旧路径 -> 累计替换次数
    for p in files:
        did, counts = realign(p)
        if did:
            changed += 1
            for old, n in counts.items():
                per_old[old] = per_old.get(old, 0) + n  # 累加该旧路径的替换次数
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
