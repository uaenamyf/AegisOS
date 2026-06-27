// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/graph/index.ts，图数据服务：fetch graph 并订阅 GraphUpdate

import { graphApi } from "@/services/api/graph";
import { sseManager } from "@/services/realtime/sse";
import { useAppStore } from "@/mappers/store";
import type { Event, Graph, GraphDiff } from "@/protocol/types";

function applyDiff(diff: GraphDiff): void {
  const store = useAppStore.getState();
  const graph = store.graph;
  const nodes = { ...(graph.nodes ?? {}) };

  for (const node of diff.added_nodes ?? []) {
    if (node.node_id) nodes[node.node_id] = node;
  }
  for (const id of diff.removed_nodes ?? []) {
    delete nodes[id];
  }

  const removed = new Set(
    (diff.removed_edges ?? []).map((e) => `${e.src}->${e.dst}`),
  );
  let edges = (graph.edges ?? []).filter(
    (e) => !removed.has(`${e.src}->${e.dst}`),
  );
  edges = [...edges, ...(diff.added_edges ?? []), ...(diff.updated_edges ?? [])];

  store.setGraph({ nodes, edges });
}

export const graphService = {
  async fetch(): Promise<Graph> {
    const graph = await graphApi.get();
    useAppStore.getState().setGraph(graph);
    return graph;
  },

  subscribe(): () => void {
    return sseManager.on((event: Event) => {
      if (event.event_type === "graph.update") {
        const diff = event.payload?.graph_diff as GraphDiff | undefined;
        if (diff) applyDiff(diff);
      }
    });
  },
};
