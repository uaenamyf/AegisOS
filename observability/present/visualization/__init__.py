# date: 2026-07-07
# dev: myf
# changelog: H5.5 新建 visualization 包——导出 ChartGenerator/GraphRenderer/DashboardAssembler/VisualizationService
"""数据可视化包。

导出图表/图谱/仪表盘数据生成器，供后端 visualization router 与前端视图消费。
输出格式兼容 ECharts（图表）与 React Flow（图谱）。
"""
from .renderer import (
    ChartData,
    ChartGenerator,
    DashboardAssembler,
    GraphData,
    GraphRenderer,
    VisualizationService,
)

__all__ = [
    "ChartData",
    "ChartGenerator",
    "GraphData",
    "GraphRenderer",
    "DashboardAssembler",
    "VisualizationService",
]
