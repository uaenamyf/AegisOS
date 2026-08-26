# date: 2026-08-17
# dev: 陈子毅
"""Ask 行动模式（人机协同 / HITL）—— 暂停提问 + 超时降级。

AP4：为攻防 Agent 提供「在关键决策点暂停并向人类提问，等待回答；
若无人值守或超时则按安全策略自动降级」的能力。

设计要点：
    - **可注入端口（AskHandler）**：提问/回答的取回逻辑被抽象为
      :class:`AskHandler` 端口，Agent 不直接耦合具体人机通道（WS/SSE/
      终端）。测试中用 :class:`MockAskHandler` 直接给答案或模拟超时；
      生产环境由 backend 注入会阻塞等待人类 WS 回答的 handler。
    - **默认安全降级（AutoAskHandler）**：未注入任何 handler 时，系统
      视为「无人值守」，立即返回超时降级响应，保证攻防链不阻塞、
      且对破坏性/高危决策走保守默认（由调用方在 ``on_timeout`` 指定）。
    - **事件总线透传**：若通过 :meth:`AskMode.set_event_bus` 注入事件总线，
      :meth:`AskMode.ask_human` 会先发布 ``HumanInputRequired``（前端
      ChatView 据此渲染「需要你确认」卡片），回答后发布 ``HumanResponse``。
    - **与 PlanMode/GoalMode 同构**：AskMode 是混入（mixin），不替代
      ``StructuredAgent`` 继承链；Agent 通过多继承获得 ``ask_human`` 能力，
      原有 LLM 调用方法保持不变（向后兼容）。

与 ``PlanMode`` 的关系：
    - PlanMode 的 ``PlanResult``/``PlanStep`` 为局部 Pydantic 类型，Ask 的
      ``AskRequest``/``AskResponse`` 同样为局部 dataclass（不外溢到
      ``protocol/``，避免破坏唯一契约）。

使用方式（以 IRPlannerAgent 为例）::

    class IRPlannerAgent(StructuredAgent[IRPlannerResult], AskMode):
        ...
        def plan_response_with_human_check(self, hypotheses, ask_handler=None):
            plan = self.plan_response(hypotheses)
            # 含破坏性动作时暂停提问，超时降级为仅 monitor
            ...

Attributes:
    AskRequest: 提问请求（含问题/选项/上下文/超时）。
    AskResponse: 人类回答（或超时降级结果）。
    AskHandler: 提问端口（抽象），取回人类回答。
    MockAskHandler: 测试/脚本用，返回预设回答或模拟超时。
    AutoAskHandler: 默认无人值守 handler，立即返回超时降级。
    AskTimeoutError: handler 主动表示超时（ask_human 据此降级）。
    AskMode: 混入类，提供 ``ask_human`` / ``set_ask_handler`` / ``set_event_bus``。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from protocol.event import Event, EventType, NodeRef

# 严重度有序枚举（供 critic 阈值比较复用）
_SEVERITY_ORDER: dict[str, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass
class AskRequest:
    """向人类提问的请求。

    Attributes:
        agent: 发起提问的 Agent 名称（如 ``"IRPlannerAgent"``）。
        question: 自然语言问题（如「计划包含破坏性动作，是否执行？」）。
        options: 候选选项列表（如 ``["确认执行", "降级为仅监控", "取消"]``）；
            空列表表示开放性问题。
        context: 决策上下文（上游产出摘要等），供人类/测试判断。
        timeout: 等待人类回答的超时秒数（仅真实 handler 生效）。
    """

    agent: str = ""
    question: str = ""
    options: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass
class AskResponse:
    """人类对提问的回答（或超时降级结果）。

    Attributes:
        answered: 是否获得人类真实回答（False 表示超时/无人值守降级）。
        answer: 选择的选项或自由文本；降级时为安全默认标记（如 ``"降级为仅监控"``）。
        timeout: 是否因超时/无人值守触发降级。
        rationale: 回答/降级的理由说明。
    """

    answered: bool = False
    answer: str = ""
    timeout: bool = False
    rationale: str = ""


class AskTimeoutError(Exception):
    """提问超时异常。

    AskHandler 在等待人类回答超时可主动抛出，:meth:`AskMode.ask_human`
    捕获后执行 ``on_timeout`` 降级逻辑。
    """


class AskHandler(ABC):
    """提问端口（抽象基类）。

    取回人类对某个 :class:`AskRequest` 的回答。具体实现可对接：
        - 终端输入（CLI 场景）
        - WebSocket（前端 ChatView 提交回答）
        - 预设响应表（测试 / :class:`MockAskHandler`）

    Subclass 只需实现 :meth:`ask`。
    """

    @abstractmethod
    def ask(self, request: AskRequest) -> AskResponse:
        """向人类提问并取回回答。

        Args:
            request: 提问请求，含问题/选项/上下文/超时。

        Returns:
            :class:`AskResponse`；超时应抛 :class:`AskTimeoutError`
            而非返回，便于调用方区分「超时」与「明确回答」。
        """
        raise NotImplementedError


class MockAskHandler(AskHandler):
    """测试/脚本用提问 handler。

    返回预设回答，或主动模拟超时，便于在无真实人机通道时驱动
    HITL 流程测试。

    Attributes:
        _response: 预设回答；非 None 时 ``ask`` 直接返回它。
        _simulate_timeout: 为 True 时 ``ask`` 抛 :class:`AskTimeoutError`。
    """

    def __init__(
        self,
        response: AskResponse | None = None,
        *,
        simulate_timeout: bool = False,
    ) -> None:
        """初始化 Mock handler。

        Args:
            response: 预设回答；传 ``answered=True`` 表示人类已作答。
            simulate_timeout: 为 True 时模拟超时（``ask`` 抛异常）。
        """
        self._response = response
        self._simulate_timeout = simulate_timeout

    def ask(self, request: AskRequest) -> AskResponse:
        """返回预设回答或模拟超时。

        Args:
            request: 提问请求（本实现忽略其内容）。

        Returns:
            预设的 :class:`AskResponse`。

        Raises:
            AskTimeoutError: 当 ``simulate_timeout`` 为 True。
        """
        if self._simulate_timeout:
            raise AskTimeoutError("MockAskHandler simulated timeout")
        # 无预设时默认视为人类已确认（answer 为空字符串）
        if self._response is None:
            return AskResponse(answered=True, answer="", timeout=False)
        return self._response


class AutoAskHandler(AskHandler):
    """默认无人值守 handler —— 立即返回超时降级响应。

    当 Agent 未注入任何 AskHandler 时使用，使系统在「无人类在线」
    时仍保持自治：不阻塞、直接走调用方在 ``on_timeout`` 中指定的
    安全默认（如破坏性动作降级为 monitor）。
    """

    def ask(self, request: AskRequest) -> AskResponse:
        """返回超时降级响应。

        Args:
            request: 提问请求（本实现忽略其内容）。

        Returns:
            ``AskResponse(answered=False, timeout=True)``；``answer``
            由调用方的 ``on_timeout`` 降级逻辑填充。
        """
        return AskResponse(
            answered=False,
            answer="",
            timeout=True,
            rationale="no human handler wired; auto-degraded",
        )


def severity_at_least(severity: str, threshold: str) -> bool:
    """判断 severity 是否达到或超过阈值（供 critic 接入复用）。

    Args:
        severity: 实际严重度（none/low/medium/high/critical）。
        threshold: 阈值严重度。

    Returns:
        当 ``severity`` 等级 ≥ ``threshold`` 时返回 True。未知等级按最低处理。
    """
    return _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER.get(threshold, 0)


class AskMode:
    """Ask 行动模式混入 —— 为人机协同提供暂停提问 + 超时降级能力。

    Agent 多继承本类后，调用 :meth:`ask_human` 即可在决策点暂停并提问。
    模式本身只负责「发布事件 → 取回回答 → 超时降级 → 发布回答」，
    具体取回逻辑委托给注入的 :class:`AskHandler`，安全降级策略由调用方
    通过 ``on_timeout`` 回调指定（保证每类 Agent 的降级语义由 Agent 决定）。

    Attributes:
        _ask_handler: 注入的提问 handler；None 时退化为 :class:`AutoAskHandler`。
        _eventbus: 可选事件总线；非 None 时发布 HumanInputRequired/HumanResponse。
    """

    _ask_handler: AskHandler | None = None
    _eventbus: Any = None

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.1 新增 set_ask_handler/set_event_bus 注入方法
    def set_ask_handler(self, handler: AskHandler) -> None:
        """注入提问 handler（覆盖默认 AutoAskHandler）。

        Args:
            handler: 实现 :class:`AskHandler` 的实例（如对接 WS 的 handler）。
        """
        self._ask_handler = handler

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.1 新增 set_event_bus 注入方法，用于发布 HumanInputRequired/HumanResponse
    def set_event_bus(self, eventbus: Any) -> None:
        """注入事件总线，使 ask_human 发布人机协同事件供前端渲染。

        Args:
            eventbus: 实现 ``publish(event)`` 的事件总线实例（如 ``EventBus``）。
        """
        self._eventbus = eventbus

    def _publish(self, event_type: EventType, agent: str, task_id: str, payload: dict) -> None:
        """向事件总线发布一条事件（总线为空时静默跳过）。

        Args:
            event_type: 事件类型（HumanInputRequired / HumanResponse）。
            agent: 发起方 Agent 名称。
            task_id: 关联任务 ID（可能为 ``""``）。
            payload: 事件负载。
        """
        if self._eventbus is None:
            return
        # duck typing：只依赖 publish(event)，避免反向依赖 planning 层
        event = Event(
            event_type=event_type,
            task_id=task_id,
            source=NodeRef(agent, ""),
            payload=payload,
        )
        self._eventbus.publish(event)

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.1 新增 ask_human——发布 HumanInputRequired → 调 handler → 超时降级 → 发布 HumanResponse
    def ask_human(
        self,
        question: str,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float = 30.0,
        on_timeout: Callable[[AskRequest], AskResponse] | None = None,
        task_id: str = "",
        agent_name: str | None = None,
    ) -> AskResponse:
        """在决策点暂停并向人类提问，等待回答；超时则按 ``on_timeout`` 降级。

        流程：
            1. 组装 :class:`AskRequest` 并发布 ``HumanInputRequired`` 事件
               （前端 ChatView 据此渲染「需要你确认」卡片）。
            2. 调用注入的 :class:`AskHandler.ask` 取回回答；handler 抛
               :class:`AskTimeoutError` 或返回 ``timeout=True`` 均视为超时。
            3. 超时时：若提供 ``on_timeout`` 则调用其产出安全降级响应，
               否则返回默认降级响应（``answered=False, timeout=True``）。
            4. 发布 ``HumanResponse`` 事件（含回答/降级标记），返回响应。

        Args:
            question: 自然语言问题。
            options: 候选选项列表；空/None 表示开放性问题。
            context: 决策上下文（上游产出摘要），供人类/测试判断。
            timeout: 等待人类回答的超时秒数（仅真实 handler 生效）。
            on_timeout: 超时降级回调，签名 ``(request) -> AskResponse``；
                由调用方指定该类 Agent 的安全默认（如破坏性动作降级为 monitor）。
            task_id: 关联任务 ID（用于事件溯源）。
            agent_name: 发起 Agent 名称；None 时用类名。

        Returns:
            :class:`AskResponse`：人类回答，或超时降级后的安全默认。
        """
        options = options or []
        context = context or {}
        agent = agent_name or self.__class__.__name__
        request = AskRequest(
            agent=agent,
            question=question,
            options=options,
            context=context,
            timeout=timeout,
        )

        # 1) 发布「需要人工输入」事件，前端据此暂停并渲染提问卡片
        self._publish(
            EventType.HumanInputRequired,
            agent,
            task_id,
            {"question": question, "options": options, "context": context},
        )

        # 2) 取回回答；handler 未注入时退化为 AutoAskHandler（即时超时降级）
        handler = self._ask_handler or AutoAskHandler()
        timed_out = False
        try:
            response = handler.ask(request)
            if response.timeout:
                timed_out = True
        except AskTimeoutError:
            timed_out = True

        # 3) 超时降级：调用方指定安全默认，否则返回默认降级响应
        if timed_out:
            if on_timeout is not None:
                response = on_timeout(request)
            else:
                response = AskResponse(
                    answered=False, answer="", timeout=True, rationale="ask timed out"
                )

        # 4) 发布「人类回答」事件（含超时降级标记），供前端/可观测消费
        self._publish(
            EventType.HumanResponse,
            agent,
            task_id,
            {
                "answered": response.answered,
                "answer": response.answer,
                "timeout": response.timeout,
                "rationale": response.rationale,
            },
        )
        return response
