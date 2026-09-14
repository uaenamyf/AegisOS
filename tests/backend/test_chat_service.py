# date: 2026-09-14
# dev: OpenSquilla
# changelog: R23 新增 ChatService 单测——意图分类 / 无基础设施显式降级 / 端点演练短路
"""Chat 对话服务测试（离线，不调真实 LLM）。"""

from __future__ import annotations

import os

os.environ.setdefault("AEGIS_USE_MOCK", "true")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.auth import API_KEY_HEADER, DEV_API_KEY
from backend.core.routes import router as gateway_router
from backend.services.chat_service import ChatService


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(gateway_router)
    return TestClient(app)


def test_classify_intent() -> None:
    svc = ChatService(infra_provider=lambda: None)
    assert svc.classify("发起一次完整红蓝紫攻防演练 10.0.0.0/24") == "drill"
    assert svc.classify("总结当前系统情况") == "system_status"
    assert svc.classify("你好，介绍一下AegisOS") == "chat"


def test_degrade_marks_local_not_cloud() -> None:
    """无基础设施时显式降级：tier=device、provider=mock-local，绝不冒充云侧。"""
    svc = ChatService(infra_provider=lambda: None)
    result = svc.chat("你好", "s-1")
    assert result["ok"] is True
    assert result["tier"] == "device"
    assert result["provider"] == "mock-local"
    assert result["text"]  # 诚实的中文降级说明，而非固定 JSON
    assert "{" not in result["text"][:1]


def test_endpoint_rejects_empty_goal() -> None:
    client = _client()
    resp = client.post(
        "/api/v1/chat",
        json={"goal": "   "},
        headers={API_KEY_HEADER: DEV_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_endpoint_drill_short_circuits_to_frontend() -> None:
    """演练语义不在 /chat 执行，返回 intent=drill 让前端转演练链路。"""
    client = _client()
    resp = client.post(
        "/api/v1/chat",
        json={"goal": "启动一次完整红蓝紫攻防演练"},
        headers={API_KEY_HEADER: DEV_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["intent"] == "drill"
    assert data["error"] == "drill_required_frontend"
