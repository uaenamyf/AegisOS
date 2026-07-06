# date: 2026-06-27
# dev: myf
"""拓扑图控制器。

提供 ``GET /graph`` 端点，返回当前 Agent 协作拓扑图的节点与边，
用于前端可视化与运维监控。
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from backend.core.composition import GraphServiceDep
from backend.schemas import GraphResponse

# 拓扑图路由器，统一前缀 /graph，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    service: GraphServiceDep,
) -> GraphResponse:
    """获取当前拓扑图。

    从图服务读取内存中的图缓存，并将节点与边序列化为字典/列表形式。

    Args:
        service: 图服务依赖，维护基于事件总线刷新的图缓存。

    Returns:
        包含 ``nodes`` 与 ``edges`` 字段的响应对象。``nodes`` 为
        节点 ID 到节点字典的映射，``edges`` 为边字典列表。
    """
    graph = await service.get_graph()
    # 节点以 ID 为键、节点 dataclass 转字典为值
    nodes = {nid: asdict(node) for nid, node in graph.nodes.items()}
    # 边直接展平为字典列表
    edges = [asdict(e) for e in graph.edges]
    return GraphResponse(nodes=nodes, edges=edges)
