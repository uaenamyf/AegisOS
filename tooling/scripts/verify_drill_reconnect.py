# date: 2026-09-13
# dev: OpenSquilla
"""演练「切走再切回」端到端验证脚本。

对运行中的后端验证三件事（对应报告的前端症状）：
  1. SSE 中途断开后重连，必须**重放**已发生的全部事件（旧 queue.Queue 会丢）；
  2. 订阅者 B 接入时立刻拿到 CoT 轨迹，不再空白显示「等待首个 agent 启动」；
  3. get_drill 返回 current_stage / current_round / elapsed / agent_trace，
     供切页返回时恢复进度条与推理时间线。

用法: python tooling/scripts/verify_drill_reconnect.py [--base http://127.0.0.1:8000]
退出码 0 = 全部通过。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

# API Key 从后端配置读（不硬编码）：优先环境变量，后退 backend.core.auth
if os.environ.get("AEGIS_REPO_ROOT"):
    sys.path.insert(0, os.environ["AEGIS_REPO_ROOT"])
try:
    from backend.core.auth import DEV_API_KEY as API_KEY  # type: ignore
except Exception:  # noqa: BLE001
    API_KEY = os.environ.get("AEGIS_API_KEY", "aegis-dev-key")


def _req(base: str, path: str, *, method: str = "GET", body: dict | None = None, timeout: float = 30.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _parse_events(raw: str) -> list[tuple[str, dict]]:
    """把 SSE 文本解析成 (event_name, data) 列表。"""
    out: list[tuple[str, dict]] = []
    name = ""
    for line in raw.splitlines():
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: ") and name:
            try:
                out.append((name, json.loads(line[6:])))
            except json.JSONDecodeError:
                pass
    return out


def _open_stream(base: str, drill_id: str, stop: threading.Event) -> str:
    """读取 SSE 文本；stop 置位后断开连接（模拟用户切走页面）。"""
    req = urllib.request.Request(
        f"{base}/api/v1/drill/{drill_id}/stream?api_key={API_KEY}",
        headers={"Accept": "text/event-stream"},
    )
    chunks: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            while not stop.is_set():
                line = resp.readline()
                if not line:
                    break
                chunks.append(line.decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError):
        pass  # 主动断开
    return "".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--max-rounds", type=int, default=5)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    status, health = _req(base, "/api/v1/health")
    print(f"[0] health {status} {health}")

    status, started = _req(
        base,
        "/api/v1/drill/start",
        method="POST",
        body={"target_range": "10.0.0.0/24", "max_rounds": args.max_rounds},
    )
    drill_id = started["drill_id"]
    print(f"[1] start {status} drill_id={drill_id} mode_note=see_get_drill")

    # 订阅者 A：接入后立刻断开，模拟「点进去看一眼再切走」
    stop_a = threading.Event()
    a_buf = ""
    while len(_parse_events(a_buf)) < 2:
        raw = _open_stream(base, drill_id, stop_a)
        a_buf += raw
        time.sleep(0.4)
    early = _parse_events(a_buf)
    print(f"[2] subscriber A got {len(early)} events, first={early[0][0] if early else 'none'}")

    # 切页返回时前端会查 get_drill：必须带回恢复字段
    _, snap = _req(base, f"/api/v1/drill/{drill_id}")
    missing = [k for k in ("current_stage", "current_round", "elapsed", "agent_trace") if k not in snap]
    assert not missing, f"get_drill 缺少恢复字段: {missing}"
    trace_at_return = snap["agent_trace"]
    print(
        f"[3] get_drill restore -> status={snap['status']} round={snap['current_round']} "
        f"stage={snap['current_stage']} elapsed={snap['elapsed']}s trace={len(trace_at_return)} steps"
    )
    assert trace_at_return, "切回时 agent_trace 不应为空（否则界面会卡在等待首个 agent）"

    # 订阅者 B：晚接入，必须重放出 A 错过的历史
    stop_done = threading.Event()
    timer = threading.Timer(90.0, stop_done.set)
    timer.daemon = True
    timer.start()
    raw_b = _open_stream(base, drill_id, stop_done)
    b_events = _parse_events(raw_b)
    names_b = [n for n, _ in b_events]
    print(f"[4] subscriber B replayed {len(b_events)} events: {sorted(set(names_b))}")

    assert names_b and names_b[0] == "drill_start", "重放必须从 drill_start 开始"
    assert "drill_agent" in names_b, "重放必须包含 drill_agent（CoT 时间线）"
    assert "drill_round" in names_b, "重放必须包含 drill_round"

    # A 收到的事件必须是 B 的前缀（历史不丢）
    a_names = [n for n, _ in early]
    assert b_events[: len(a_names)] == list(early[: len(b_events) and len(a_names)]) or all(
        b_events[i] == early[i] for i in range(min(len(a_names), len(b_events)))
    ), "订阅者 B 的历史必须以 A 已收到的事件为前缀"

    # 等演练结束，核对最终状态与前端展示口径
    for _ in range(120):
        _, fin = _req(base, f"/api/v1/drill/{drill_id}")
        if fin["status"] != "running":
            break
        time.sleep(1.0)
    print(
        f"[5] final status={fin['status']} rounds_executed={fin['rounds_executed']} "
        f"convergence={fin.get('convergence_code')} trace_total={len(fin['agent_trace'])}"
    )
    assert fin["status"] == "done", f"演练应正常结束，实际 {fin['status']} / error={fin.get('error')}"
    assert fin["rounds_executed"] >= 1
    assert len(fin["agent_trace"]) >= len(trace_at_return), "结束后轨迹不应回退"

    print("\nPASS: 切走再切回可完整恢复进度与 CoT 推理时间线")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"\nFAIL: {exc}")
        sys.exit(1)
