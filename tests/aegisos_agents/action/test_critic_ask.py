# date: 2026-08-17
# dev: 陈子毅
"""AP4.3 critic 人机协同（HITL）测试——严重度阈值请求人工复核 + 超时降级。"""
from aegisos_agents.action.critic.agent import CriticAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskHandler,
    AskResponse,
    MockAskHandler,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider

HIGH = '{"valid":false,"issues":["missing step"],"severity":"high","suggestion":"fix"}'
LOW = '{"valid":true,"issues":[],"severity":"low","suggestion":""}'


class _SpyHandler(AskHandler):
    """记录是否被调用的提问 handler。"""

    def __init__(self) -> None:
        self.calls = 0

    def ask(self, request):
        self.calls += 1
        return AskResponse(answered=True, answer="确认结论")


def _agent(plan_json: str) -> CriticAgent:
    return CriticAgent(provider=MockProvider(responses={"default": plan_json}))


def test_asks_when_high_severity():
    agent = _agent(HIGH)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="确认结论"))
    result = agent.critique_with_human_check({"chain_id": "c1"}, ask_handler=handler)
    assert result["_human_check"]["answered"] is True
    assert result["_human_check"]["answer"] == "确认结论"


def test_no_ask_when_low_severity():
    agent = _agent(LOW)
    spy = _SpyHandler()
    result = agent.critique_with_human_check({"chain_id": "c1"}, ask_handler=spy)
    assert spy.calls == 0
    assert "未触发阈值" in result["_human_check"]["answer"]


def test_escalates_when_human_requests():
    agent = _agent(HIGH)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="人工升级"))
    result = agent.critique_with_human_check({"chain_id": "c1"}, ask_handler=handler)
    assert result["_human_check"].get("escalated") is True


def test_timeout_confirms_conclusion():
    agent = _agent(HIGH)
    handler = MockAskHandler(simulate_timeout=True)
    result = agent.critique_with_human_check({"chain_id": "c1"}, ask_handler=handler)
    assert result["_human_check"]["timeout"] is True
    assert result["_human_check"]["answer"] == "确认结论"
