# date: 2026-08-17
# dev: 陈子毅
"""AP4.2 ir_planner 人机协同（HITL）测试——破坏性操作前确认 + 超时降级。"""
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskHandler,
    AskResponse,
    MockAskHandler,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider

# 含破坏性动作（isolate）的响应计划（Mock LLM 返回）
ISOLATE_PLAN = (
    '{"plan_id":"rp1","actions":[{"action_id":"d1","kind":"isolate",'
    '"target":"h1","rationale":"stop lateral move"}],"confidence":0.9,'
    '"rollback":{"enabled":true,"steps":["reconnect"]}}'
)
# 仅监视（无破坏性）的响应计划
MONITOR_PLAN = (
    '{"plan_id":"rp2","actions":[{"action_id":"m1","kind":"monitor",'
    '"target":"h2","rationale":"watch"}],"confidence":0.7,'
    '"rollback":{"enabled":false}}'
)


class _SpyHandler(AskHandler):
    """记录是否被调用的提问 handler（用于断言「无需确认时不提问」。"""

    def __init__(self) -> None:
        self.calls = 0

    def ask(self, request):
        self.calls += 1
        return AskResponse(answered=True, answer="确认执行")


def _agent(plan_json: str) -> IRPlannerAgent:
    return IRPlannerAgent(provider=MockProvider(responses={"default": plan_json}))


def test_confirms_destructive_when_human_approves():
    agent = _agent(ISOLATE_PLAN)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="确认执行"))
    plan = agent.plan_response_with_human_check(
        [{"hypothesis": "x", "confidence": 0.8, "technique": "T1021"}], ask_handler=handler
    )
    assert plan.actions[0]["kind"] == "isolate"


def test_downgrades_to_monitor_when_human_denies():
    agent = _agent(ISOLATE_PLAN)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="降级为仅监控"))
    plan = agent.plan_response_with_human_check(
        [{"hypothesis": "x", "confidence": 0.8, "technique": "T1021"}], ask_handler=handler
    )
    assert plan.actions[0]["kind"] == "monitor"


def test_timeout_downgrades_to_monitor():
    agent = _agent(ISOLATE_PLAN)
    handler = MockAskHandler(simulate_timeout=True)
    plan = agent.plan_response_with_human_check(
        [{"hypothesis": "x", "confidence": 0.8, "technique": "T1021"}], ask_handler=handler
    )
    assert plan.actions[0]["kind"] == "monitor"


def test_cancels_returns_empty_actions():
    agent = _agent(ISOLATE_PLAN)
    handler = MockAskHandler(response=AskResponse(answered=True, answer="取消执行"))
    plan = agent.plan_response_with_human_check(
        [{"hypothesis": "x", "confidence": 0.8, "technique": "T1021"}], ask_handler=handler
    )
    assert plan.actions == []


def test_no_ask_when_no_destructive_action():
    agent = _agent(MONITOR_PLAN)
    spy = _SpyHandler()
    plan = agent.plan_response_with_human_check(
        [{"hypothesis": "x", "confidence": 0.8, "technique": "T1021"}], ask_handler=spy
    )
    # 无破坏性动作：不应暂停提问，直接返回原计划
    assert spy.calls == 0
    assert plan.actions[0]["kind"] == "monitor"
