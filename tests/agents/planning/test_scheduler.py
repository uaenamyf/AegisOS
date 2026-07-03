import pytest
from protocol.scheduler import Task
from agents.planning.engine.scheduler.scheduler import schedule, Model, EDGE_THRESHOLD


def test_privacy_local_picks_edge_model():
    task = Task(goal="triage alert", privacy="local")
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["triage"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["triage"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


def test_low_latency_picks_edge():
    task = Task(goal="detect", privacy="unrestricted", latency_budget=EDGE_THRESHOLD - 0.1)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["detect"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["detect"]),
    ]
    result = schedule(task, models)
    assert result.tier == "edge"


def test_high_latency_no_privacy_picks_cloud():
    task = Task(goal="attack_chain_planning", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["planning"]),
        Model(model_id="cloud_large", tier="cloud", size="large", capabilities=["planning"]),
    ]
    result = schedule(task, models)
    assert result.tier == "cloud"


def test_filters_by_required_capability():
    task = Task(goal="hunt", privacy="unrestricted", latency_budget=60.0)
    models = [
        Model(model_id="edge_small", tier="edge", size="small", capabilities=["triage"]),
        Model(model_id="cloud_hunt", tier="cloud", size="large", capabilities=["hunt"]),
    ]
    result = schedule(task, models, required_capability="hunt")
    assert result.model_id == "cloud_hunt"
