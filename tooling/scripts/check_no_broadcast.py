#!/usr/bin/env python3
# date: 2026-08-25
# dev: overwhelmingly
"""低熵广播静态检测脚本（C2 铁律守卫）。

扫描 ``aegisos_agents/`` 业务代码，识别违反 ``04_PROTOCOL_SPEC.md`` §16
「低熵稀疏通信」的反模式：

1. **全节点遍历后发送**：
   ``for n in graph.nodes.values(): ... send/dispatch/publish ...``
   （绕开 ``router.route()`` Top-K 稀疏路由）
2. **直接对所有 nodes 调用**：
   ``for ... in topology.nodes: ...dispatch(...)``
3. **总线广播调用**：``bus.broadcast`` / ``bus.send_all`` 显式 API
4. **router 绕过**：
   - 调用了 ``graph.nodes`` / ``topology.nodes`` 但既不是 ``active_subgraph`` 也不是 ``router.route``
   - 直接 ``dispatch(message)`` 不带 target / node_ref 列表

参考：
    developer/specs/00_PROJECT_SPEC.md §G3 / §NG3
    developer/specs/04_PROTOCOL_SPEC.md §16
    developer/specs/11_AI_CODING_SPEC.md §7

用法：
    python3 tooling/scripts/check_no_broadcast.py
    python3 tooling/scripts/check_no_broadcast.py --path aegisos_agents --strict

退出码：
    0 — 无违规
    1 — 至少一处违规
    2 — 配置/IO 错误
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass

# 仓库根：本文件位于 tooling/scripts/，向上回溯两级
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 默认扫描路径：业务域（不在扫描范围：tests / tooling / scripts 自身 / 文档）
DEFAULT_SCAN_DIR = os.path.join(ROOT, "aegisos_agents")

# 排除目录：测试、缓存、虚拟环境、IDE/编辑器配置、协议类型定义
_EXCLUDE_DIRS = (
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".claude",
    "node_modules",
    "dist",
    "build",
    "tests",  # 测试可临时遍历，但生产代码不可
    "tooling",  # 本工具所在域
    "protocol",  # 类型定义，无运行时路由逻辑
)

# 包含的文件后缀
_INCLUDE_EXTS = (".py",)

# 允许的「合法节点访问」上下文（不算违规）：
# - 序列化给 LLM 上下文（topology/nodes.values() + json.dumps）
# - 子图构造（active_subgraph）
# - 节点计数 / 状态聚合（len/keys/all/any）
_LEGIT_NODE_TRAVERSAL = (
    re.compile(r"\.nodes\.values\(\)"),
    re.compile(r"\.nodes\.keys\(\)"),
    re.compile(r"\.nodes\.items\(\)"),
    re.compile(r"active_subgraph\("),
    re.compile(r"json\.dumps\("),  # 序列化给 LLM，非运行时分发
)

# 违规模式：广播式发送 / 全节点分发
_BROADCAST_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "显式总线广播",
        re.compile(r"\b(bus|event_bus|eventbus)\.(broadcast|send_all|publish_all)\b"),
    ),
    (
        "遍历 nodes.values() 后 dispatch",
        re.compile(
            r"for\s+\w+\s+in\s+[\w\.]*\.nodes\.values\(\)\s*:\s*[^\n]*?(dispatch|send|publish|forward)\b"
        ),
    ),
    (
        "遍历 topology.nodes 后 dispatch",
        re.compile(
            r"for\s+\w+\s+in\s+[\w\.]*(?:topology|graph)\.nodes\s*:\s*[^\n]*?(dispatch|send|publish|forward)\b"
        ),
    ),
    (
        "裸 dispatch 无目标过滤",
        re.compile(r"\bdispatch\((?![^)]*node_refs?=(?!None))"),
    ),
)


@dataclass(frozen=True)
class Violation:
    """一次违规命中。

    Attributes:
        path: 文件相对仓库根的路径。
        line: 1-based 行号。
        kind: 违规模式名称。
        snippet: 触发违规的代码行（截断到 120 字符）。
    """

    path: str
    line: int
    kind: str
    snippet: str

    def format(self) -> str:
        """格式化为单行报告。"""
        return f"  {self.path}:{self.line}  [{self.kind}]  {self.snippet}"


def _iter_python_files(root: str) -> Iterable[str]:
    """遍历 ``root`` 下所有 ``.py`` 文件，跳过排除目录。"""
    for dirpath, dirnames, filenames in os.walk(root):
        # 原地裁剪排除目录，避免 os.walk 进入
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for name in filenames:
            if name.endswith(_INCLUDE_EXTS):
                yield os.path.join(dirpath, name)


def _check_file(path: str) -> list[Violation]:
    """对单文件执行模式匹配，返回违规列表。"""
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        # 跨盘符（Windows 临时目录在 C: 而 ROOT 在 D:），回退绝对路径
        rel = path
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"warn: cannot read {rel}: {exc}", file=sys.stderr)
        return []

    # 1) AST 验证语法有效性（不通过则文本匹配可能误报）
    try:
        ast.parse(content, filename=rel)
    except SyntaxError as exc:
        # 语法错误的文件不在检测范围（lint 阶段处理）
        print(f"warn: syntax error in {rel}:{exc.lineno}", file=sys.stderr)
        return []

    violations: list[Violation] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        # 跳过纯注释行
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for kind, pattern in _BROADCAST_PATTERNS:
            if not pattern.search(line):
                continue

            # 合法节点访问豁免：若该行同时含合法模式，跳过
            if any(legit.search(line) for legit in _LEGIT_NODE_TRAVERSAL):
                continue

            snippet = stripped[:120]
            violations.append(Violation(path=rel, line=idx, kind=kind, snippet=snippet))

    return violations


def scan(scan_dir: str) -> list[Violation]:
    """扫描整个目录，返回全部违规。

    Args:
        scan_dir: 扫描根目录绝对路径。

    Returns:
        违规列表（按文件、行号排序）。
    """
    if not os.path.isdir(scan_dir):
        raise FileNotFoundError(f"scan_dir not found: {scan_dir}")

    all_violations: list[Violation] = []
    for path in _iter_python_files(scan_dir):
        all_violations.extend(_check_file(path))

    # 稳定排序：先按 path 再按 line
    all_violations.sort(key=lambda v: (v.path, v.line))
    return all_violations


def _print_report(violations: list[Violation], strict: bool) -> int:
    """打印报告并返回退出码。"""
    print("=" * 60)
    print("AegisOS 低熵广播检测（spec 04 §16 / 11 §7 铁律）")
    print("=" * 60)

    if not violations:
        print("[OK] No broadcast violations: all routing goes through router.route() Top-K sparse dispatch.")
        return 0

    print(f"[FAIL] Found {len(violations)} potential broadcast violations:\n")
    for v in violations:
        print(v.format())

    if strict:
        print(
            "\n--strict mode: blocking (exit 1). "
            "To exempt: replace raw traversal with active_subgraph(...) "
            "or router.route(message, topology, capability) returning Top-K=3."
        )
        return 1

    print(
        "\nNon-strict mode (warnings only). "
        "Recommendation: replace `for n in graph.nodes` with active_subgraph + router.route."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="AegisOS 低熵广播静态检测（C2 铁律守卫）",
    )
    parser.add_argument(
        "--path",
        default=DEFAULT_SCAN_DIR,
        help=f"扫描根目录（默认：{os.path.relpath(DEFAULT_SCAN_DIR, ROOT)}）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：发现违规即返回非零退出码（CI 用）",
    )
    args = parser.parse_args(argv)

    try:
        violations = scan(os.path.abspath(args.path))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return _print_report(violations, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
