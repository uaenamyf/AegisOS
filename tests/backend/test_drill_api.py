# date: 2026-09-04
# dev: AegisOS Dev
"""多轮攻防演练（CyberDrill）路由端点集成测试。

覆盖 R3 全部 5 个端点：
    - POST /api/v1/drill/start — 启动演练（201，返回 drill_id）
    - GET  /api/v1/drill/{id}/stream — SSE 实时战报（drill_start→round*→summary→done）
    - GET  /api/v1/drill/{id} — 状态与已发生轮次（轮询兜底）
    - GET  /api/v1/drill/{id}/summary — 收敛总结报告
    - POST /api/v1/drill/{id}/abort — 请求中止
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import DEV_API_KEY

_AUTH_HEADERS = {"X-API-Key": DEV_API_KEY}


@pytest.fixture()
def client():
    """创建测试客户端，使用 Mock 模式。"""
    from backend.core.composition import reset_composition
    from backend.main import create_app

    reset_composition()
    app = create_app()
    return TestClient(app)


def _start_drill(client: TestClient, target_range: str = "10.0.0.0/24", max_rounds: int = 5) -> str:
    """启动一场演练并返回 drill_id。"""
    resp = client.post(
        "/api/v1/drill/start",
        json={"target_range": target_range, "max_rounds": max_rounds},
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "running"
    assert data["max_rounds"] == max_rounds
    return data["drill_id"]


class TestDrillStart:
    """演练启动端点。"""

    def test_start_returns_201_and_drill_id(self, client: TestClient):
        """POST /drill/start 应返回 201 + drill_id + running 状态。"""
        drill_id = _start_drill(client)
        assert drill_id.startswith("drill-")

    def test_start_default_target(self, client: TestClient):
        """未传 target_range 时使用默认 10.0.0.0/24。"""
        resp = client.post("/api/v1/drill/start", json={}, headers=_AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["max_rounds"] == 5


class TestDrillStream:
    """SSE 战报流端点。"""

    def test_stream_emits_full_lifecycle(self, client: TestClient):
        """stream 应依次产出 drill_start → drill_round* → drill_summary → drill_done。"""
        drill_id = _start_drill(client)
        # 演练为同步编排且收敛较快，等待其完成后一次性读取队列中的全部事件
        time.sleep(2.0)
        with client.stream("GET", f"/api/v1/drill/{drill_id}/stream", headers=_AUTH_HEADERS) as resp:
            assert resp.status_code == 200
            body = resp.read().decode("utf-8")
        events = [ln.split("event: ")[1] for ln in body.splitlines() if ln.startswith("event: ")]
        assert events[0] == "drill_start"
        assert events[-2] == "drill_summary"
        assert events[-1] == "drill_done"
        assert "drill_round" in events
        assert events.count("drill_start") == 1
        assert events.count("drill_done") == 1

    def test_stream_unknown_drill_404(self, client: TestClient):
        """stream 未知 drill_id 应返回 404。"""
        resp = client.get("/api/v1/drill/drill-nope/stream", headers=_AUTH_HEADERS)
        assert resp.status_code == 404


class TestDrillQuery:
    """状态查询与总结端点。"""

    def test_get_after_completion(self, client: TestClient):
        """GET /drill/{id} 完成后应返回 done 状态与已发生轮次。"""
        drill_id = _start_drill(client)
        time.sleep(2.0)
        resp = client.get(f"/api/v1/drill/{drill_id}", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert len(data["rounds"]) >= 1

    def test_get_unknown_drill_404(self, client: TestClient):
        """GET /drill/{id} 未知 drill_id 应返回 404。"""
        resp = client.get("/api/v1/drill/drill-nope", headers=_AUTH_HEADERS)
        assert resp.status_code == 404

    def test_summary_after_convergence(self, client: TestClient):
        """GET /drill/{id}/summary 完成后应返回总结报告。"""
        drill_id = _start_drill(client)
        time.sleep(2.0)
        resp = client.get(f"/api/v1/drill/{drill_id}/summary", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "conclusion" in data
        assert "convergence_code" in data
        assert data["convergence_code"] == "converged"

    def test_summary_unknown_drill_404(self, client: TestClient):
        """summary 未知 drill_id 应返回 404。"""
        resp = client.get("/api/v1/drill/drill-nope/summary", headers=_AUTH_HEADERS)
        assert resp.status_code == 404


class TestDrillAbort:
    """中止端点。"""

    def test_abort_returns_aborted(self, client: TestClient):
        """POST /drill/{id}/abort 应返回 aborted 状态。"""
        drill_id = _start_drill(client)
        resp = client.post(f"/api/v1/drill/{drill_id}/abort", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"drill_id": drill_id, "status": "aborted"}

    def test_abort_unknown_drill_404(self, client: TestClient):
        """abort 未知 drill_id 应返回 404。"""
        resp = client.post("/api/v1/drill/drill-nope/abort", headers=_AUTH_HEADERS)
        assert resp.status_code == 404
