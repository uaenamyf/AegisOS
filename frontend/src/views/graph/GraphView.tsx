// date: 2026-08-27
// dev: ox-alpha
// R11: Graph 视图增强 —— 节点上叠加执行落点徽标 (D/E/C)

import { useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import { TierBadge } from "@/components/TierBadge";

export function GraphView() {
  const graph = useAppStore((s) => s.graph);
  const setGraph = useAppStore((s) => s.setGraph);
  const nodeCount = Object.keys(graph.nodes ?? {}).length;
  const edgeCount = (graph.edges ?? []).length;
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const nodes = Object.entries(graph.nodes ?? {});
  const filteredNodes = useMemo(
    () => nodes.filter(([id, node]) => `${id} ${(node as Record<string, unknown>)?.name ?? ""}`.toLowerCase().includes(query.toLowerCase())),
    [nodes, query],
  );
  const selectedNode = filteredNodes.find(([id]) => id === selectedId) ?? filteredNodes[0];
  const selectedEdges = (graph.edges ?? []).filter((edge) => edge.src === selectedNode?.[0] || edge.dst === selectedNode?.[0]);

  const loadDemoGraph = () => {
    setGraph({
      nodes: {
        recon: { name: "侦察 Agent", tier: "device", kind: "agent", status: "active" },
        vuln: { name: "漏洞关联", tier: "edge", kind: "agent", status: "active" },
        planner: { name: "攻击规划", tier: "cloud", kind: "agent", status: "active" },
        memory: { name: "长期记忆", tier: "edge", kind: "memory", status: "active" },
      },
      edges: [
        { src: "recon", dst: "vuln", weight: 0.92, entropy: 0.12 },
        { src: "vuln", dst: "planner", weight: 0.84, entropy: 0.24 },
        { src: "planner", dst: "memory", weight: 0.76, entropy: 0.31 },
      ],
    });
  };

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
            <button type="button" className="canvas-demo-cta" onClick={loadDemoGraph}>加载演示拓扑</button>
          </div>
        ) : (
          <div className="graph-workbench">
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
            <div className="graph-toolbar">
              <input aria-label="搜索节点" placeholder="搜索节点" value={query} onChange={(event) => setQuery(event.target.value)} />
              <span>{filteredNodes.length} / {nodeCount} 节点</span>
            </div>
            <div className="graph-workbench__body">
            <div>
              <h3 className="view__section-title">节点执行落点</h3>
              <ul className="view__list">
                {filteredNodes.map(([id, node]) => {
                  const tier = (node as Record<string, string> | undefined)?.tier ?? "";
                  return (
                    <li key={id} className={`view__list-item graph-node-row${selectedNode?.[0] === id ? " graph-node-row--selected" : ""}`} onClick={() => setSelectedId(id)}>
                      <span className="view__list-label">{id}</span>
                      {tier && <TierBadge tier={tier} full />}
                    </li>
                  );
                })}
              </ul>
            </div>
            {selectedNode ? <aside className="graph-inspector">
              <span className="canvas-inspector__eyebrow">NODE DETAIL</span>
              <h3>{(selectedNode[1] as Record<string, string>).name || selectedNode[0]}</h3>
              <code>{selectedNode[0]}</code>
              <p>{selectedEdges.length} 条关联边</p>
              <ul>{selectedEdges.map((edge, index) => <li key={`${edge.src}-${edge.dst}-${index}`}>{edge.src} → {edge.dst} <small>{edge.weight ?? 1}</small></li>)}</ul>
            </aside> : null}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}