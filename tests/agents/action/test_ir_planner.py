from agents.action.ir_planner.agent import IRPlannerAgent
from agents.tools.llms.mock_provider import MockProvider


def test_plan_response_returns_response_plan():
    mock = MockProvider(
        responses={
            "default": '{"plan_id": "rp1", "actions": [{"action_id": "d1", "kind": "isolate", "target": "h1", "rationale": "stop lateral move"}], "confidence": 0.9, "rollback": {"enabled": true, "steps": ["reconnect"]}}'
        }
    )
    agent = IRPlannerAgent(provider=mock)
    hypotheses = [{"hypothesis": "lateral movement", "confidence": 0.8, "technique": "T1021"}]
    plan = agent.plan_response(hypotheses)
    assert plan.plan_id == "rp1"
    assert len(plan.actions) == 1
    assert plan.actions[0]["kind"] == "isolate"
    assert plan.confidence == 0.9
    assert plan.rollback["enabled"] is True


def test_plan_response_has_empty_actions_on_no_hypotheses():
    mock = MockProvider(
        responses={
            "default": '{"plan_id": "rp0", "actions": [], "confidence": 0.0, "rollback": {"enabled": false}}'
        }
    )
    agent = IRPlannerAgent(provider=mock)
    plan = agent.plan_response([])
    assert plan.actions == []
