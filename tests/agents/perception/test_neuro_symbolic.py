from protocol.cyber import AttackChain, AttackStep
from agents.perception.reasoning.neuro_symbolic import NeuroSymbolicLoop, validate_chain
from agents.tools.llms.mock_provider import MockProvider


def test_validate_chain_passes_valid_techniques():
    chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110", "T1021", "T1053"]}
    assert validate_chain(chain, rules) == []


def test_validate_chain_flags_invalid_technique():
    chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    issues = validate_chain(chain, rules)
    assert len(issues) == 1
    assert "T9999" in issues[0]


def test_loop_fixes_invalid_chain():
    # First call returns invalid technique, second call returns fixed
    mock = MockProvider(responses={
        "default": '{"chain_id": "c1", "target": "h1", "steps": [{"step_id": "s1", "technique": "T1110", "from_asset": "ext", "to_asset": "h1", "success": true}], "status": "validated"}'
    })
    loop = NeuroSymbolicLoop(provider=mock)
    bad_chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999", from_asset="ext", to_asset="h1"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    fixed = loop.validate_and_fix(bad_chain, rules, max_iterations=3)
    assert fixed.steps[0].technique == "T1110"


def test_loop_returns_original_after_max_iterations():
    mock = MockProvider(responses={
        "default": '{"chain_id": "c1", "steps": [{"step_id": "s1", "technique": "T9999"}], "status": "failed"}'
    })
    loop = NeuroSymbolicLoop(provider=mock)
    bad_chain = AttackChain(chain_id="c1", steps=[
        AttackStep(step_id="s1", technique="T9999"),
    ])
    rules = {"allowed_techniques": ["T1110"]}
    result = loop.validate_and_fix(bad_chain, rules, max_iterations=1)
    assert result.steps[0].technique == "T9999"
