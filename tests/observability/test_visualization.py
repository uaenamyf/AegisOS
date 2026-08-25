# date: 2026-07-07
# dev: myf
# changelog: H5.5 可视化单元测试——ChartGenerator/GraphRenderer/DashboardAssembler
"""H5.5 数据可视化单元测试。"""
from __future__ import annotations

from observability.inspect.monitor import MetricsCollector, MetricType
from observability.present.visualization import (
    ChartGenerator,
    DashboardAssembler,
    GraphRenderer,
    VisualizationService,
)
from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph, GraphEdge, GraphNode, NodeKind


def test_render_topology_generates_nodes_and_edges():
    """GraphRenderer 应从 Graph 生成节点和边。"""
    g = Graph()
    g.add_node(GraphNode(node_id="a", kind=NodeKind.Agent, name="agent-a", capabilities=["recon"]))
    g.add_node(GraphNode(node_id="b", kind=NodeKind.Agent, name="agent-b"))
    g.add_edge(GraphEdge(src="a", dst="b", weight=0.8))

    data = GraphRenderer.render_topology(g)

    assert len(data.nodes) == 2
    assert data.nodes[0]["id"] == "a"
    assert data.nodes[0]["type"] == "agent"
    assert len(data.edges) == 1
    assert data.edges[0]["source"] == "a"
    assert data.edges[0]["target"] == "b"


def test_render_attack_chain_generates_dag():
    """GraphRenderer 应从 AttackChain 生成 DAG 节点-边。"""
    chain = AttackChain(
        chain_id="c1",
        target="asset-3",
        steps=[
            AttackStep(step_id="s1", technique="T1110", from_asset="asset-1", to_asset="asset-2", success=True),
            AttackStep(step_id="s2", technique="T1210", from_asset="asset-2", to_asset="asset-3", success=True),
        ],
    )

    data = GraphRenderer.render_attack_chain(chain)

    # 2 步骤节点 + 1 目标节点
    assert len(data.nodes) == 3
    assert data.nodes[0]["type"] == "attack_step"
    assert data.nodes[-1]["type"] == "target"
    # 2 条边（s1→s2, s2→target）
    assert len(data.edges) == 2


def test_chart_generator_agent_latency():
    """ChartGenerator 应从 MetricsCollector 生成延迟柱状图。"""
    mc = MetricsCollector()
    mc.record_metric("agent.latency_ms", 100.0, MetricType.HISTOGRAM, {"agent": "A"})
    mc.record_metric("agent.start_count", 1, MetricType.COUNTER, {"agent": "A"})

    chart = ChartGenerator.agent_latency_chart(mc)

    assert chart.chart_type == "bar"
    assert "Agent" in chart.title or "延迟" in chart.title


def test_chart_generator_evaluation_radar():
    """ChartGenerator 应从 EvaluationReport 生成雷达图。"""
    from observability.measure.evaluation import Evaluator

    evaluator = Evaluator()
    report = evaluator.evaluate(run_id="r1", accuracy=0.9, recall=0.8)

    chart = ChartGenerator.evaluation_radar_chart(report)

    assert chart.chart_type == "radar"
    assert len(chart.categories) == 5


def test_dashboard_assembler_aggregates_sources():
    """DashboardAssembler 应聚合多个数据源。"""
    mc = MetricsCollector()
    mc.record_metric("agent.start_count", 1, MetricType.COUNTER, {"agent": "A"})

    dashboard = DashboardAssembler.assemble(metrics_collector=mc)

    assert "monitor" in dashboard
    assert "charts" in dashboard
    assert len(dashboard["charts"]) >= 1


def test_dashboard_assembler_with_all_sources():
    """聚合全部数据源应含 monitor/benchmark/evaluation/replay。"""
    from observability.inspect.replay import Timeline
    from observability.measure.benchmark import BenchmarkCase, BenchmarkRunner, BenchmarkSuite
    from observability.measure.evaluation import Evaluator
    from protocol.event import Event, EventType
    from protocol.message import NodeRef

    mc = MetricsCollector()
    bench_report = BenchmarkRunner().run_suite(
        BenchmarkSuite(suite_id="s", cases=[BenchmarkCase(name="c", func=lambda: None)], iterations=1)
    )
    eval_report = Evaluator().evaluate(run_id="r", accuracy=0.9)
    timeline = Timeline([Event(event_type=EventType.AgentStart, source=NodeRef("A", "agent"))])

    dashboard = DashboardAssembler.assemble(
        metrics_collector=mc,
        benchmark_report=bench_report,
        evaluation_report=eval_report,
        timeline=timeline,
    )

    assert "monitor" in dashboard
    assert "benchmark" in dashboard
    assert "evaluation" in dashboard
    assert "replay" in dashboard


def test_visualization_service_render_dashboard():
    """VisualizationService.render 应支持 dashboard 视图。"""
    mc = MetricsCollector()
    service = VisualizationService()
    result = service.render({"metrics_collector": mc}, view="dashboard")
    assert "charts" in result


def test_visualization_service_render_topology():
    """VisualizationService.render 应支持 topology 视图。"""
    g = Graph()
    g.add_node(GraphNode(node_id="a", kind=NodeKind.Agent, name="A"))
    service = VisualizationService()
    result = service.render({"graph": g}, view="topology")
    assert "nodes" in result
    assert len(result["nodes"]) == 1


def test_visualization_service_render_attack_chain():
    """VisualizationService.render 应支持 attack_chain 视图。"""
    chain = AttackChain(chain_id="c1", steps=[AttackStep(step_id="s1", technique="T1110")])
    service = VisualizationService()
    result = service.render({"chain": chain}, view="attack_chain")
    assert "nodes" in result
    assert len(result["nodes"]) >= 1
