# date: 2026-07-06
# dev: myf
"""任务规划器 —— 将高层目标分解为可执行 DAG 计划。

本模块实现 :class:`Planner`，将一个 ``goal`` 字符串分解为 :class:`protocol.scheduler.Plan`
（含 ``dag`` 依赖图与 ``tasks`` 列表）。当前采用规则模板分解，不调用 LLM，
后续可替换为 ``StructuredAgent[PlanResult]`` 接入 LLM 规划（对齐 R4 路线）。

设计要点：
    - **场景模板**：内置 4 套分解模板：
        - ``cyber_red``：recon -> vuln_correlator -> exploit_planner -> lateral_move
        - ``cyber_blue``：detector -> triage -> threat_hunt -> ir_planner
        - ``cyber_purple``：critic + reviewer（并行，无依赖）
        - ``generic``（默认）：analyze -> execute -> verify
    - **DAG 表示**：``Plan.dag`` 是 ``{node_id: [dep_id, ...]}`` 字典，
      与 :class:`WorkflowEngine` 的 ``WorkflowNode.dependencies`` 对齐。
    - **Task 列表**：每个节点对应一个 :class:`Task`，``goal`` 描述子任务，
      ``dependency`` 列出前驱 task_id。
    - **不调用 LLM**：保持纯算法，便于测试与确定性。

与现有架构的关系：
    - 输出 :class:`protocol.Plan`（不自造并行结构，对齐 04_PROTOCOL_SPEC）。
    - ``Orchestrator`` 将 :class:`Plan` 转换为 ``WorkflowNode`` 字典后
      交给 :class:`WorkflowEngine` 执行。
"""

from __future__ import annotations

from protocol.scheduler import Plan, Task, TaskStatus


# ---- 场景模板定义 ----
# 每个模板是 (node_id, sub_goal_description, explicit_deps) 三元组列表。
# explicit_deps:
#   None  → 链式，依赖前一个节点（默认行为）
#   []    → 无依赖（并行节点，如紫队 critic + reviewer）
#   [...] → 显式依赖列表
_TEMPLATES: dict[str, list[tuple[str, str, list[str] | None]]] = {
    "cyber_red": [
        ("recon", "扫描目标网络范围，发现资产清单", None),
        ("vuln_correlator", "对资产进行漏洞关联，识别可利用漏洞", None),
        ("exploit_planner", "基于漏洞规划攻击链，生成 AttackChain", None),
        ("lateral_move", "基于攻击链规划横向移动路径", None),
    ],
    "cyber_blue": [
        ("detector", "对事件流进行入侵检测，生成告警", None),
        ("triage", "对告警进行分诊，按严重度排序", None),
        ("threat_hunt", "基于告警生成 ATT&CK 威胁狩猎假设", None),
        ("ir_planner", "基于假设规划应急响应计划", None),
    ],
    # 紫队：critic 与 reviewer 并行（均无依赖）
    "cyber_purple": [
        ("critic", "对红队产出进行对抗性批判校验", []),
        ("reviewer", "对全部产出进行跨一致性审查", []),
    ],
    "generic": [
        ("analyze", "分析任务目标与约束", None),
        ("execute", "执行核心逻辑，产出结果", None),
        ("verify", "校验结果正确性与完整性", None),
    ],
}


class Planner:
    """任务规划器 —— 将 goal 分解为 DAG Plan。

    基于内置场景模板分解目标，不调用 LLM。每个场景模板定义一组有序子任务，
    前后项构成依赖链（cyber_purple 例外：并行无依赖）。

    Attributes:
        _default_scenario: 未指定场景时使用的默认模板名。
    """

    def __init__(self, default_scenario: str = "generic") -> None:
        """初始化规划器。

        Args:
            default_scenario: 默认场景模板名，当 :meth:`plan` 未指定
                scenario 时使用。必须是 :data:`_TEMPLATES` 中的键。
        """
        self._default_scenario = default_scenario

    def plan(
        self,
        goal: str,
        scenario: str | None = None,
    ) -> Plan:
        """将目标分解为 DAG 计划。

        根据 scenario 选择模板，将模板中的每个子任务转化为 :class:`Task`，
        并构建 ``dag`` 依赖图。子任务的 ``goal`` 描述具体职责，``dependency``
        按模板顺序链接（构成链式 DAG）。

        Args:
            goal: 高层目标描述（如 ``对 10.0.0.0/24 进行网络防御演练``）。
            scenario: 场景名，None 时用 ``self._default_scenario``。
                可选值：``cyber_red`` / ``cyber_blue`` / ``cyber_purple`` / ``generic``。

        Returns:
            :class:`Plan`，``plan_id`` 自动生成，``goal`` 为传入目标，
            ``dag`` 为 ``{node_id: [dep_id, ...]}``，``tasks`` 为子任务列表。

        Raises:
            ValueError: scenario 不在已知模板中。
        """
        scene = scenario or self._default_scenario
        template = _TEMPLATES.get(scene)
        if template is None:
            raise ValueError(
                f"Unknown scenario '{scene}'; "
                f"available: {list(_TEMPLATES.keys())}"
            )

        # 构建子任务列表与 DAG
        tasks: list[Task] = []
        dag: dict[str, list[str]] = {}
        # node_id -> task_id 映射，供显式 deps 转换为 task_id 列表
        node_to_task: dict[str, str] = {}
        prev_node_id: str | None = None

        for entry in template:
            node_id, sub_goal, explicit_deps = entry
            # explicit_deps: None = 链式（依赖前一个）；[] = 无依赖；[...] = 显式
            if explicit_deps is None:
                deps = [prev_node_id] if prev_node_id is not None else []
            else:
                deps = list(explicit_deps)
            # Task.dependency: 把 node_id 列表映射为 task_id 列表
            task_deps = [node_to_task[d] for d in deps if d in node_to_task]
            task = Task(
                goal=f"[{scene}/{node_id}] {sub_goal} (父目标: {goal})",
                status=TaskStatus.Pending,
                dependency=task_deps,
                priority=0,
            )
            tasks.append(task)
            dag[node_id] = deps
            node_to_task[node_id] = task.task_id
            prev_node_id = node_id

        return Plan(
            goal=goal,
            dag=dag,
            tasks=tasks,
        )

    def available_scenarios(self) -> list[str]:
        """返回所有可用的场景模板名。

        Returns:
            场景名列表。
        """
        return list(_TEMPLATES.keys())
