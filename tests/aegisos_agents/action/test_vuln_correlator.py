from aegisos_agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Asset


def test_correlate_returns_findings():
    mock = MockProvider(
        responses={
            "default": '{"findings": [{"finding_id": "v1", "cve_id": "CVE-2024-1", "asset_id": "h1", "cvss": 9.8, "attack_surface": "ssh"}]}'
        }
    )
    agent = VulnCorrelatorAgent(provider=mock)
    findings = agent.correlate([Asset(asset_id="h1", host="10.0.0.1")])
    assert len(findings) == 1
    assert findings[0].cve_id == "CVE-2024-1"
    assert findings[0].cvss == 9.8


def test_correlate_empty_on_no_vulns():
    mock = MockProvider(responses={"default": '{"findings": []}'})
    agent = VulnCorrelatorAgent(provider=mock)
    findings = agent.correlate([Asset(asset_id="h1")])
    assert findings == []
