// date: 2026-08-27
// dev: ox-alpha
// R11: Graph 视图增强 —— 节点上叠加执行落点徽标 (D/E/C)
// 2026-09-12: 真图化——SVG 分层布局渲染节点/连线（圆节点 + 带箭头有向边 +
// 权重粗细/熵虚线编码），替代纯列表；保留右侧节点详情。修复"叫 graph 却没有图"。

import { useEffect, useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import { TierBadge } from "@/components/TierBadge";
import { graphService } from "@/services/graph";

type GraphNode = Record<string, any> & { name?: string; kind?: string; status?: string; tier?: string };
type GraphEdge = { src: string; dst: string; weight?: number; entropy?: number };

const KIND_COLOR: Record<string, string> = {
  agent: "#3b82f6",
  task: "#10b981",
  memory: "#a855f7",
  tool: "#f59e0b",
};

function kindOf(node: GraphNode): string {
  return String(node.kind ?? "agent");
}

/** 分层布局：按 BFS 深度分层（源在左，汇在右），层内均匀分布。 */
function layeredLayout(ids: string[], edges: GraphEdge[]): Map<string, { x: number; y: number }> {
  const W = 560;
  const H = 380;
  const padX = 70;
  const padY = 46;
  const pos = new Map<string, { x: number; y: number }>();
  if (ids.length === 0) return pos;

  // BFS 求深度（无入边者为根；环用 seen 防死循环）
  const depth = new Map<string, number>();
  const incoming = new Map<string, string[]>();
  for (const id of ids) incoming.set(id, []);
  for (const e of edges) {
    if (incoming.has(e.dst)) incoming.get(e.dst)!.push(e.src);
  }
  const roots = ids.filter((id) => (incoming.get(id) ?? []).length === 0);
  const queue = [...(roots.length ? roots : [ids[0]])];
  const seen = new Set(queue);
  for (const r of queue) depth.set(r, 0);
  while (queue.length) {
    const cur = queue.shift()!;
    const d = depth.get(cur) ?? 0;
    for (const e of edges) {
      if (e.src !== cur || seen.has(e.dst)) continue;
      // 只连图内节点
      if (!ids.includes(e.dst)) continue;
      seen.add(e.dst);
      depth.set(e.dst, Math.min(depth.get(e.dst) ?? d + 1, d + 1));
      queue.push(e.dst);
    }
  }
  for (const id of ids) if (!depth.has(id)) depth.set(id, 0);

  // 分层
  const layers = new Map<number, string[]>();
  for (const id of ids) {
    const d = depth.get(id) ?? 0;
    layers.set(d, [...(layers.get(d) ?? []), id]);
  }
  const maxDepth = Math.max(...layers.keys(), 0);
  for (const [d, members] of layers) {
    const x = maxDepth === 0 ? W / 2 : padX + (d * (W - 2 * padX)) / maxDepth;
    members.forEach((id, i) => {
      const y = members.length === 1 ? H / 2 : padY + (i * (H - 2 * padY)) / (members.length - 1);
      pos.set(id, { x, y });
    });
  }
  return pos;
}

export function GraphView() {
  const graph = useAppStore((s) => s.graph);
  const tasks = useAppStore((s) => s.tasks);
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
  const selectedEdges = (graph.edges ?? []).filter((edge: GraphEdge) => edge.src === selectedNode?.[0] || edge.dst === selectedNode?.[0]);

  useEffect(() => {
    void (async () => {
      await graphService.fetch().catch(() => {});
      if (!tasks.length) return;
      const latestGraph = useAppStore.getState().graph;
      const nodes = { ...(latestGraph.nodes ?? {}) };
      const edges = [...(latestGraph.edges ?? [])];
      for (const task of tasks) {
        const taskId = task.task_id;
        if (!taskId) continue;
        const agentId = String(task.payload?.agent_id ?? task.payload?.agent ?? "router");
        nodes[agentId] = { ...(nodes[agentId] ?? {}), name: agentId, kind: "agent", status: "active" };
        nodes[taskId] = { ...(nodes[taskId] ?? {}), name: task.goal ?? taskId, kind: "task", status: task.status ?? "pending" };
        if (!edges.some((edge) => edge.src === agentId && edge.dst === taskId)) edges.push({ src: agentId, dst: taskId, weight: 1, entropy: 0 });
      }
      setGraph({ nodes, edges });
    })();
  }, [setGraph, tasks]);

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

  // 布局与渲染数据（只对过滤后的节点作图；边两端都在图内才画）
  const renderIds = useMemo(() => filteredNodes.map(([id]) => id), [filteredNodes]);
  const renderEdges = useMemo(
    () =>
      ((graph.edges ?? []) as GraphEdge[]).filter(
        (e) => renderIds.includes(e.src) && renderIds.includes(e.dst),
      ),
    [graph.edges, renderIds],
  );
  const layout = useMemo(() => layeredLayout(renderIds, renderEdges), [renderIds, renderEdges]);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">协作拓扑</h2>
        <p className="view__desc">
          Agent、任务与记忆节点之间的协作关系、权重和通信熵。
        </p>
      </header>

      <div className="view__body">
        {nodeCount === 0 ? (
          <div className="view__empty">
            <p className="view__empty-text">
              暂无拓扑数据。请先从 Chat 发起任务，系统会自动生成协作关系。
            </p>
            <button type="button" className="canvas-demo-cta" onClick={loadDemoGraph}>加载演示拓扑</button>
          </div>
        ) : (
          <div className="graph-workbench">
            <div className="view__metrics">
              <div className="metric">
                <span className="metric__value">{nodeCount}</span>
                <span className="metric__label">节点</span>
              </div>
              <div className="metric">
                <span className="metric__value">{edgeCount}</span>
                <span className="metric__label">连接</span>
              </div>
            </div>

            <div className="graph-toolbar">
              <input aria-label="搜索节点" placeholder="搜索节点" value={query} onChange={(event) => setQuery(event.target.value)} />
              <span>{filteredNodes.length} / {nodeCount} 节点</span>
            </div>

            {/* 真图：SVG 有向图（分层布局） */}
            <div className="graph-canvas" role="img" aria-label="协作拓扑图">
              <svg viewBox="0 0 560 380" width="100%" height="auto">
                <defs>
                  <marker id="graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                  </marker>
                </defs>
                {renderEdges.map((edge, i) => {
                  const a = layout.get(edge.src);
                  const b = layout.get(edge.dst);
                  if (!a || !b) return null;
                  const weight = Math.min(Math.max(edge.weight ?? 1, 0.1), 1);
                  const entropy = edge.entropy ?? 0;
                  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 18 };
                  const active = selectedNode?.[0] === edge.src || selectedNode?.[0] === edge.dst;
                  return (
                    <g key={`${edge.src}-${edge.dst}-${i}`} className={active ? "graph-edge--active" : "graph-edge"}>
                      <line
                        x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                        stroke="#64748b"
                        strokeWidth={1 + weight * 3}
                        strokeDasharray={entropy > 0.2 ? "6 4" : undefined}
                        markerEnd="url(#graph-arrow)"
                        opacity={active ? 0.95 : 0.45}
                      />
                      <text x={mid.x} y={mid.y} textAnchor="middle" className="graph-edge__label">
                        {weight.toFixed(2)}{entropy > 0 ? ` · H=${entropy.toFixed(2)}` : ""}
                      </text>
                    </g>
                  );
                })}
                {filteredNodes.map(([id, raw]) => {
                  const node = raw as GraphNode;
                  const p = layout.get(id);
                  if (!p) return null;
                  const kind = kindOf(node);
                  const color = KIND_COLOR[kind] ?? "#3b82f6";
                  const status = String(node.status ?? "");
                  const active = selectedNode?.[0] === id;
                  const label = String(node.name ?? id);
                  return (
                    <g
                      key={id}
                      className={`graph-node${active ? " graph-node--selected" : ""}`}
                      onClick={() => setSelectedId(id)}
                    >
                      <circle
                        cx={p.x} cy={p.y} r={active ? 20 : 16}
                        fill={color}
                        stroke={status === "running" || status === "active" ? "#fbbf24" : "#e2e8f0"}
                        strokeWidth={status === "running" || status === "active" ? 3 : 1.5}
                      />
                      <text x={p.x} y={p.y + 4} textAnchor="middle" className="graph-node__initial">
                        {label.slice(0, 2)}
                      </text>
                      <text x={p.x} y={p.y + 34} textAnchor="middle" className="graph-node__label">
                        {label.length > 12 ? `${label.slice(0, 12)}…` : label}
                      </text>
                    </g>
                  );
                })}
              </svg>
              <div className="graph-legend">
                <span><i style={{ background: KIND_COLOR.agent }} />Agent</span>
                <span><i style={{ background: KIND_COLOR.task }} />任务</span>
                <span><i style={{ background: KIND_COLOR.memory }} />记忆</span>
                <span><i style={{ background: KIND_COLOR.tool }} />工具</span>
                <span><em />权重=线宽 · 熵&gt;0.2=虚线 · 黄圈=活跃</span>
              </div>
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
                <span className="canvas-inspector__eyebrow">节点详情</span>
                <h3>{(selectedNode[1] as Record<string, string>).name || selectedNode[0]}</h3>
                <code>{selectedNode[0]}</code>
                <p>{selectedEdges.length} 条关联边</p>
                <ul>{selectedEdges.map((edge: GraphEdge, index: number) => <li key={`${edge.src}-${edge.dst}-${index}`}>{edge.src} → {edge.dst} <small>{edge.weight ?? 1}</small></li>)}</ul>
              </aside> : null}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
