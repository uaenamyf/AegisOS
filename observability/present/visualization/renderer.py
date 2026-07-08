# date: 2026-07-07
# dev: myf
# changelog: H5.5 新建可视化——ChartGenerator 图表数据 + GraphRenderer 拓扑图数据 + DashboardAssembler 仪表盘聚合
"""数据可视化 —— 为前端生成图表/图谱/仪表盘的可渲染数据。

本模块实现 :class:`ChartGenerator` / :class:`GraphRenderer` / :class:`DashboardAssembler`，
将 :class:`MetricsCollector` / :class:`BenchmarkReport` / :class:`EvaluationReport` /
:class:`Timeline` 的数据转换为前端可直接渲染的 JSON 结构。

设计要点：
    - **ChartGenerator**：从指标生成折线图 / 柱状图 / 饼图数据（ECharts 兼容格式）。
    - **GraphRenderer**：从 ``protocol.Graph`` 或攻击链生成节点-边数据（React Flow 兼容）。
    - **DashboardAssembler**：聚合监控/基准/评测/回放数据为综合仪表盘。
    - 不渲染 HTML/SVG，只生成数据结构（前端负责实际渲染）。

与现有架构的关系：
    - 实现 :class:`observability.api.VisualizationAPI` Protocol。
    - 消费 :class:`MetricsCollector` / :class:`BenchmarkReport` /
      :class:`EvaluationReport` / :class:`Timeline` 的产出。
    - 输出格式兼容 ECharts（图表）与 React Flow（图谱）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from protocol.cyber import AttackChain
from protocol.graph import Graph


@dataclass
class ChartData:
    """单个图表的数据结构（ECharts 兼容）。

    Attributes:
        title: 图表标题。
        chart_type: 图表类型（``"line"`` / ``"bar"`` / ``"pie"``）。
        categories: X 轴分类列表。
        series: 数据系列列表，每个含 ``name`` 与 ``data``。
    """

    title: str = ""
    chart_type: str = "line"
    categories: list[str] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChartGenerator:
    """图表数据生成器 —— 从指标生成 ECharts 兼容数据。

    实现 :class:`observability.api.VisualizationAPI` 的图表部分。
    """

    @staticmethod
    def agent_latency_chart(metrics_collector: Any) -> ChartData:
        """生成 Agent 延迟柱状图数据。

        Args:
            metrics_collector: :class:`MetricsCollector` 实例。

        Returns:
            :class:`ChartData`（柱状图）。
        """
        dashboard = metrics_collector.get_dashboard()
        agents = dashboard.get("agents", {})
        categories = list(agents.keys())
        data = [agents[a].get("latency_ms_avg", 0) for a in categories]
        return ChartData(
            title="Agent 平均延迟（毫秒）",
            chart_type="bar",
            categories=categories,
            series=[{"name": "延迟(ms)", "data": data}],
        )

    @staticmethod
    def agent_success_rate_chart(metrics_collector: Any) -> ChartData:
        """生成 Agent 成功率饼图数据。

        Args:
            metrics_collector: :class:`MetricsCollector` 实例。

        Returns:
            :class:`ChartData`（饼图）。
        """
        dashboard = metrics_collector.get_dashboard()
        agents = dashboard.get("agents", {})
        categories = list(agents.keys())
        data = [
            {"name": a, "value": agents[a].get("success_rate", 0) * 100}
            for a in categories
        ]
        return ChartData(
            title="Agent 成功率（%）",
            chart_type="pie",
            categories=categories,
            series=[{"name": "成功率", "data": data}],
        )

    @staticmethod
    def benchmark_latency_chart(benchmark_report: Any) -> ChartData:
        """生成基准测试延迟柱状图。

        Args:
            benchmark_report: :class:`BenchmarkReport` 实例。

        Returns:
            :class:`ChartData`。
        """
        stats = benchmark_report.case_stats
        categories = [s.case_name for s in stats]
        avg_data = [s.latency_avg_ms for s in stats]
        max_data = [s.latency_max_ms for s in stats]
        return ChartData(
            title="基准测试延迟（毫秒）",
            chart_type="bar",
            categories=categories,
            series=[
                {"name": "平均延迟", "data": avg_data},
                {"name": "最大延迟", "data": max_data},
            ],
        )

    @staticmethod
    def evaluation_radar_chart(evaluation_report: Any) -> ChartData:
        """生成 5 维度评测雷达图数据。

        Args:
            evaluation_report: :class:`EvaluationReport` 实例。

        Returns:
            :class:`ChartData`（雷达图）。
        """
        dims = evaluation_report.dimensions
        categories = [d.dimension for d in dims]
        data = [round(d.score, 2) for d in dims]
        return ChartData(
            title="5 维度评测雷达图",
            chart_type="radar",
            categories=categories,
            series=[{"name": evaluation_report.run_id, "data": data}],
        )


@dataclass
class GraphData:
    """图谱数据结构（React Flow 兼容）。

    Attributes:
        nodes: 节点列表，每个含 ``id`` / ``label`` / ``type`` / ``data``。
        edges: 边列表，每个含 ``source`` / ``target`` / ``label``。
    """

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}


class GraphRenderer:
    """图谱数据生成器 —— 从拓扑图或攻击链生成 React Flow 兼容数据。

    实现 :class:`observability.api.VisualizationAPI` 的图谱部分。
    """

    @staticmethod
    def render_topology(graph: Graph) -> GraphData:
        """渲染拓扑图为 React Flow 节点-边数据。

        Args:
            graph: :class:`protocol.graph.Graph` 实例。

        Returns:
            :class:`GraphData`。
        """
        nodes = []
        for node_id, node in graph.nodes.items():
            nodes.append(
                {
                    "id": node_id,
                    "label": node.name or node_id,
                    "type": node.kind.value,
                    "data": {
                        "capabilities": node.capabilities,
                        "status": node.status,
                        "success_rate": node.success_rate,
                    },
                }
            )
        edges = []
        for edge in graph.edges:
            edges.append(
                {
                    "source": edge.src,
                    "target": edge.dst,
                    "label": f"w={edge.weight:.2f}",
                }
            )
        return GraphData(nodes=nodes, edges=edges)

    @staticmethod
    def render_attack_chain(chain: AttackChain) -> GraphData:
        """渲染攻击链为 DAG 节点-边数据。

        将 AttackChain 的每个 AttackStep 渲染为节点，按步骤顺序连成链。

        Args:
            chain: :class:`protocol.cyber.AttackChain` 实例。

        Returns:
            :class:`GraphData`。
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        prev_id: str | None = None
        for i, step in enumerate(chain.steps):
            node_id = step.step_id or f"step-{i}"
            nodes.append(
                {
                    "id": node_id,
                    "label": f"{step.technique}\n{step.from_asset}→{step.to_asset}",
                    "type": "attack_step",
                    "data": {
                        "technique": step.technique,
                        "from_asset": step.from_asset,
                        "to_asset": step.to_asset,
                        "success": step.success,
                    },
                }
            )
            if prev_id is not None:
                edges.append({"source": prev_id, "target": node_id, "label": ""})
            prev_id = node_id
        # 目标节点
        if chain.target:
            target_id = f"target-{chain.chain_id}"
            nodes.append(
                {
                    "id": target_id,
                    "label": f"目标\n{chain.target}",
                    "type": "target",
                    "data": {"target": chain.target},
                }
            )
            if prev_id is not None:
                edges.append({"source": prev_id, "target": target_id, "label": "到达"})
        return GraphData(nodes=nodes, edges=edges)


