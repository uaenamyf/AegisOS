from protocol.cyber import Alert
from agents.action.threat_hunt.agent import ThreatHuntAgent
from agents.tools.llms.mock_provider import MockProvider


def test_hunt_returns_hypotheses():
    mock = MockProvider(responses={
        "default": '{"hypotheses": [{"hypothesis": "lateral movement via SMB", "confidence": 0.8, "technique": "T1021"}]}'
    })
    agent = ThreatHuntAgent(provider=mock)
    result = agent.hunt([Alert(alert_id="a1", severity="high", technique="T1110")])
    assert len(result) == 1
    assert result[0]["technique"] == "T1021"
    assert result[0]["confidence"] == 0.8


def test_hunt_returns_empty_on_no_threat():
    mock = MockProvider(responses={"default": '{"hypotheses": []}'})
    agent = ThreatHuntAgent(provider=mock)
    result = agent.hunt([])
    assert result == []
