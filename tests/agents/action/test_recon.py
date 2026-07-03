from agents.action.recon.agent import ReconAgent
from agents.tools.llms.mock_provider import MockProvider


def test_recon_returns_assets_for_target_range():
    mock = MockProvider(
        responses={
            "default": '{"assets": [{"asset_id": "h1", "host": "10.0.0.1", "services": ["ssh:22"], "os": "linux"}]}'
        }
    )
    agent = ReconAgent(provider=mock)
    assets = agent.scan(target_range="10.0.0.0/24")
    assert len(assets) >= 1
    assert assets[0].asset_id == "h1"
    assert assets[0].host == "10.0.0.1"


def test_recon_returns_empty_on_no_response():
    mock = MockProvider(responses={"default": '{"assets": []}'})
    agent = ReconAgent(provider=mock)
    assets = agent.scan(target_range="10.0.0.0/24")
    assert assets == []
