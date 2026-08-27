// date: 2026-08-27
// dev: ox-alpha
// R11: Graph 视图增强 —— 节点上叠加执行落点徽标 (D/E/C)

import { useAppStore } from "@/lib/store";
import { TierBadge } from "@/components/TierBadge";

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

      <div className="view__body">
        {nodeCount === 0 ? (
          <div className="view__empty">
            <p className="view__empty-text">
              Graph is empty. Connect agents and tasks to populate the topology.
            </p>
          </div>
        ) : (
          <div>
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

            {/* R11: 节点列表 + 执行落点徽标 */}
            <div style={{ marginTop: "1rem" }}>
              <h3 className="view__section-title">节点执行落点</h3>
              <ul className="view__list">
                {Object.entries(graph.nodes ?? {}).map(([id, node]) => {
                  const tier = (node as Record<string, string> | undefined)?.tier ?? "";
                  return (
                    <li key={id} className="view__list-item">
                      <span className="view__list-label">{id}</span>
                      {tier && <TierBadge tier={tier} full />}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}