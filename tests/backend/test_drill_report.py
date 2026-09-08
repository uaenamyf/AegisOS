# date: 2026-09-05
# dev: OpenSquilla
# changelog: 新建——Auto Drill 运行记录报告 + 云侧 API Key 配置端点测试
"""Auto Drill 运行记录报告 & API Key 端点测试。

覆盖：
    - ``build_drill_report``：报告含元信息 / 卸载轨迹 / 逐轮红蓝紫战报 / 收敛总结；
    - ``write_drill_report``：落盘到指定目录；
    - ``POST /api/v1/system/api-key``：写入 env 文件 + 即时生效 + has_key 反映；
    - ``GET /api/v1/drill/{id}/report``：演练完成后返回 Markdown 报告。
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import DEV_API_KEY
from backend.services.drill_report import build_drill_report, build_drill_report_json, write_drill_report

_AUTH_HEADERS = {"X-API-Key": DEV_API_KEY}


def _synthetic_record() -> dict:
    """构造一份小型演练记录（含两轮红蓝紫产物）。"""
    return {
        "drill_id": "drill-report-test",
        "target_range": "10.0.0.0/24",
        "max_rounds": 2,
        "rounds_executed": 2,
        "convergence_code": "converged",
        "rounds": [
            {
                "round": 1,
                "convergence_code": "exploring",
                "phase": {
                    "red": {"tier": "device", "model_id": "device_firewall", "reason": "攻击链实时生成（超低延迟） → 端侧·超低延迟/本地隐私"},
                    "blue": {"tier": "edge", "model_id": "edge_gateway", "reason": "防御响应低延迟 → 边侧·低延迟/区域隔离"},
                    "purple": {"tier": "cloud", "model_id": "cloud_gpu", "reason": "评审总结高算力需求 → 云侧·强算力/可脱敏"},
                },
                "red": {
                    "ok": True,
                    "assets": ["asset-001", "asset-002"],
                    "finding_count": 8,
                    "steps": [
                        {"step_id": "s1", "technique": "Exploit CVE-2021-41773", "from_asset": "asset-001", "to_asset": "asset-001", "success": True}
                    ],
                    "new_steps": [
                        {"step_id": "s1", "technique": "Exploit CVE-2021-41773", "from_asset": "asset-001", "to_asset": "asset-001", "success": True}
                    ],
                },
                "blue": {
                    "ok": True,
                    "alerts": [
                        {"alert_id": "a1", "severity": "high", "src": "10.0.0.5", "dst": "10.0.0.1", "technique": "T1190"}
                    ],
                    "triaged_count": 1,
                    "plan": {
                        "plan_id": "p1",
                        "confidence": 0.9,
                        "actions": [{"action": "Patch CVE-2021-41773 on asset-001"}],
                    },
                },
                "purple": {
                    "ok": True,
                    "critique": {"valid": True, "issues": [], "suggestion": "继续探测横向移动面"},
                    "review": {"overall_assessment": "红蓝对抗有效，攻击链与防御动作一致"},
                    "converged": False,
                    "valid": True,
                    "new_issue_count": 0,
                },
                "event_stream": [],
            },
            {
                "round": 2,
                "convergence_code": "converged",
                "phase": {
                    "red": {"tier": "device", "model_id": "device_firewall", "reason": "攻击链实时生成（超低延迟） → 端侧·超低延迟/本地隐私"},
                    "blue": {"tier": "device", "model_id": "device_firewall", "reason": "防御响应低延迟（第 2 轮负载 82%） → 端侧·超低延迟/本地隐私"},
                    "purple": {"tier": "edge", "model_id": "edge_gateway", "reason": "评审总结高算力需求（第 2 轮负载 82%） → 边侧·低延迟/区域隔离"},
                },
                "red": {"ok": True, "assets": ["asset-001"], "finding_count": 8, "steps": [], "new_steps": []},
                "blue": {"ok": True, "alerts": [], "triaged_count": 0, "plan": {"plan_id": "p2", "confidence": 0.8, "actions": []}},
                "purple": {"ok": True, "critique": {"valid": True, "issues": [], "suggestion": ""}, "review": {"overall_assessment": "已收敛"}, "converged": True, "valid": True, "new_issue_count": 0},
                "event_stream": [],
            },
        ],
        "summary": {
            "conclusion": "多轮红蓝紫对抗后达成收敛：攻击链覆盖全部暴露面并通过紫队一致性校验。",
            "convergence_code": "converged",
            "rounds_executed": 2,
            "memory_trace": [
                {"round": 1, "stored_task_id": "drill-report-test:r1", "next_round_summary": "round 1: valid=True new_issues=0"}
            ],
        },
    }


class TestDrillReport:
    def test_build_drill_report_contains_sections(self):
        md = build_drill_report(_synthetic_record())
        assert "Auto Drill 运行记录" in md
        assert "drill-report-test" in md
        assert "2. 端-边-云卸载轨迹" in md
        assert "3. 逐轮战报" in md
        assert "Round 1" in md and "Round 2" in md
        assert "红队攻击" in md and "蓝队防御" in md and "紫队评审" in md
        assert "CVE-2021-41773" in md
        assert "Patch CVE-2021-41773" in md
        assert "4. 收敛总结" in md
        assert "converged" in md

    def test_write_drill_report_persists_file(self, tmp_path):
        path = write_drill_report(_synthetic_record(), out_dir=tmp_path)
        assert path.exists()
        assert path.name == "drill-report-test.md"
        content = path.read_text(encoding="utf-8")
        assert "Round 1" in content

    def test_build_drill_report_json(self):
        payload = build_drill_report_json(_synthetic_record())
        assert payload["drill_id"] == "drill-report-test"
        assert "report_md" in payload
        assert payload["raw_json_path"] == "data/drills/drill-report-test.json"


class TestSystemApiKeyEndpoint:
    @pytest.fixture()
    def client(self):
        from backend.core.composition import reset_composition
        from backend.main import create_app

        reset_composition()
        app = create_app()
        return TestClient(app)

    def test_set_api_key_syncs_and_describes(self, client, tmp_path, monkeypatch):
        # 用临时 env 文件避免污染真实 tooling/configs/.env
        import backend.routers.system as system_mod

        fake_env = tmp_path / ".env"
        monkeypatch.setattr(system_mod, "_ENV_PATH", fake_env)

        old_key = None
        import os

        old_key = os.environ.get("OPENAI_API_KEY")
        try:
            resp = client.post(
                "/api/v1/system/api-key",
                json={"api_key": "sk-test-1234567890"},
                headers=_AUTH_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["has_key"] is True
            assert "sk-test-1234567890" not in str(data)  # 不回显 Key
            # env 文件已写入
            assert fake_env.exists()
            assert "OPENAI_API_KEY=sk-test-1234567890" in fake_env.read_text(encoding="utf-8")
            # 进程环境变量已生效
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-1234567890"
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_set_api_key_rejects_short_key(self, client, tmp_path, monkeypatch):
        import backend.routers.system as system_mod

        monkeypatch.setattr(system_mod, "_ENV_PATH", tmp_path / ".env")
        resp = client.post(
            "/api/v1/system/api-key",
            json={"api_key": "short"},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 400


class TestDrillReportEndpoint:
    @pytest.fixture()
    def client(self):
        from backend.core.composition import reset_composition
        from backend.main import create_app

        reset_composition()
        app = create_app()
        return TestClient(app)

    def test_report_after_drill_done(self, client):
        # 启动一场 mock 演练（后台线程，轮询等待完成）
        resp = client.post(
            "/api/v1/drill/start",
            json={"target_range": "10.0.0.0/24", "max_rounds": 2},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 201
        drill_id = resp.json()["drill_id"]

        # 轮询直到 done（mock 应秒级完成）
        for _ in range(50):
            rec = client.get(f"/api/v1/drill/{drill_id}", headers=_AUTH_HEADERS).json()
            if rec["status"] == "done":
                break
            time.sleep(0.2)
        else:
            pytest.fail("drill did not finish in time")

        report = client.get(f"/api/v1/drill/{drill_id}/report", headers=_AUTH_HEADERS)
        assert report.status_code == 200
        payload = report.json()
        assert payload["drill_id"] == drill_id
        assert "Auto Drill 运行记录" in payload["report_md"]
        assert "红队攻击" in payload["report_md"]
        assert "蓝队防御" in payload["report_md"]
