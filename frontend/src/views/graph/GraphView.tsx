// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/graph/GraphView.tsx，动态图可视化占位

import { useAppStore } from "@/lib/store";

export function GraphView() {
  const graph = useAppStore((s) => s.graph);
  const nodeCount = Object.keys(graph.nodes ?? {}).length;
  const edgeCount = (graph.edges ?? []).length;

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Graph</h2>
        <p className="view__desc">
          Dynamic heterogeneous graph visualization. Nodes, edges, weights, and
          entropy rendered with incremental WebGL/Canvas.
        </p>
      </header>

      <div className="view__body view__empty">
        {nodeCount === 0 ? (
          <p className="view__empty-text">
            Graph is empty. Connect agents and tasks to populate the topology.
          </p>
        ) : (
          <div className="view__metrics">
            <div className="metric">
              <span className="metric__value">{nodeCount}</span>
              <span className="metric__label">nodes</span>
            </div>
            <div className="metric">
              <span className="metric__value">{edgeCount}</span>
              <span className="metric__label">edges</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
