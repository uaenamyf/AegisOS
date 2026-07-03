from agents.action.reviewer.agent import ReviewerAgent
from agents.tools.llms.mock_provider import MockProvider


def test_review_returns_consistent():
    mock = MockProvider(responses={
        "default": '{"consistent": true, "findings": [], "overall_assessment": "all artifacts align"}'
    })
    agent = ReviewerAgent(provider=mock)
    result = agent.review({"chain": {}, "plan": {}, "report": {}})
    assert result["consistent"] is True
    assert result["overall_assessment"] == "all artifacts align"


def test_review_flags_inconsistency():
    mock = MockProvider(responses={
        "default": '{"consistent": false, "findings": ["chain targets h1 but plan isolates h2"], "overall_assessment": "mismatch"}'
    })
    agent = ReviewerAgent(provider=mock)
    result = agent.review({"chain": {}, "plan": {}})
    assert result["consistent"] is False
    assert len(result["findings"]) == 1
