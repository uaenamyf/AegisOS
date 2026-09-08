# date: 2026-09-04
# dev: OpenSquilla
# changelog: R2 新建——CyberDefenseService.drill 透出编排器 run_drill 并持久化演练记录
"""R2 服务层演练测试：drill 一键闭环 + 记录持久化/读取/列表。

验证：
    - CyberDefenseService.drill 透出 run_drill，返回含 drill_id/rounds/
      convergence_code/summary 的结构；
    - 演练记录写入 data/drills/（测试用 tmp_path 隔离），get_drill 可回读，
      list_drills 返回元信息，缺失 drill 返回 None；
    - on_round 回调每轮触发一次。
"""

from __future__ import annotations

from backend.services.cyber_defense_service import CyberDefenseService


def _make_service(tmp_path):
    svc = CyberDefenseService()
    svc._drill_dir = tmp_path  # 隔离到临时目录，不污染 data/drills/
    return svc


def test_drill_returns_converged_record(tmp_path):
    svc = _make_service(tmp_path)
    rec = svc.drill("10.0.0.0/24", max_rounds=5)
    assert rec["drill_id"] == "drill_10.0.0.0_24"
    assert rec["target_range"] == "10.0.0.0/24"
    assert rec["rounds_executed"] >= 2  # 多轮收敛真实推进（R1.5 演化 mock）
    assert rec["convergence_code"] == "converged"
    assert len(rec["rounds"]) == rec["rounds_executed"]
    assert "conclusion" in rec["summary"]
    assert "created_at" in rec


def test_drill_record_persisted_and_readable(tmp_path):
    svc = _make_service(tmp_path)
    rec = svc.drill("10.0.0.0/24")
    drill_id = rec["drill_id"]

    # 落盘文件存在
    assert (tmp_path / f"{drill_id}.json").exists()

    back = svc.get_drill(drill_id)
    assert back is not None
    assert back["drill_id"] == drill_id
    assert back["rounds_executed"] == rec["rounds_executed"]
    assert len(back["rounds"]) == rec["rounds_executed"]
    assert back["convergence_code"] == rec["convergence_code"]


def test_get_drill_missing_returns_none(tmp_path):
    svc = _make_service(tmp_path)
    assert svc.get_drill("drill_does_not_exist") is None


def test_list_drills_metadata(tmp_path):
    svc = _make_service(tmp_path)
    svc.drill("10.0.0.0/24")
    svc.drill("192.168.1.0/24")

    drills = svc.list_drills()
    ids = [d["drill_id"] for d in drills]
    assert "drill_10.0.0.0_24" in ids
    assert "drill_192.168.1.0_24" in ids
    # 每条都含元信息
    for d in drills:
        assert "target_range" in d
        assert "rounds_executed" in d
        assert "convergence_code" in d


def test_drill_list_empty_when_no_records(tmp_path):
    svc = _make_service(tmp_path)
    assert svc.list_drills() == []


def test_drill_on_round_callback_called_per_round(tmp_path):
    svc = _make_service(tmp_path)
    seen: list[int] = []
    rec = svc.drill("10.0.0.0/24", on_round=lambda data, r: seen.append(r))
    assert seen == list(range(1, rec["rounds_executed"] + 1))
