from aegisos_agents.action.forensics.agent import ForensicsAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import ResponsePlan


def test_investigate_returns_report():
    mock = MockProvider(
        responses={
            "default": '{"report_id": "f1", "root_cause": "unpatched ssh", "timeline": [{"ts": "t1", "event": "brute force"}], "recommendations": ["patch ssh"]}'
        }
    )
    agent = ForensicsAgent(provider=mock)
    plan = ResponsePlan(plan_id="rp1", confidence=0.9)
    report = agent.investigate(plan)
    assert report["report_id"] == "f1"
    assert report["root_cause"] == "unpatched ssh"
    assert len(report["timeline"]) == 1
    assert "patch ssh" in report["recommendations"]
