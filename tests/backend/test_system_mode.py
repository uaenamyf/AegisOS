# date: 2026-09-04
# dev: AegisOS Dev
# changelog: R7 新建——/api/v1/system/mode 运行时模式端点测试（mock/real 切换）
"""运行时模式端点测试：查询/切换 mock ↔ 真实 LLM。

覆盖 R7 全部行为：
    - GET  /api/v1/system/mode → 模式描述（mode/model/provider/has_key/available）
    - POST /api/v1/system/mode → 切换模式，real 无 Key 时 400
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import DEV_API_KEY

_AUTH_HEADERS = {"X-API-Key": DEV_API_KEY}


@pytest.fixture()
def client():
    """创建测试客户端（Mock 模式由 conftest 强制）。"""
    from backend.core.composition import reset_composition
    from backend.main import create_app

    reset_composition()
    app = create_app()
    return TestClient(app)


def test_get_mode_returns_description(client: TestClient):
    """GET /system/mode 返回模式描述。"""
    resp = client.get("/api/v1/system/mode", headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "model" in data
    assert "provider" in data
    assert "has_key" in data
    assert "available" in data
    # 测试环境 conftest 强制 mock
    assert data["mode"] == "mock"


def test_switch_to_mock_then_back(client: TestClient):
    """POST /system/mode 可在 mock/real 间切换（real 需 Key）。"""
    # 先查当前描述，按环境自适应断言（.env 有 Key 时 real 可用）
    info = client.get("/api/v1/system/mode", headers=_AUTH_HEADERS).json()
    has_key = info["has_key"]

    # 切到 mock（幂等）
    resp = client.post("/api/v1/system/mode", json={"mode": "mock"}, headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "mock"

    # 切到 real：有 Key 时成功；无 Key 时 400
    resp = client.post("/api/v1/system/mode", json={"mode": "real"}, headers=_AUTH_HEADERS)
    if has_key:
        assert resp.status_code == 200
        assert resp.json()["mode"] == "real"
    else:
        assert resp.status_code == 400
        body = resp.json()
        # 项目统一错误格式：{"code", "message", "trace_id"}（无 FastAPI 默认 detail）
        detail = body.get("detail")
        code = detail.get("code") if isinstance(detail, dict) else body.get("code")
        assert "INVALID_MODE" in str(code)

    # 收尾：切回 mock，避免把 real 模式泄漏给同进程后续测试
    resp = client.post("/api/v1/system/mode", json={"mode": "mock"}, headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "mock"


def test_invalid_mode_rejected(client: TestClient):
    """非法模式 422（pydantic Literal 校验）。"""
    resp = client.post("/api/v1/system/mode", json={"mode": "turbo"}, headers=_AUTH_HEADERS)
    assert resp.status_code == 422