class DashboardAssembler:
    """仪表盘聚合器 —— 聚合监控/基准/评测/回放为综合仪表盘。

    实现 :class:`observability.api.VisualizationAPI` 的仪表盘部分。
    """

    @staticmethod
    def assemble(
        metrics_collector: Any | None = None,
        benchmark_report: Any | None = None,
        evaluation_report: Any | None = None,
        timeline: Any | None = None,
    ) -> dict[str, Any]:
        """聚合多个数据源为综合仪表盘数据。

        Args:
            metrics_collector: 可选的 :class:`MetricsCollector`。
            benchmark_report: 可选的 :class:`BenchmarkReport`。
            evaluation_report: 可选的 :class:`EvaluationReport`。
            timeline: 可选的 :class:`Timeline`。

        Returns:
            含 ``monitor`` / ``benchmark`` / ``evaluation`` / ``replay`` /
            ``charts`` / ``graphs`` 的综合仪表盘字典。
        """
        dashboard: dict[str, Any] = {}
        charts: list[dict[str, Any]] = []

        # 监控面板
        if metrics_collector is not None:
            dashboard["monitor"] = metrics_collector.get_dashboard()
            charts.append(ChartGenerator.agent_latency_chart(metrics_collector).to_dict())
            charts.append(ChartGenerator.agent_success_rate_chart(metrics_collector).to_dict())

        # 基准测试
        if benchmark_report is not None:
            dashboard["benchmark"] = benchmark_report.to_dict()
            charts.append(ChartGenerator.benchmark_latency_chart(benchmark_report).to_dict())

        # 评测
        if evaluation_report is not None:
            dashboard["evaluation"] = evaluation_report.to_dict()
            charts.append(ChartGenerator.evaluation_radar_chart(evaluation_report).to_dict())

        # 回放时间线
        if timeline is not None:
            entries = timeline.entries()
            dashboard["replay"] = {
                "total_events": len(entries),
                "attack_chain_view": timeline.get_attack_chain_view(),
                "timeline": [e.to_dict() for e in entries],
            }

        dashboard["charts"] = charts
        return dashboard


class VisualizationService:
    """可视化服务 —— 实现 :class:`observability.api.VisualizationAPI`。

    聚合 ChartGenerator / GraphRenderer / DashboardAssembler，提供统一 ``render`` 入口。
    """

    def render(self, data: dict[str, Any], view: str = "default") -> Any:
        """根据 view 类型渲染数据。

        Args:
            data: 输入数据，含 ``metrics_collector`` / ``benchmark_report`` /
                ``evaluation_report`` / ``timeline`` / ``graph`` / ``chain`` 等。
            view: 视图类型（``"dashboard"`` / ``"topology"`` / ``"attack_chain"`` /
                ``"latency_chart"`` / ``"radar_chart"``）。

        Returns:
            渲染结果字典。
        """
        if view == "dashboard":
            return DashboardAssembler.assemble(
                metrics_collector=data.get("metrics_collector"),
                benchmark_report=data.get("benchmark_report"),
                evaluation_report=data.get("evaluation_report"),
                timeline=data.get("timeline"),
            )
        if view == "topology":
            return GraphRenderer.render_topology(data.get("graph", Graph())).to_dict()
        if view == "attack_chain":
            return GraphRenderer.render_attack_chain(
                data.get("chain", AttackChain(chain_id=""))
            ).to_dict()
        if view == "latency_chart":
            mc = data.get("metrics_collector")
            return ChartGenerator.agent_latency_chart(mc).to_dict() if mc else {}
        if view == "radar_chart":
            er = data.get("evaluation_report")
            return ChartGenerator.evaluation_radar_chart(er).to_dict() if er else {}
        return {}
