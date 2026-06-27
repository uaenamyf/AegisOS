// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 views/monitor/MonitorView.tsx，Agent 状态监控占位

import { useAppStore } from "@/mappers/store";

export function MonitorView() {
  const agents = useAppStore((s) => s.agents);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Monitor</h2>
        <p className="view__desc">
          Real-time agent status panel. Metrics, trust scores, and alerts.
        </p>
      </header>

      <div className="view__body view__empty">
        {agents.length === 0 ? (
          <p className="view__empty-text">
            No agents registered. Agents appear here once they join the swarm.
          </p>
        ) : (
          <ul className="view__list">
            {agents.map((a) => (
              <li key={a.agent_id} className="view__list-item">
                <span className="view__list-label">
                  {a.name}{" "}
                  <span className="view__list-sub">({a.role})</span>
                </span>
                <span className={`badge badge--${a.status ?? "idle"}`}>
                  {a.status ?? "idle"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
