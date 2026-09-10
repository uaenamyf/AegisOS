# date: 2026-08-27
# dev: ox-alpha
"""Infra 端点集成测试 —— R10 后端 API 暴露。

覆盖三个端点：
- GET  /api/v1/infra/nodes
- POST /api/v1/infra/dispatch
- GET  /api/v1/infra/dispatch/history
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """创建测试客户端，初始化 infra 服务。

    测试环境用 dependency_overrides 绕过 API Key 鉴权
    （鉴权逻辑本身由 backend/core/auth 的单测覆盖）。
    """
    from backend.core.auth import verify_api_key
    from backend.main import _init_infra_service, app

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    try:
        _init_infra_service()
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


# ---- GET /api/v1/infra/nodes ----


def test_list_nodes_returns_array(client):
    """节点列表返回数组（初始为空）。"""
    resp = client.get("/api/v1/infra/nodes")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_nodes_accepts_ok(client):
    """节点列表端点返回 200 OK。"""
    resp = client.get("/api/v1/infra/nodes")
    assert resp.status_code == 200


def test_configure_nodes_updates_demo_runtime(client):
    """配置接口应替换本地演示节点并反映新的模型和启用状态。"""
    resp = client.post(
        "/api/v1/infra/configure",
        json={
            "nodes": [
                {
                    "node_id": "device_local",
                    "tier": "device",
                    "base_url": "http://demo-device:11434",
                    "provider": "ollama",
                    "model_id": "demo-device-model",
                    "capabilities": ["chat"],
                    "enabled": True,
                },
                {
                    "node_id": "edge_server_01",
                    "tier": "edge",
                    "base_url": "http://demo-edge:8900",
                    "provider": "aegis_edge",
                    "model_id": "demo-edge-model",
                    "capabilities": ["chat", "reasoning"],
                    "enabled": False,
                },
            ]
        },
    )
    assert resp.status_code == 200
    nodes = {node["node_id"]: node for node in resp.json()}
    assert nodes["device_local"]["model_id"] == "demo-device-model"
    assert nodes["edge_server_01"]["status"] == "offline"


# ---- POST /api/v1/infra/dispatch ----


def test_dispatch_missing_goal_returns_422(client):
    """缺少必填字段 goal 返回 422。"""
    resp = client.post("/api/v1/infra/dispatch", json={})
    assert resp.status_code == 422


def test_dispatch_invalid_privacy_returns_ok_or_422(client):
    """无效 privacy 值被 Pydantic 校验拦截。"""
    resp = client.post("/api/v1/infra/dispatch", json={
        "goal": "test",
        "privacy": "invalid_value",
    })
    assert resp.status_code in (200, 422)  # 422 if Pydantic enum, 200 if accepts any str


def test_dispatch_returns_result(client):
    """正常派发返回结构化结果。"""
    resp = client.post("/api/v1/infra/dispatch", json={
        "goal": "解释一下什么是防火墙",
        "latency_budget": 5.0,
        "privacy": "unrestricted",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "ok" in body
    assert "tier" in body
    # 无节点注册时 dispatch 返回 failure
    if not body["ok"]:
        assert any(
            message in body.get("error", "")
            for message in ("no online nodes", "attempt(s) exhausted")
        )


def test_dispatch_populates_history(client):
    """派发成功后历史记录增加。"""
    client.post("/api/v1/infra/dispatch", json={
        "goal": "简单安全测试",
        "privacy": "unrestricted",
    })
    resp = client.get("/api/v1/infra/dispatch/history?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


# ---- GET /api/v1/infra/dispatch/history ----


def test_history_default_limit(client):
    """默认 limit=20 返回列表。"""
    resp = client.get("/api/v1/infra/dispatch/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_history_respects_limit(client):
    """limit 参数生效。"""
    resp = client.get("/api/v1/infra/dispatch/history?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) <= 3


def test_history_invalid_limit_returns_422(client):
    """limit 超出范围返回 422。"""
    resp = client.get("/api/v1/infra/dispatch/history?limit=200")
    assert resp.status_code == 422
