from protocol.cyber import (
    Asset, VulnFinding, AttackStep, AttackChain,
    Alert, DefenseAction, ResponsePlan, ThreatIntel,
)


def test_asset_fields():
    a = Asset(asset_id="h1", host="10.0.0.1", services=["ssh:22", "http:80"], os="linux")
    assert a.asset_id == "h1"
    assert a.services == ["ssh:22", "http:80"]
    assert a.os == "linux"


def test_vuln_finding_fields():
    v = VulnFinding(
        finding_id="v1", cve_id="CVE-2024-1", asset_id="h1",
        cvss=9.8, attack_surface="ssh",
    )
    assert v.cvss == 9.8
    assert v.attack_surface == "ssh"


def test_attack_step_and_chain():
    s = AttackStep(
        step_id="s1", technique="T1110",
        from_asset="ext", to_asset="h1", success=True,
    )
    chain = AttackChain(chain_id="c1", target="h1", steps=[s], status="ongoing")
    assert chain.steps[0].technique == "T1110"
    assert chain.steps[0].success is True
    assert chain.status == "ongoing"


def test_alert_and_defense_action():
    a = Alert(
        alert_id="a1", severity="high", src="ext", dst="h1",
        technique="T1110", raw={"port": 22},
    )
    d = DefenseAction(
        action_id="d1", kind="isolate", target="h1", rationale="lateral move",
    )
    assert a.severity == "high"
    assert a.raw == {"port": 22}
    assert d.kind == "isolate"


def test_response_plan_and_threat_intel():
    rp = ResponsePlan(
        plan_id="rp1", actions=[], confidence=0.85, rollback={"enabled": False},
    )
    ti = ThreatIntel(
        technique="T1110", tactic="credential-access", refs=["CVE-2024-1"],
    )
    assert rp.confidence == 0.85
    assert ti.tactic == "credential-access"
    assert ti.refs == ["CVE-2024-1"]


def test_attack_chain_to_dict_roundtrip():
    s = AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1")
    chain = AttackChain(chain_id="c1", target="h1", steps=[s], status="ongoing")
    d = chain.to_dict()
    assert d["chain_id"] == "c1"
    restored = AttackChain.from_dict(d)
    assert restored.steps[0].technique == "T1110"
