from agents.action.detector.agent import DetectorAgent
from agents.tools.llms.mock_provider import MockProvider


def test_detect_returns_alerts():
    mock = MockProvider(
        responses={
            "default": '{"alerts": [{"alert_id": "a1", "severity": "high", "src": "ext", "dst": "h1", "technique": "T1110", "raw": {"port": 22}}]}'
        }
    )
    agent = DetectorAgent(provider=mock)
    events = [{"type": "ssh_brute_force", "src": "ext", "dst": "h1"}]
    alerts = agent.detect(events)
    assert len(alerts) == 1
    assert alerts[0].severity == "high"
    assert alerts[0].technique == "T1110"


def test_detect_returns_empty_on_no_anomaly():
    mock = MockProvider(responses={"default": '{"alerts": []}'})
    agent = DetectorAgent(provider=mock)
    alerts = agent.detect([{"type": "normal_traffic"}])
    assert alerts == []
