// date: 2026-09-14
// dev: OpenSquilla
// R21: Graph + Canvas 合并为「任务图 TaskMap」——同一画布承载两类数据流：
//   Chat 模式（对话任务流）：任务 DAG + 底部对话记忆条，随新问题实时刷新；
//   Cyber Defense 模式（演练流）：红/蓝/紫轮次图 + 历史演练回看，新一轮演练整体替换刷新。
// 点击节点 → 右侧检视面板查看该 Agent 的输入/输出（低代码平台风格）。

import { useEffect, useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import { taskApi } from "@/services/api/tasks";
import { graphService } from "@/services/graph";
import { cyberApi } from "@/services/api/cyber";
import type { DrillMeta, DrillRecord, DrillRoundPhases, Event, Task } from "@/protocol/types";

type MapTone = "red" | "blue" | "purple" | "neutral" | "memory";

interface MapNode {
  id: string;
  label: string;
  sublabel: string;
  tone: MapTone;
  status: string;
  tier?: string;
  detail: {
    kind: string;
    agent?: string;
    input?: string;
    output?: string;
    extra?: Array<[string, string]>;
  };
}

interface MapEdge {
  src: string;
  dst: string;
}

const TONE_COLOR: Record<MapTone, string> = {
  red: "#ef7770",
  blue: "#5b8def",
  purple: "#a78bfa",
  neutral: "#64748b",
  memory: "#a855f7",
};

const TONE_LABEL: Record<MapTone, string> = {
  red: "红队",
  blue: "蓝队",
  purple: "紫队",
  neutral: "系统",
  memory: "记忆",
};

const SNAPSHOT_KEY = "aegis.cyber-drill.snapshot";

function statusLabel(status: string): string {
  return (
    {
      pending: "待处理",
      running: "执行中",
      succeeded: "已完成",
      failed: "失败",
      cancelled: "已取消",
      converged: "已收敛",
    } as Record<string, string>
  )[status] || status;
}

function compact(value: unknown, limit = 240): string {
  if (value == null) return "—";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

/** 分层布局：BFS 深度分层（源在左，汇在右），层内均匀分布。 */
function layeredLayout(ids: string[], edges: MapEdge[]): Map<string, { x: number; y: number }> {
  const W = 640;
  const H = 400;
  const padX = 90;
  const padY = 52;
  const pos = new Map<string, { x: number; y: number }>();
  if (!ids.length) return pos;

  const depth = new Map<string, number>();
  const incoming = new Map<string, string[]>();
  for (const id of ids) incoming.set(id, []);
  for (const e of edges) {
    if (!ids.includes(e.src) || !ids.includes(e.dst)) continue;
    incoming.get(e.dst)?.push(e.src);
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
      if (!ids.includes(e.dst)) continue;
      seen.add(e.dst);
      depth.set(e.dst, Math.min(depth.get(e.dst) ?? d + 1, d + 1));
      queue.push(e.dst);
    }
  }
  for (const id of ids) if (!depth.has(id)) depth.set(id, 0);

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

// ---- Chat 模式：任务 DAG（含 Chat 发起的演练任务，随对话实时更新） ----
function taskTone(task: Task): MapTone {
  const phase = task.payload?.phase as string | undefined;
  if (phase === "red" || phase === "blue" || phase === "purple") return phase;
  const stage = Number(task.payload?.stage ?? 0);
  if (stage >= 1 && stage <= 4) return "red";
  if (stage >= 5 && stage <= 8) return "blue";
  if (stage >= 9) return "purple";
  return "neutral";
}

function buildChatMap(tasks: Task[], events: Event[]): { nodes: MapNode[]; edges: MapEdge[] } {
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];
  const ids = new Set(tasks.map((t) => t.task_id).filter(Boolean));
  for (const task of tasks) {
    const id = task.task_id ?? "";
    if (!id) continue;
    const tone = taskTone(task);
    const agent = String(task.payload?.agent_id ?? task.payload?.agent ?? "router");
    const tier = String(task.payload?.tier ?? "");
    const activity = events.filter(
      (e) => e.task_id === id || e.payload?.task_id === id,
    );
    const finish = activity.find((e) => e.event_type === "agent.finish");
    const output = task.result?.output ?? task.result ?? finish?.payload?.output;
    nodes.push({
      id,
      label: String(task.goal ?? id),
      sublabel: `${TONE_LABEL[tone]} · ${statusLabel(task.status ?? "pending")}`,
      tone,
      status: task.status ?? "pending",
      tier: tier || undefined,
      detail: {
        kind: "任务",
        agent,
        input: String(task.goal ?? id),
        output: output ? compact(output) : "等待 Agent 输出…",
        extra: [
          ["任务 ID", id],
          ["优先级", `P${task.priority ?? 0}`],
          ["延迟预算", `${task.latency_budget ?? 10}s`],
          ["依赖", (task.dependency ?? []).join(", ") || "无"],
          ["事件", `${activity.length} 条`],
        ],
      },
    });
    for (const dep of task.dependency ?? []) {
      if (ids.has(dep)) edges.push({ src: dep, dst: id });
    }
  }
  return { nodes, edges };
}

// ---- Cyber 模式：红/蓝/紫轮次图（每轮 3 节点 + 轮间衔接，随演练整体替换） ----
function stepLine(step: Record<string, any>): string {
  return `${step.step_id ?? "?"} ${step.technique ?? ""} → ${step.to_asset ?? "?"}${step.success ? "" : " ✗"}`;
}

function buildCyberMap(record: DrillRecord): { nodes: MapNode[]; edges: MapEdge[] } {
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];
  for (const round of record.rounds ?? []) {
    const r = round.round;
    const phase = round.phase ?? ({} as DrillRoundPhases);
    const redId = `r${r}-red`;
    const blueId = `r${r}-blue`;
    const purpleId = `r${r}-purple`;
    const redTrace = round.red.agent_trace ?? [];
    const blueTrace = round.blue.agent_trace ?? [];
    const purpleTrace = round.purple.agent_trace ?? [];
    nodes.push(
      {
        id: redId,
        label: `红队 · 第 ${r} 轮`,
        sublabel: `${(round.red.steps ?? []).length} 步 · ${phase.red?.tier ?? "cloud"}`,
        tone: "red",
        status: round.red.ok ? "succeeded" : "failed",
        tier: phase.red?.tier,
        detail: {
          kind: "红队",
          agent: phase.red?.model_id ?? "red-team",
          input: redTrace[0]?.input ?? "侦察目标网段，构建攻击链",
          output:
            (round.red.steps ?? []).map(stepLine).join("\n") ||
            compact(redTrace.at(-1)?.output) ||
            "无攻击步骤",
          extra: [
            ["资产", (round.red.assets ?? []).join(", ") || "—"],
            ["发现漏洞", `${round.red.finding_count ?? 0}`],
            ["执行落点", `${phase.red?.tier ?? "cloud"} · ${phase.red?.model_id ?? ""}`],
          ],
        },
      },
      {
        id: blueId,
        label: `蓝队 · 第 ${r} 轮`,
        sublabel: `${(round.blue.alerts ?? []).length} 告警 · ${phase.blue?.tier ?? "edge"}`,
        tone: "blue",
        status: round.blue.ok ? "succeeded" : "failed",
        tier: phase.blue?.tier,
        detail: {
          kind: "蓝队",
          agent: phase.blue?.model_id ?? "blue-team",
          input: blueTrace[0]?.input ?? "接收红队攻击事件流，检测并响应",
          output:
            compact(round.blue.plan) ||
            compact(blueTrace.at(-1)?.output) ||
            "无响应计划",
          extra: [
            ["告警分诊", `${round.blue.triaged_count ?? 0} 条`],
            ["响应动作", `${(round.blue.plan?.actions ?? []).length ?? 0} 项`],
            ["执行落点", `${phase.blue?.tier ?? "edge"} · ${phase.blue?.model_id ?? ""}`],
          ],
        },
      },
      {
        id: purpleId,
        label: `紫队 · 第 ${r} 轮`,
        sublabel: `${round.purple.new_issue_count ?? 0} 缺口 · ${phase.purple?.tier ?? "cloud"}`,
        tone: "purple",
        status: round.purple.valid ? "succeeded" : "pending",
        tier: phase.purple?.tier,
        detail: {
          kind: "紫队",
          agent: phase.purple?.model_id ?? "purple-team",
          input: purpleTrace[0]?.input ?? "对红蓝对抗产物做一致性审查与收敛判定",
          output:
            compact(round.purple.critique) ||
            compact(purpleTrace.at(-1)?.output) ||
            "无审查意见",
          extra: [
            ["链路有效", round.purple.valid ? "是" : "否"],
            ["新增缺口", `${round.purple.new_issue_count ?? 0}`],
            ["执行落点", `${phase.purple?.tier ?? "cloud"} · ${phase.purple?.model_id ?? ""}`],
          ],
        },
      },
    );
    edges.push({ src: redId, dst: blueId }, { src: blueId, dst: purpleId });
    if (r > 1) edges.push({ src: `r${r - 1}-purple`, dst: redId });
  }
  return { nodes, edges };
}

