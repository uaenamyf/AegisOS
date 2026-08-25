# date: 2026-08-25
# dev: overwhelmingly
"""低熵广播检测脚本（check_no_broadcast）测试。

覆盖：
- 干净仓库：0 违规
- 含广播反模式：被检测出
- 合法豁免（json.dumps / active_subgraph）：不被误报
- --strict 退出码
- AST 语法错误文件跳过
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tooling" / "scripts" / "check_no_broadcast.py"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """执行 check_no_broadcast 脚本并返回结果。

    Windows 子进程默认 GBK，stdout/stderr 用 utf-8 + errors='replace' 避免解码崩溃。
    """
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_clean_repo_has_no_violations() -> None:
    """业务域默认扫描应返回 0 违规。"""
    result = _run([], ROOT)
    assert result.returncode == 0
    assert "No broadcast violations" in result.stdout


def test_strict_mode_passes_on_clean_repo() -> None:
    """严格模式在干净仓库应通过。"""
    result = _run(["--strict"], ROOT)
    assert result.returncode == 0
    assert "No broadcast violations" in result.stdout


def test_explicit_broadcast_call_is_detected() -> None:
    """显式 bus.broadcast() 调用应被识别为违规。"""
    with tempfile.TemporaryDirectory() as tmp:
        bad_dir = Path(tmp) / "violating_module"
        bad_dir.mkdir()
        (bad_dir / "bad.py").write_text(
            textwrap.dedent(
                """\
                def emit(bus, event):
                    bus.broadcast(event)
                """
            ),
            encoding="utf-8",
        )
        result = _run(["--path", str(bad_dir)], ROOT)
        assert result.returncode == 0  # 非 strict
        # 跨盘符（tempfile 在 C: ROOT 在 D:）会回退为绝对路径，断言文件名即可
        assert "bad.py" in result.stdout
        assert "broadcast" in result.stdout.lower()


def test_loop_over_nodes_then_dispatch_is_detected() -> None:
    """遍历 nodes.values() 后调 dispatch 应被识别为违规。"""
    with tempfile.TemporaryDirectory() as tmp:
        bad_dir = Path(tmp) / "violating_loop"
        bad_dir.mkdir()
        (bad_dir / "loop.py").write_text(
            textwrap.dedent(
                """\
                def fanout(graph, msg):
                    for n in graph.nodes.values():
                        dispatch(n, msg)
                """
            ),
            encoding="utf-8",
        )
        result = _run(["--path", str(bad_dir)], ROOT)
        assert "loop.py" in result.stdout


def test_json_dumps_traversal_is_exempt() -> None:
    """nodes.values() + json.dumps 同行应被豁免（合法：序列化给 LLM）。"""
    with tempfile.TemporaryDirectory() as tmp:
        good_dir = Path(tmp) / "legit_serial"
        good_dir.mkdir()
        (good_dir / "good.py").write_text(
            textwrap.dedent(
                """\
                import json
                def to_prompt(graph):
                    return json.dumps([n.node_id for n in graph.nodes.values()])
                """
            ),
            encoding="utf-8",
        )
        result = _run(["--path", str(good_dir)], ROOT)
        assert "No broadcast violations" in result.stdout


def test_active_subgraph_is_exempt() -> None:
    """active_subgraph(...) 调用应被豁免（合法：子图构造）。"""
    with tempfile.TemporaryDirectory() as tmp:
        good_dir = Path(tmp) / "legit_subgraph"
        good_dir.mkdir()
        (good_dir / "good.py").write_text(
            textwrap.dedent(
                """\
                from aegisos_agents.planning.engine.topology.topology import active_subgraph
                def filter_active(graph, cap):
                    return active_subgraph(graph, cap)
                """
            ),
            encoding="utf-8",
        )
        result = _run(["--path", str(good_dir)], ROOT)
        assert "No broadcast violations" in result.stdout


def test_strict_mode_returns_nonzero_on_violation() -> None:
    """--strict 模式发现违规应返回非零退出码。"""
    with tempfile.TemporaryDirectory() as tmp:
        bad_dir = Path(tmp) / "violating_strict"
        bad_dir.mkdir()
        (bad_dir / "bad.py").write_text(
            textwrap.dedent(
                """\
                def emit(bus, event):
                    bus.send_all(event)
                """
            ),
            encoding="utf-8",
        )
        result = _run(["--path", str(bad_dir), "--strict"], ROOT)
        assert result.returncode == 1
        assert "[FAIL]" in result.stdout


def test_syntax_error_file_is_skipped() -> None:
    """语法错误文件不应导致脚本崩溃，应仅警告。"""
    with tempfile.TemporaryDirectory() as tmp:
        bad_dir = Path(tmp) / "syntax_err"
        bad_dir.mkdir()
        (bad_dir / "broken.py").write_text("def f(:\n    pass\n", encoding="utf-8")
        result = _run(["--path", str(bad_dir)], ROOT)
        assert result.returncode == 0  # 不应崩溃
        # warn 应在 stderr，但脚本返回 0（无 AST 校验违规）
        assert "No broadcast violations" in result.stdout


def test_nonexistent_path_returns_error_code_2() -> None:
    """不存在的路径应返回退出码 2。"""
    result = _run(["--path", "/nonexistent/path/xxx"], ROOT)
    assert result.returncode == 2
    assert "not found" in result.stderr.lower()


def test_comment_line_is_ignored() -> None:
    """纯注释行（提到 bus.broadcast 字符串）不应被误报。"""
    with tempfile.TemporaryDirectory() as tmp:
        good_dir = Path(tmp) / "only_comment"
        good_dir.mkdir()
        (good_dir / "good.py").write_text(
            "# NOTE: do NOT call bus.broadcast()\n", encoding="utf-8"
        )
        result = _run(["--path", str(good_dir)], ROOT)
        assert "No broadcast violations" in result.stdout


def test_scan_excludes_tests_directory() -> None:
    """扫描应默认排除 tests/ 目录（测试可临时遍历但生产不可）。"""
    with tempfile.TemporaryDirectory() as tmp:
        fake_repo = Path(tmp) / "fake_repo"
        prod = fake_repo / "aegisos_agents" / "agents"
        tests = fake_repo / "tests"
        prod.mkdir(parents=True)
        tests.mkdir(parents=True)

        # 生产域含违规：应被检测
        (prod / "bad.py").write_text(
            "def f(bus, e):\n    bus.broadcast(e)\n", encoding="utf-8"
        )
        # 测试域含违规：应被豁免
        (tests / "test_bad.py").write_text(
            "def f(bus, e):\n    bus.broadcast(e)\n", encoding="utf-8"
        )

        result = _run(["--path", str(fake_repo)], ROOT)
        assert "bad.py" in result.stdout
        assert "test_bad.py" not in result.stdout
