# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 测试更新为端边云三层调度（device → edge → cloud）
from agents.planning.engine.scheduler.scheduler import (
    DEVICE_THRESHOLD,
    EDGE_THRESHOLD,
    Model,
    schedule,
)
from protocol.scheduler import Task


# --- 端侧（device）测试 ---


def test_privacy_local_picks_device_model():
    """隐私敏感任务必须端侧处理。"""
    task = Task(goal="triage alert", privacy="local")
    models = [
        Model(model_id="device_small", tier="device", size="small", capabilities=["triage"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["triage"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["triage"]),
    ]
    result = schedule(task, models)
    assert result.tier == "device"


def test_ultra_low_latency_picks_device():
    """超低延迟（< DEVICE_THRESHOLD）优先端侧。"""
    task = Task(goal="detect", privacy="unrestricted", latency_budget=DEVICE_THRESHOLD - 0.1)
    models = [
        Model(model_id="device_small", tier="device", size="small", capabilities=["detect"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["detect"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["detect"]),
    ]
    result = schedule(task, models)
    assert result.tier == "device"


def test_ultra_low_latency_no_device_falls_back_to_edge():
    """超低延迟但无端侧模型时降级到边侧。"""
    task = Task(goal="detect", privacy="unrestricted", latency_budget=DEVICE_THRESHOLD - 0.1)
    models = [
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["detect"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["detect"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


# --- 边侧（edge）测试 ---


def test_low_latency_picks_edge():
    """低延迟（DEVICE_THRESHOLD < budget < EDGE_THRESHOLD）优先边侧。"""
    task = Task(goal="detect", privacy="unrestricted", latency_budget=EDGE_THRESHOLD - 0.1)
    models = [
        Model(model_id="device_small", tier="device", size="small", capabilities=["detect"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["detect"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["detect"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


def test_privacy_local_no_device_falls_back_to_edge():
    """隐私敏感但无端侧模型时降级到边侧（延迟最低的可用层）。"""
    task = Task(goal="triage alert", privacy="local")
    models = [
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["triage"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["triage"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


# --- 云侧（cloud）测试 ---


def test_high_latency_no_privacy_picks_cloud():
    """高延迟容忍 + 无隐私约束 → 云侧（算力最强）。"""
    task = Task(goal="attack_chain_planning", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="device_small", tier="device", size="small", capabilities=["planning"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["planning"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["planning"]),
    ]
    result = schedule(task, models)
    assert result.tier == "cloud"


# --- 能力过滤测试 ---


def test_filters_by_required_capability():
    """按 required_capability 过滤后选云侧。"""
    task = Task(goal="hunt", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="device_small", tier="device", size="small", capabilities=["triage"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["triage"]),
        Model(model_id="cloud_hunt", tier="cloud", size="large", capabilities=["hunt"]),
    ]
    result = schedule(task, models, required_capability="hunt")
    assert result.model_id == "cloud_hunt"


def test_three_tier_all_present():
    """三层模型同时存在时，中延迟任务选边侧。"""
    task = Task(goal="analyze", privacy="standard", latency_budget=3.0)
    models = [
        Model(model_id="device_tiny", tier="device", size="small", capabilities=["analyze"]),
        Model(model_id="edge_mid", tier="edge", size="medium", capabilities=["analyze"]),
        Model(model_id="cloud_big", tier="cloud", size="large", capabilities=["analyze"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"
