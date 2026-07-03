from agents.action.critic.agent import CriticAgent
from agents.tools.llms.mock_provider import MockProvider


def test_critique_red_chain_flags_issue():
    mock = MockProvider(
        responses={
            "default": '{"valid": false, "issues": ["missing persistence step"], "severity": "medium", "suggestion": "add T1053 for persistence"}'
        }
    )
    agent = CriticAgent(provider=mock)
    result = agent.critique({"chain_id": "c1", "steps": []}, side="red")
    assert result["valid"] is False
    assert "missing persistence step" in result["issues"]
    assert result["severity"] == "medium"


def test_critique_blue_plan_passes():
    mock = MockProvider(
        responses={"default": '{"valid": true, "issues": [], "severity": "none", "suggestion": ""}'}
    )
    agent = CriticAgent(provider=mock)
    result = agent.critique({"plan_id": "rp1"}, side="blue")
    assert result["valid"] is True
    assert result["issues"] == []
