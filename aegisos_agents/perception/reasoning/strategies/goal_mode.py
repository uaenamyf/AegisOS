# date: 2026-07-08
# dev: myf
"""Goal 行动模式 -- 递归目标分解 + 失败重试 + 备选路径。

本模块实现 :class:`GoalMode`，将复杂高层目标递归分解为子目标树，每个
子目标由对应 Agent 执行，失败时自动重试或尝试备选路径，最终将子目标
产出汇聚为完整结果。

与 :class:`PlanMode` 的区别：
    - **PlanMode**（AP1）：单 Agent 两阶段推理（先规划策略再执行），适合
      提升**单个 Agent** 产出的连贯性。
    - **GoalMode**（AP3）：跨 Agent 递归分解，目标 -> 子目标 -> Agent
      执行 -> 失败重试/备选路径 -> 汇聚，适合**超长程复杂任务**。

设计动机：
    - 赛题要求"超长程"能力：攻击链跨数十~数百步，无法由单个 Agent 一次完成。
    - 复杂目标需递归分解为可执行的子目标树（如"攻破内网" -> "侦察外网入口"
      + "利用漏洞获取初始访问" + "横向移动到核心资产"）。
    - 子目标执行可能失败，需要失败重试 + 备选路径策略保障鲁棒性。
    - 与 :class:`CyberOrchestrator` 的固定模板（recon -> vuln -> exploit）
      互补：Goal 模式可动态生成分解树，适应任意目标。

工作流程：
    1. :meth:`decompose` 递归分解目标为子目标树（``GoalNode``）。
    2. :meth:`execute_tree` 按依赖序遍历子目标树：
       a. 对每个子目标，调用绑定的 Agent 执行。
       b. 成功则记录产出，继续下一个子目标。
       c. 失败则重试（最多 ``max_retries`` 次）。
       d. 重试仍失败则尝试 ``fallback`` 备选路径（如有）。
       e. 全部备选路径失败则标记子目标为 ``failed``。
    3. 汇聚所有子目标产出为最终结果字典。

与 :class:`StructuredAgent` 的关系：
    - GoalMode 是混入（mixin）能力，不替代 StructuredAgent 继承链。
    - 实际执行时由外部调用方（如 CyberOrchestrator）传入 agent 执行回调，
      GoalMode 自身不直接调用 LLM，只负责分解 + 调度 + 重试逻辑。

Attributes:
    GoalNode: 子目标树节点。
    GoalResult: 子目标执行结果。
    GoalMode: 混入类，提供递归分解 + 执行树能力。
    create_goal_mode_orchestrator: 工厂函数。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Generic, TypeVar

T = TypeVar("T", bound=Any)


class GoalStatus(StrEnum):
    """子目标执行状态。"""

    Pending = "pending"        # 待执行
    Running = "running"        # 执行中
    Succeeded = "succeeded"  # 成功
    Failed = "failed"        # 失败（重试耗尽）
    Skipped = "skipped"      # 跳过（上游失败导致）


@dataclass
class GoalNode:
    """子目标树节点。

    递归分解后的一层子目标，可包含子节点形成树结构。

    Attributes:
        goal_id: 子目标唯一标识（如 ``"sub-1"``）。
        description: 子目标描述（如 ``"获取 asset-1 的初始访问权限"``）。
        agent_name: 绑定的 Agent 名称（如 ``"exploit_planner"``）。
        children: 子节点列表（递归分解的更细粒度子目标）。
        fallback: 备选路径描述（主路径失败时尝试的替代方案）。
        dependencies: 依赖的子目标 ID 列表（需先完成才能执行本节点）。
        status: 当前执行状态。
        result: 执行产出（成功后填充）。
        retry_count: 已重试次数。
    """

    goal_id: str
    description: str = ""
    agent_name: str = ""
    children: list[GoalNode] = field(default_factory=list)
    fallback: str = ""
    dependencies: list[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.Pending
    result: Any = None
    retry_count: int = 0


@dataclass
class GoalResult:
    """Goal 模式执行结果。

    记录递归分解树的执行状态与所有子目标产出。

    Attributes:
        root_goal: 根目标描述。
        nodes: 全部子目标节点（扁平化后的列表）。
        succeeded: 成功的子目标 ID 列表。
        failed: 失败的子目标 ID 列表。
        outputs: 子目标 ID -> 产出的映射字典。
        overall_success: 整体是否成功（所有必需子目标成功）。
    """

    root_goal: str = ""
    nodes: list[GoalNode] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    overall_success: bool = False


# 默认重试次数
_DEFAULT_MAX_RETRIES = 2

# 场景分解模板（与 Planner 的场景模板对齐，但 GoalMode 的模板可递归展开）
_GOAL_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "cyber_red": [
        {
            "goal_id": "recon",
            "description": "侦察目标网络范围，发现资产清单",
            "agent_name": "recon",
            "dependencies": [],
            "fallback": "使用被动侦察（DNS/OSINT）替代主动扫描",
        },
        {
            "goal_id": "vuln",
            "description": "对发现的资产进行漏洞关联",
            "agent_name": "vuln_correlator",
            "dependencies": ["recon"],
            "fallback": "基于已知 CVE 数据库手动关联",
        },
        {
            "goal_id": "exploit",
            "description": "基于漏洞规划攻击利用链",
            "agent_name": "exploit_planner",
            "dependencies": ["vuln"],
            "fallback": "降级为单步利用（不构建完整链）",
        },
        {
            "goal_id": "lateral",
            "description": "基于攻击链规划横向移动路径",
            "agent_name": "lateral_move",
            "dependencies": ["exploit"],
            "fallback": "仅枚举可达资产，不规划移动路径",
        },
    ],
    "cyber_blue": [
        {
            "goal_id": "detect",
            "description": "对事件流进行入侵检测",
            "agent_name": "detector",
            "dependencies": [],
            "fallback": "基于规则的静态检测替代 AI 检测",
        },
        {
            "goal_id": "triage",
            "description": "对告警进行分诊排序",
            "agent_name": "triage",
            "dependencies": ["detect"],
            "fallback": "按严重度字段直接排序",
        },
        {
            "goal_id": "hunt",
            "description": "基于告警生成威胁狩猎假设",
            "agent_name": "threat_hunt",
            "dependencies": ["triage"],
            "fallback": "基于 ATT&CK 知识库模板生成假设",
        },
        {
            "goal_id": "respond",
            "description": "基于假设规划应急响应计划",
            "agent_name": "ir_planner",
            "dependencies": ["hunt"],
            "fallback": "生成默认隔离+监控响应计划",
        },
    ],
    "generic": [
        {
            "goal_id": "analyze",
            "description": "分析任务目标与约束",
            "agent_name": "",
            "dependencies": [],
            "fallback": "",
        },
        {
            "goal_id": "execute",
            "description": "执行核心逻辑",
            "agent_name": "",
            "dependencies": ["analyze"],
            "fallback": "",
        },
        {
            "goal_id": "verify",
            "description": "校验结果正确性",
            "agent_name": "",
            "dependencies": ["execute"],
            "fallback": "",
        },
    ],
}


class GoalMode(Generic[T]):
    """Goal 行动模式混入 -- 递归目标分解 + 失败重试 + 备选路径。

    为编排器或 Agent 群体提供目标递归分解与执行能力。混入后可调用
    :meth:`decompose` 将目标分解为子目标树，再调用 :meth:`execute_tree`
    按依赖序执行，失败时自动重试或尝试备选路径。

    与 :class:`PlanMode` 的区别：
        - PlanMode 是单 Agent 两阶段推理（LLM 驱动规划 + 执行）。
        - GoalMode 是跨 Agent 编排（递归分解 + 多 Agent 执行 + 重试）。

    使用方式（以 CyberOrchestrator 为例）::

        class CyberOrchestrator(GoalMode[dict]):
            ...
            def run_red_chain_with_goal(self, target_range):
                tree = self.decompose("攻击 " + target_range, scenario="cyber_red")
                executor = self._create_agent_executor()
                result = self.execute_tree(tree, executor)
                return result.outputs

    Attributes:
        _max_retries: 子目标执行失败后的最大重试次数。
    """

    _max_retries: int = _DEFAULT_MAX_RETRIES

    def decompose(
        self,
        goal: str,
        scenario: str = "generic",
        custom_template: list[dict[str, Any]] | None = None,
    ) -> GoalNode:
        """将高层目标递归分解为子目标树。

        根据场景模板将目标分解为有序子目标列表，子目标间通过 dependencies
        字段构成 DAG 依赖图。当前实现为单层分解（模板展开为同级子目标），
        未来可扩展为多级递归（子目标再分解为更细粒度的子子目标）。

        Args:
            goal: 高层目标描述（如 ``"攻击 10.0.0.0/24"``）。
            scenario: 场景名，取值 ``cyber_red`` / ``cyber_blue`` / ``generic``。
            custom_template: 自定义子目标模板列表，覆盖内置模板。每个元素
                是一个 dict，含 ``goal_id`` / ``description`` / ``agent_name``
                / ``dependencies`` / ``fallback`` 键。

        Returns:
            根 :class:`GoalNode`，其 ``children`` 为分解出的子目标列表。

        Raises:
            ValueError: scenario 不在已知模板中且未提供 custom_template。
        """
        # 优先使用自定义模板
        template = (
            custom_template
            if custom_template is not None
            else _GOAL_TEMPLATES.get(scenario)
        )
        if template is None:
            raise ValueError(
                f"Unknown scenario '{scenario}'; "
                f"available: {list(_GOAL_TEMPLATES.keys())}"
            )

        # 构建根节点
        root = GoalNode(
            goal_id="root",
            description=goal,
            agent_name="",
        )

        # 展开模板为子目标节点
        for entry in template:
            child = GoalNode(
                goal_id=entry["goal_id"],
                description=entry.get("description", ""),
                agent_name=entry.get("agent_name", ""),
                fallback=entry.get("fallback", ""),
                dependencies=list(entry.get("dependencies", [])),
            )
            root.children.append(child)

        return root

    def execute_tree(
        self,
        tree: GoalNode,
        executor: Callable[[GoalNode, dict[str, Any]], Any],
        max_retries: int | None = None,
    ) -> GoalResult:
        """按依赖序执行子目标树，失败时重试或尝试备选路径。

        遍历根节点的 children，按 dependencies 拓扑序逐个执行。每个子目标：
            1. 等待所有依赖子目标完成（成功或失败）。
            2. 若依赖全部成功，调用 executor 执行。
            3. 失败则重试（最多 max_retries 次）。
            4. 重试仍失败则标记为 failed，其下游标记为 skipped。
            5. 若该子目标有 fallback 描述，将 fallback 注入下次重试的上下文。

        Args:
            tree: :meth:`decompose` 返回的子目标树。
            executor: 执行回调，签名 ``executor(node, context) -> Any``。
                ``node`` 是 :class:`GoalNode`，``context`` 是上游产出字典
                （``{dep_goal_id: dep_output}``）。返回值为该子目标的产出。
                执行失败时回调应抛出异常。
            max_retries: 子目标失败后的最大重试次数；None 时用默认值。

        Returns:
            :class:`GoalResult`，含全部子目标的执行状态与产出。
        """
        retries = max_retries if max_retries is not None else self._max_retries
        children = list(tree.children)

        # 扁平化所有节点（当前为单层，直接用 children）
        all_nodes: dict[str, GoalNode] = {c.goal_id: c for c in children}
        succeeded: list[str] = []
        failed: list[str] = []
        outputs: dict[str, Any] = {}

        # 按依赖序执行（简单拓扑排序：重复扫描直到全部处理完）
        remaining = list(children)
        while remaining:
            progressed = False
            for node in list(remaining):
                # 检查依赖是否全部处理完（成功或失败）
                deps_resolved = all(
                    d in succeeded or d in failed for d in node.dependencies
                )
                if not deps_resolved:
                    continue

                # 依赖中有失败的 -> 跳过本节点
                dep_failed = [d for d in node.dependencies if d in failed]
                if dep_failed:
                    node.status = GoalStatus.Skipped
                    failed.append(node.goal_id)
                    remaining.remove(node)
                    progressed = True
                    continue

                # 依赖全部成功 -> 执行
                context = {d: outputs.get(d) for d in node.dependencies}
                node.status = GoalStatus.Running

                success = False
                for attempt in range(retries + 1):
                    node.retry_count = attempt
                    try:
                        result = executor(node, context)
                        node.result = result
                        node.status = GoalStatus.Succeeded
                        outputs[node.goal_id] = result
                        succeeded.append(node.goal_id)
                        success = True
                        break
                    except Exception:
                        # 重试时注入 fallback 上下文
                        if attempt < retries and node.fallback:
                            context["_fallback_hint"] = node.fallback
                        continue

                if not success:
                    node.status = GoalStatus.Failed
                    failed.append(node.goal_id)

                remaining.remove(node)
                progressed = True

            if not progressed:
                # 无法推进（可能存在循环依赖），标记剩余为 skipped
                for node in remaining:
                    node.status = GoalStatus.Skipped
                    failed.append(node.goal_id)
                break

        return GoalResult(
            root_goal=tree.description,
            nodes=list(all_nodes.values()),
            succeeded=succeeded,
            failed=failed,
            outputs=outputs,
            overall_success=len(failed) == 0,
        )

    @staticmethod
    def available_scenarios() -> list[str]:
        """返回所有可用的场景模板名。

        Returns:
            场景名列表。
        """
        return list(_GOAL_TEMPLATES.keys())


def create_goal_mode_orchestrator(
    orchestrator_class: type,
    **kwargs: Any,
) -> Any:
    """工厂函数 -- 创建同时继承目标类与 GoalMode 的实例。

    动态构造一个联合子类，让现有编排器类获得 Goal 模式能力，
    无需修改其继承链。

    Args:
        orchestrator_class: 现有编排器类（如 ``CyberOrchestrator``）。
        **kwargs: 透传给 orchestrator_class 构造函数的参数。

    Returns:
        同时具备目标类与 GoalMode 能力的实例。
    """
    joint_name = f"{orchestrator_class.__name__}WithGoal"
    joint_class = type(joint_name, (orchestrator_class, GoalMode), {})
    return joint_class(**kwargs)
