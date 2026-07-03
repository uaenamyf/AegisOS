import pytest
from agents.tools.llms.base import ModelProvider, LLMRequest, LLMResponse
from agents.tools.llms.mock_provider import MockProvider
from agents.tools.llms.model_router import ModelRouter
from agents.tools.llms.scheduler_adapter import schedule_for_llm
from protocol.scheduler import Task
from agents.planning.engine.scheduler.scheduler import Model


def test_mock_provider_returns_response():
    provider = MockProvider(responses={"hello": "world"})
    req = LLMRequest(prompt="hello", model_id="mock-1")
    resp = provider.complete(req)
    assert resp.text == "world"
    assert resp.ok is True


def test_model_router_dispatches_to_correct_provider():
    mock_openai = MockProvider(responses={"default": "openai_response"})
    mock_anthropic = MockProvider(responses={"default": "anthropic_response"})
    mock_local = MockProvider(responses={"default": "local_response"})
    router = ModelRouter(
        providers={
            "openai": mock_openai,
            "anthropic": mock_anthropic,
            "local": mock_local,
        },
        default_provider="openai",
    )
    resp = router.complete(LLMRequest(prompt="test", model_id="gpt-4"))
    assert resp.text == "openai_response"


def test_model_router_falls_back_to_default():
    mock_default = MockProvider(responses={"default": "fallback"})
    router = ModelRouter(
        providers={"default": mock_default},
        default_provider="default",
    )
    resp = router.complete(LLMRequest(prompt="test", model_id="unknown-model"))
    assert resp.text == "fallback"


def test_mock_provider_without_matching_response_returns_stub():
    provider = MockProvider()
    req = LLMRequest(prompt="anything", model_id="mock-1")
    resp = provider.complete(req)
    assert resp.ok is True
    assert len(resp.text) > 0


def test_router_uses_scheduler_result():
    """Router selects provider based on scheduler Model.tier -> provider mapping."""
    mock_edge = MockProvider(responses={"default": "edge_response"})
    mock_cloud = MockProvider(responses={"default": "cloud_response"})
    router = ModelRouter(
        providers={"edge": mock_edge, "cloud": mock_cloud},
        default_provider="cloud",
    )
    # Simulate scheduler picking edge model
    edge_model = Model(model_id="edge_small", tier="edge", capabilities=["triage"])
    resp = router.complete_with_model(
        LLMRequest(prompt="triage this alert", model_id="edge_small"),
        edge_model,
    )
    assert resp.text == "edge_response"
