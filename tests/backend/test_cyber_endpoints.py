# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""攻防端点集成测试。

覆盖 Phase F 全部 REST 端点：
    - POST /api/v1/range/start — 启动靶场
    - GET  /api/v1/range/{id} — 查询靶场
    - GET  /api/v1/range/{id}/topology — 拓扑
    - POST /api/v1/attack — 红队攻击
    - GET  /api/v1/attack/chain/{range_id} — 攻击链
    - POST /api/v1/defense — 蓝队防御
    - GET  /api/v1/defense/{range_id} — 防御查询
    - POST /api/v1/defense/purple-review — 紫队校验
    - GET  /api/v1/threat/attack-techniques — 威胁情报
"""

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


class TestRangeEndpoints:
    """靶场管理端点测试。"""

    def test_start_range(self, client: TestClient):
        """POST /range/start 应返回 range_id 和拓扑。"""
        resp = client.post(
            "/api/v1/range/start",
            json={"target_range": "192.168.1.0/24", "label": "test-range"},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["range_id"].startswith("range-")
        assert data["target_range"] == "192.168.1.0/24"
        assert data["label"] == "test-range"
        assert data["status"] == "active"
        assert "topology" in data
        assert len(data["topology"]["nodes"]) >= 1

    def test_get_range(self, client: TestClient):
        """GET /range/{id} 应返回靶场信息。"""
        start = client.post(
            "/api/v1/range/start",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        )
        range_id = start.json()["range_id"]

        resp = client.get(f"/api/v1/range/{range_id}", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["range_id"] == range_id
        assert data["target_range"] == "10.0.0.0/24"

    def test_get_range_not_found(self, client: TestClient):
        """不存在的 range_id 应返回 404。"""
        resp = client.get("/api/v1/range/nonexistent", headers=_AUTH_HEADERS)
        assert resp.status_code == 404

    def test_get_topology(self, client: TestClient):
        """GET /range/{id}/topology 应返回网络拓扑。"""
        start = client.post(
            "/api/v1/range/start",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        )
        range_id = start.json()["range_id"]

        resp = client.get(f"/api/v1/range/{range_id}/topology", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_range"] == "10.0.0.0/24"
        assert len(data["nodes"]) >= 1
        assert len(data["edges"]) >= 1


class TestAttackEndpoints:
    """红队攻击端点测试。"""

    def test_red_attack(self, client: TestClient):
        """POST /attack 应返回资产、漏洞和攻击链。"""
        resp = client.post(
            "/api/v1/attack",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["assets"]) >= 2
        assert len(data["findings"]) >= 1
        assert data["chain"]["chain_id"] == "chain-1"
        assert data["chain"]["status"] == "planned"
        assert len(data["chain"]["steps"]) >= 1

    def test_get_attack_chain_by_range(self, client: TestClient):
        """GET /attack/chain/{range_id} 应返回缓存的攻击链。"""
        start = client.post(
            "/api/v1/range/start",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        )
        range_id = start.json()["range_id"]

        resp = client.get(f"/api/v1/attack/chain/{range_id}", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain"]["chain_id"] == "chain-1"


class TestDefenseEndpoints:
    """蓝队防御端点测试。"""

    def test_blue_defense(self, client: TestClient):
        """POST /defense 应返回告警和响应计划。"""
        resp = client.post(
            "/api/v1/defense",
            json={
                "event_stream": [
                    {"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}
                ]
            },
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alerts"]) >= 1
        assert data["plan"]["plan_id"] == "rp-1"
        assert len(data["plan"]["actions"]) >= 1
        assert data["plan"]["confidence"] > 0.0

    def test_get_defense_by_range(self, client: TestClient):
        """GET /defense/{range_id} 应返回防御响应。"""
        start = client.post(
            "/api/v1/range/start",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        )
        range_id = start.json()["range_id"]

        resp = client.get(f"/api/v1/defense/{range_id}", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"]["plan_id"] == "rp-1"

    def test_purple_review(self, client: TestClient):
        """POST /defense/purple-review 应返回批判和审查结果。"""
        red = client.post(
            "/api/v1/attack",
            json={"target_range": "10.0.0.0/24"},
            headers=_AUTH_HEADERS,
        ).json()
        blue = client.post(
            "/api/v1/defense",
            json={"event_stream": [{"event": "ssh-brute-force"}]},
            headers=_AUTH_HEADERS,
        ).json()

        resp = client.post(
            "/api/v1/defense/purple-review",
            json={
                "attack_chain": red["chain"],
                "response_plan": blue["plan"],
                "alerts": blue["alerts"],
            },
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "critique" in data
        assert "review" in data
        assert data["critique"]["valid"] is True
        assert data["review"]["consistent"] is True


class TestThreatEndpoints:
    """威胁情报端点测试。"""

    def test_get_all_techniques(self, client: TestClient):
        """GET /threat/attack-techniques 应返回全部威胁情报。"""
        resp = client.get("/api/v1/threat/attack-techniques", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 8  # 种子库有 8 条
        first = data[0]
        assert "technique" in first
        assert "tactic" in first
        assert "technique_id" in first
        assert "risk_level" in first

    def test_filter_by_tactic(self, client: TestClient):
        """GET /threat/attack-techniques?tactic=Execution 应返回过滤结果。"""
        resp = client.get(
            "/api/v1/threat/attack-techniques",
            params={"tactic": "Execution"},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(t["tactic"] == "Execution" for t in data)

    def test_threat_intel_has_attack_mapping(self, client: TestClient):
        """威胁情报应包含 ATT&CK 技战术映射字段。"""
        resp = client.get(
            "/api/v1/threat/attack-techniques",
            params={"tactic": "Execution"},
            headers=_AUTH_HEADERS,
        )
        data = resp.json()
        entry = data[0]
        assert entry["technique_id"] == "T1059"
        assert entry["sub_technique"] == "T1059.004 Unix Shell"
        assert "detection" in entry
        assert "mitigation" in entry
        assert entry["risk_level"] == "high"
