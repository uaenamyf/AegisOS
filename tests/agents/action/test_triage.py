from agents.action.triage.agent import TriageAgent
from agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert


def test_triage_sorts_by_severity():
    mock = MockProvider(
        responses={
            "default": '{"alerts": [{"alert_id": "a2", "severity": "critical"}, {"alert_id": "a1", "severity": "low"}]}'
        }
    )
    agent = TriageAgent(provider=mock)
    result = agent.triage(
        [
            Alert(alert_id="a1", severity="low"),
            Alert(alert_id="a2", severity="critical"),
        ]
    )
    assert result[0].alert_id == "a2"  # critical first
    assert result[1].alert_id == "a1"


def test_triage_deduplicates():
    mock = MockProvider(
        responses={"default": '{"alerts": [{"alert_id": "a1", "severity": "high"}]}'}
    )
    agent = TriageAgent(provider=mock)
    result = agent.triage(
        [
            Alert(alert_id="a1", severity="high"),
            Alert(alert_id="a1", severity="high"),
        ]
    )
    assert len(result) == 1
