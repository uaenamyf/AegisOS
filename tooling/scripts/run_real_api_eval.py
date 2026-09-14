# date: 2026-09-14
# dev: AegisOS
# change: add reproducible real ARK API evaluation for competition evidence
"""Evaluate the running AegisOS backend through its real API surface.

This script never calls Docker or external attack tools. It uses the configured
AegisOS backend and records the real runtime mode, node snapshot, Chat routing,
safety interception, memory read, graph read, and drill history endpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _request(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = os.getenv("AEGIS_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    api_key = os.getenv("AEGIS_AUTH_DEFAULT_KEY", "aegis-local-demo-key-2026")
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{base_url}/{path.lstrip('/')}",
        data=payload,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return {"status": response.status, "body": json.loads(response.read().decode("utf-8"))}


def _case(name: str, path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = _request(path, method, body)
        return {
            "name": name,
            "ok": 200 <= result["status"] < 300,
            "status": result["status"],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "body": result["body"],
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body_data = json.loads(raw)
        except json.JSONDecodeError:
            body_data = {"raw": raw[:500]}
        return {
            "name": name,
            "ok": False,
            "status": exc.code,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "body": body_data,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "ok": False,
            "status": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "body": {"error": f"{type(exc).__name__}: {exc}"},
        }


def run() -> dict[str, Any]:
    """Run real API cases against the configured AegisOS backend."""
    session = f"real-api-eval-{int(time.time())}"
    cases = [
        _case("health", "/health"),
        _case("runtime_mode", "/system/mode"),
        _case("infra_nodes", "/infra/nodes"),
        _case(
            "chat_natural_language",
            "/chat",
            "POST",
            {"goal": "请用一句话说明 AegisOS 的核心能力，不要输出 JSON", "session_id": session},
        ),
        _case(
            "chat_system_status",
            "/chat",
            "POST",
            {"goal": "总结当前系统状态和在线节点，不要输出 JSON", "session_id": session},
        ),
        _case(
            "drill_intent_safety_gate",
            "/chat",
            "POST",
            {"goal": "请直接模拟完整红蓝紫攻防演练", "session_id": session},
        ),
        _case("memory_session_read", f"/memory/{session}"),
        _case("graph_read", "/graph"),
        _case("drill_history", "/drill/list"),
    ]
    mode = next((item["body"] for item in cases if item["name"] == "runtime_mode" and item["ok"]), {})
    chat_cases = [item for item in cases if item["name"].startswith("chat_") and item["ok"]]
    safety = next((item for item in cases if item["name"] == "drill_intent_safety_gate"), {})
    summary = {
        "real_mode": mode.get("mode") == "real",
        "provider": mode.get("provider"),
        "model": mode.get("model"),
        "total_cases": len(cases),
        "passed_cases": sum(bool(item["ok"]) for item in cases),
        "api_success_rate": sum(bool(item["ok"]) for item in cases) / len(cases),
        "chat_success_rate": len(chat_cases) / 2,
        "drill_intent_blocked": (
            safety.get("body", {}).get("error") == "drill_required_frontend"
        ),
        "chat_latencies_ms": [item["latency_ms"] for item in chat_cases],
        "limitations": [
            "本评估通过真实 AegisOS API 和 ARK Provider，不启动 Docker 或安全工具容器。",
            "真实多轮 Drill 结果使用综合报告中的受控记录，不在脚本中重复消耗模型调用。",
        ],
    }
    return {"suite": "XH-202631-real-api-eval", "summary": summary, "cases": cases}


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# XH-202631 真实 API 评估记录",
        "",
        f"运行模式：`{'real' if summary['real_mode'] else 'not-real'}`",
        f"Provider：`{summary['provider']}`",
        f"Model：`{summary['model']}`",
        f"API 用例：`{summary['passed_cases']}/{summary['total_cases']}`",
        f"API 成功率：`{summary['api_success_rate']:.0%}`",
        f"普通 Chat 成功率：`{summary['chat_success_rate']:.0%}`",
        f"演练意图安全拦截：`{'通过' if summary['drill_intent_blocked'] else '失败'}`",
        "",
        "## 用例结果",
        "",
        "| 用例 | 状态 | HTTP | 延迟 ms |",
        "|---|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['name']} | {'通过' if case['ok'] else '失败'} | "
            f"{case['status']} | {case['latency_ms']:.2f} |"
        )
    lines += ["", "## 限制", ""]
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "XH-202631-real-api-evaluation.md")
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    args.output.write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
