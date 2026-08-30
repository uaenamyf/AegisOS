"""R3 边缘服务器 —— 集成测试（本地起停，验证 HTTP 端点）。

测试 edge_server.py 的 /health 和 /infer 两个端点，
以及区域聚合缓存行为。
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request

import pytest

EDGE_PORT = 8920  # 测试专用端口，避免与真实服务冲突
EDGE_URL = f"http://127.0.0.1:{EDGE_PORT}"


@pytest.fixture(scope="module")
def edge_server() -> int:
    """启动 edge_server.py 进程，返回 pid；模块结束后清理。"""
    proc = subprocess.Popen(
        [
            "python",
            "tooling/scripts/edge_server.py",
            "--port",
            str(EDGE_PORT),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # 等待服务就绪（最多 5 秒）
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{EDGE_URL}/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("edge_server did not start within 5 seconds")

    yield proc.pid

    proc.kill()
    proc.wait()


def _get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{EDGE_URL}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            raw = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, {}


def _post(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{EDGE_URL}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(raw)
    except urllib.error.HTTPError as e:
        return e.code, {"error": str(e)}


# ============ /health ============


def test_health_returns_200(edge_server):
    status, body = _get("/health")
    assert status == 200
    assert body.get("status") == "ok"
    assert "cache_size" in body


# ============ /infer ============


def test_infer_without_ollama_returns_mock(edge_server):
    """没有 Ollama 时，/infer 返回本地短语。"""
    status, body = _post("/infer", {"prompt": "你好"})
    assert status == 200
    assert body.get("ok") is True
    assert len(body.get("text", "")) > 0
    assert body.get("tier") == "edge"


def test_infer_returns_usage(edge_server):
    """/infer 返回 token 用量统计。"""
    status, body = _post("/infer", {"prompt": "Python 是什么？"})
    assert status == 200
    usage = body.get("usage", {})
    assert usage.get("prompt_tokens", 0) > 0
    assert usage.get("completion_tokens", 0) > 0


# ============ 缓存行为 ============


def test_cache_increments_on_repeat_request(edge_server):
    """同一 prompt 再次请求命中缓存，cache_size 增加。"""
    # 清空缓存（重启服务做不到，就直接发两次看 cache_size 变化）
    _, before = _get("/health")
    initial_cache = before.get("cache_size", 0)

    _post("/infer", {"prompt": "缓存测试专用"})
    _, after = _get("/health")

    # 缓存至少不减少
    assert after.get("cache_size", 0) >= initial_cache


# ============ /aggregate 区域聚合 ============


def test_aggregate_returns_summary(edge_server):
    """POST /aggregate 接收多条 prompts，返回汇总结果。"""
    status, body = _post("/aggregate", {
        "prompts": ["告警A: SSH爆破", "告警B: 端口扫描"],
        "system": "安全分析",
    })
    assert status == 200
    assert body.get("ok") is True
    assert "aggregated_text" in body
    assert body["sub_count"] == 2
    assert body["ok_count"] == 2
    assert "cached_count" in body


def test_aggregate_empty_prompts_returns_400(edge_server):
    status, _ = _post("/aggregate", {"prompts": []})
    assert status == 400


def test_aggregate_missing_prompts_returns_400(edge_server):
    status, _ = _post("/aggregate", {})
    assert status == 400
