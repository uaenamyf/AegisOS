# date: 2026-09-13
# dev: OpenSquilla
# changelog: 新增记忆端点测试——/memory/stats 暴露记忆子系统可观测统计

"""记忆 REST 端点测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# 网关鉴权所需 API Key（与 tooling/configs/defaults.yaml 一致）。
_API_KEY = "aegis-dev-key"
_AUTH_HEADERS = {"X-API-Key": _API_KEY}


@pytest.fixture()
def client():
    """创建测试客户端，使用 Mock 模式。"""
    from backend.core.composition import reset_composition
    from backend.main import create_app

    reset_composition()
    app = create_app()
    return TestClient(app)


class TestMemoryStatsEndpoint:
    """记忆子系统统计端点。"""

    def test_memory_stats_returns_layers(self, client: TestClient):
        """GET /memory/stats 应返回各层记忆与子系统状态。"""
        resp = client.get("/api/v1/memory/stats", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        # 关键层计数器存在
        for key in (
            "working_sessions",
            "episodic_total",
            "semantic_total",
            "vector_total",
            "archive_total",
            "checkpoint_total",
            "snapshot_total",
            "persisted",
            "auto_embed",
        ):
            assert key in data, f"stats 缺少字段 {key}"

    def test_memory_stats_requires_auth(self, client: TestClient):
        """无 API Key 访问应 401。"""
        resp = client.get("/api/v1/memory/stats")
        assert resp.status_code == 401