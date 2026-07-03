# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 graph 控制器 GET /graph
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from backend.src.composition import GraphServiceDep
from backend.src.controllers.schemas import GraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    service: GraphServiceDep,
) -> GraphResponse:
    graph = await service.get_graph()
    nodes = {nid: asdict(node) for nid, node in graph.nodes.items()}
    edges = [asdict(e) for e in graph.edges]
    return GraphResponse(nodes=nodes, edges=edges)