export function TaskMapView() {
  const mode = useAppStore((s) => s.taskMapMode);
  const setMode = useAppStore((s) => s.setTaskMapMode);
  const selectedKey = useAppStore((s) => s.taskMapSelectedNode);
  const setSelectedKey = useAppStore((s) => s.setTaskMapSelectedNode);
  const tasks = useAppStore((s) => s.tasks);
  const events = useAppStore((s) => s.events);
  const chatMessages = useAppStore((s) => s.chatMessages);
  const setTasks = useAppStore((s) => s.setTasks);

  const [record, setRecord] = useState<DrillRecord | null>(null);
  const [liveDrillId, setLiveDrillId] = useState<string | null>(null);
  const [drillMeta, setDrillMeta] = useState<DrillMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Chat 模式：随任务刷新（5s 轮询 + store 实时推送），保留 Chat 发起的演练任务快照
  useEffect(() => {
    if (mode !== "chat") return;
    const refresh = () => {
      const sessionId = useAppStore.getState().currentSession?.id;
      if (sessionId) {
        void taskApi
          .list(sessionId)
          .then((remote) => {
            const store = useAppStore.getState();
            const localDrill = store.tasks.filter((t) => t.payload?.source === "chat-drill");
            for (let index = 0; index < sessionStorage.length; index += 1) {
              const key = sessionStorage.key(index);
              if (!key?.startsWith("aegis.taskmap.drill.") && !key?.startsWith("aegis.canvas.drill.")) continue;
              try {
                const saved = JSON.parse(sessionStorage.getItem(key) ?? "[]") as Task[];
                localDrill.push(...saved);
              } catch {
                /* 忽略损坏的旧快照 */
              }
            }
            const merged = new Map<string, Task>();
            [...remote, ...localDrill].forEach((t) => {
              if (t.task_id) merged.set(t.task_id, t);
            });
            setTasks([...merged.values()]);
          })
          .catch(() => {});
      }
      void graphService.fetch().catch(() => {});
    };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [mode, setTasks]);

  // Cyber 模式：跟随现场快照（CyberDrillPanel 写入）+ 历史回看
  useEffect(() => {
    if (mode !== "cyber") return;
    let cancelled = false;
    const loadList = async () => {
      try {
        const resp = await cyberApi.listDrills();
        if (!cancelled) setDrillMeta(resp.drills ?? []);
      } catch {
        /* 后端离线等静默 */
      }
    };
    void loadList();

    // 从「演练历史」跳转：直接加载指定记录
    if (selectedKey && selectedKey.startsWith("drill-")) {
      setLoading(true);
      void cyberApi
        .getDrill(selectedKey)
        .then((rec) => {
          if (cancelled) return;
          setRecord(rec);
          setLiveDrillId(selectedKey);
          setError(null);
        })
        .catch(() => {
          if (!cancelled) setError("演练记录加载失败，请稍后重试");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
      return () => {
        cancelled = true;
      };
    }

    // 现场快照跟随：新一轮演练开始时整体替换（不堆叠）
    const loadSnapshotDrill = () => {
      try {
        const raw = sessionStorage.getItem(SNAPSHOT_KEY);
        if (!raw) return;
        const snap = JSON.parse(raw) as { drillId?: string | null };
        if (!snap.drillId) return;
        void cyberApi
          .getDrill(snap.drillId)
          .then((rec) => {
            if (cancelled) return;
            setRecord(rec);
            setLiveDrillId(snap.drillId ?? null);
            setError(null);
          })
          .catch(() => {
            /* 演练尚未落盘时静默，等待下一轮轮询 */
          });
      } catch {
        /* ignore */
      }
    };
    loadSnapshotDrill();
    const timer = window.setInterval(loadSnapshotDrill, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [mode, selectedKey]);

  const map = useMemo(() => {
    if (mode === "chat") return buildChatMap(tasks, events);
    if (record) return buildCyberMap(record);
    return { nodes: [] as MapNode[], edges: [] as MapEdge[] };
  }, [mode, tasks, events, record]);

  const renderIds = useMemo(() => map.nodes.map((n) => n.id), [map.nodes]);
  const renderEdges = useMemo(
    () => map.edges.filter((e) => renderIds.includes(e.src) && renderIds.includes(e.dst)),
    [map.edges, renderIds],
  );
  const layout = useMemo(() => layeredLayout(renderIds, renderEdges), [renderIds, renderEdges]);

  const activeId =
    selectedKey && map.nodes.some((n) => n.id === selectedKey) ? selectedKey : map.nodes[0]?.id ?? null;
  const activeNode = map.nodes.find((n) => n.id === activeId) ?? null;

  const recentChat = useMemo(() => chatMessages.slice(-8), [chatMessages]);

  const pickHistory = (drillId: string) => {
    setSelectedKey(drillId);
  };

  return (
    <section className="view taskmap-view">
      <header className="view__header">
        <div className="taskmap-heading-row">
          <div>
            <span className="eyebrow">统一协作视图 / 低代码检视</span>
            <h2 className="view__title">任务图</h2>
          </div>
          <div className="taskmap-mode-switch" role="tablist" aria-label="任务图模式">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "chat"}
              className={`taskmap-mode-switch__btn${mode === "chat" ? " is-active" : ""}`}
              onClick={() => setMode("chat")}
            >
              Chat 对话流
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "cyber"}
              className={`taskmap-mode-switch__btn${mode === "cyber" ? " is-active" : ""}`}
              onClick={() => setMode("cyber")}
            >
              Cyber Defense 演练流
            </button>
          </div>
        </div>
        <p className="view__desc">
          {mode === "chat"
            ? "对话任务流：每个节点是一个任务，点击查看执行 Agent 的输入/输出。对话记忆保留在底部。"
            : "攻防演练流：每轮红→蓝→紫一条链路，随新一轮演练整体刷新；可从下方选择历史演练回看。"}
        </p>
      </header>

      <div className="view__body">
        {/* 演练流工具栏：历史回看 */}
        {mode === "cyber" ? (
          <div className="taskmap-toolbar">
            <label className="taskmap-toolbar__label" htmlFor="taskmap-history">
              历史演练
            </label>
            <select
              id="taskmap-history"
              className="taskmap-toolbar__select"
              value={liveDrillId ?? ""}
              onChange={(event) => pickHistory(event.target.value)}
              disabled={loading}
            >
              <option value="">— 跟随当前演练 —</option>
              {drillMeta.map((drill) => (
                <option key={drill.drill_id} value={drill.drill_id}>
                  {drill.drill_id} · {drill.rounds_executed} 轮 · {drill.convergence_code}
                </option>
              ))}
            </select>
            {liveDrillId ? (
              <span className="taskmap-live">
                <i />
                {liveDrillId}
              </span>
            ) : null}
          </div>
        ) : null}

        {error ? <div className="taskmap-error">{error}</div> : null}

        {map.nodes.length === 0 ? (
          <div className="view__empty">
            <p className="view__empty-text">
              {mode === "chat"
                ? "还没有可展示的任务节点。先从 Chat 发起一个目标，或发起一场攻防演练。"
                : "暂无演练数据。去 Cyber Defense 开始自动演练，或从上方历史下拉选择一场演练回看。"}
            </p>
          </div>
        ) : (
          <div className="taskmap-layout">
            <div className="taskmap-canvas" role="img" aria-label="任务图">
              <svg viewBox="0 0 640 400" width="100%" height="auto">
                <defs>
                  <marker id="taskmap-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                  </marker>
                </defs>
                {renderEdges.map((edge, index) => {
                  const a = layout.get(edge.src);
                  const b = layout.get(edge.dst);
                  if (!a || !b) return null;
                  const active = activeId === edge.src || activeId === edge.dst;
                  return (
                    <line
                      key={`${edge.src}-${edge.dst}-${index}`}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="#64748b"
                      strokeWidth={active ? 2.4 : 1.4}
                      strokeDasharray={mode === "cyber" ? undefined : "none"}
                      markerEnd="url(#taskmap-arrow)"
                      opacity={active ? 0.95 : 0.45}
                    />
                  );
                })}
                {map.nodes.map((node) => {
                  const p = layout.get(node.id);
                  if (!p) return null;
                  const color = TONE_COLOR[node.tone];
                  const active = activeId === node.id;
                  const running = node.status === "running" || node.status === "active";
                  const w = Math.max(96, Math.min(170, node.label.length * 8 + 30));
                  const h = 44;
                  return (
                    <g
                      key={node.id}
                      className={`taskmap-node${active ? " is-selected" : ""}`}
                      onClick={() => setSelectedKey(node.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <rect
                        x={p.x - w / 2}
                        y={p.y - h / 2}
                        width={w}
                        height={h}
                        rx={8}
                        fill="rgba(16, 24, 32, 0.92)"
                        stroke={color}
                        strokeWidth={active ? 2.5 : running ? 2 : 1.2}
                      />
                      <circle cx={p.x - w / 2 + 11} cy={p.y - 12} r={4} fill={color} />
                      <text x={p.x - w / 2 + 20} y={p.y - 9} className="taskmap-node__label">
                        {node.label.length > 16 ? `${node.label.slice(0, 16)}…` : node.label}
                      </text>
                      <text x={p.x - w / 2 + 20} y={p.y + 10} className="taskmap-node__sublabel">
                        {node.sublabel}
                      </text>
                      {node.tier ? (
                        <text x={p.x + w / 2 - 6} y={p.y - 12} textAnchor="end" className="taskmap-node__tier">
                          {node.tier}
                        </text>
                      ) : null}
                    </g>
                  );
                })}
              </svg>
              <div className="taskmap-legend">
                <span><i style={{ background: TONE_COLOR.red }} />红队</span>
                <span><i style={{ background: TONE_COLOR.blue }} />蓝队</span>
                <span><i style={{ background: TONE_COLOR.purple }} />紫队</span>
                <span><i style={{ background: TONE_COLOR.neutral }} />系统</span>
                <em>点击节点查看输入/输出</em>
              </div>
            </div>

            <aside className="taskmap-inspector" role="dialog" aria-modal="false" aria-label="节点输入输出">
              {activeNode ? (
                <>
                  <span className="taskmap-inspector__eyebrow">
                    {TONE_LABEL[activeNode.tone]} · {activeNode.detail.kind}
                  </span>
                  <h3>{activeNode.label}</h3>
                  <code>{activeNode.id}</code>
                  <span className={`badge badge--${activeNode.status}`}>{statusLabel(activeNode.status)}</span>
                  {activeNode.detail.agent ? (
                    <p className="taskmap-inspector__agent">执行 Agent：<b>{activeNode.detail.agent}</b></p>
                  ) : null}
                  <section className="taskmap-inspector__io">
                    <div className="taskmap-io-card taskmap-io-card--input">
                      <span className="taskmap-io-card__tag">输入 INPUT</span>
                      <pre>{activeNode.detail.input ?? "—"}</pre>
                    </div>
                    <div className="taskmap-io-card taskmap-io-card--output">
                      <span className="taskmap-io-card__tag">输出 OUTPUT</span>
                      <pre>{activeNode.detail.output ?? "—"}</pre>
                    </div>
                  </section>
                  {activeNode.detail.extra?.length ? (
                    <dl className="taskmap-inspector__facts">
                      {activeNode.detail.extra.map(([key, value]) => (
                        <div key={key}>
                          <dt>{key}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                </>
              ) : (
                <p className="taskmap-inspector__empty">点击图上的节点查看输入/输出</p>
              )}
            </aside>
          </div>
        )}

        {/* Chat 模式：对话记忆条——对话是记忆的载体，随新问题持续追加 */}
        {mode === "chat" ? (
          <section className="taskmap-chat-strip" aria-label="对话记忆">
            <div className="taskmap-chat-strip__heading">
              <span>对话记忆（最近 {recentChat.length} 条）</span>
              <small>{chatMessages.length} 条总计 · 记忆面板见 Monitor</small>
            </div>
            <div className="taskmap-chat-strip__items">
              {recentChat.length === 0 ? (
                <p className="taskmap-chat-strip__empty">暂无对话，去 Chat 提问吧。</p>
              ) : (
                recentChat.map((message) => (
                  <div className={`taskmap-chat-item taskmap-chat-item--${message.role}`} key={message.id}>
                    <b>{message.role === "user" ? "用户" : message.role === "assistant" ? "Agent" : "系统"}</b>
                    <span>{compact(message.content, 140)}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : null}
      </div>
    </section>
  );
}
