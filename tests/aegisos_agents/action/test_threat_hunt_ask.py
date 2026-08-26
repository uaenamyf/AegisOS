# date: 2026-08-17
# dev: 陈子毅
"""AP4.4 threat_hunt 人机协同（HITL）测试——不确定时澄清 + 超时降级。"""
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskHandler,
    AskResponse,
    MockAskHandler,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert

# 低置信度假设（触发澄清）
LOW_CONF = '{"hypotheses":[{"hypothesis":"maybe SMB","confidence":0.3,"technique":"T1021"}]}'
# 高置信度假设（无需澄清）
HIGH_CONF = '{"hypotheses":[{"hypothesis":"clear SMB","confidence":0.9,"technique":"T1021"}]}'


class _SpyHandler(AskHandler):
    """记录是否被调用的提问 handler。"""

    def __init__(self) -> None:
        self.calls = 0

    def ask(self, request):
        self.calls += 1
        return AskResponse(answered=True, answer="保持当前假设")


def _agent(plan_json: str) -> ThreatHuntAgent:
    return ThreatHuntAgent(provider=MockProvider(responses={"default": plan_json}))


def test_asks_when_uncertain():
    agent = _agent(LOW_CONF)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="保持当前假设"))
    result = agent.hunt_with_human_check(
        [Alert(alert_id="a1", severity="high", technique="T1110")], ask_handler=handler
    )
    assert len(result) == 1


def test_no_ask_when_confident():
    agent = _agent(HIGH_CONF)
    spy = _SpyHandler()
    result = agent.hunt_with_human_check(
        [Alert(alert_id="a1", severity="high", technique="T1110")], ask_handler=spy
    )
    assert spy.calls == 0
    assert len(result) == 1


def test_narrow_retry_reruns():
    agent = _agent(LOW_CONF)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="缩小范围重试"))
    result = agent.hunt_with_human_check(
        [Alert(alert_id="a1", severity="high", technique="T1110")], ask_handler=handler
    )
    # 缩小范围重试后仍为合法假设列表（Mock 返回同结构）
    assert len(result) == 1
    assert "hypothesis" in result[0]


def test_timeout_keeps_hypotheses():
    agent = _agent(LOW_CONF)
    handler = MockAskHandler(simulate_timeout=True)
    result = agent.hunt_with_human_check(
        [Alert(alert_id="a1", severity="high", technique="T1110")], ask_handler=handler
    )
    assert len(result) == 1
