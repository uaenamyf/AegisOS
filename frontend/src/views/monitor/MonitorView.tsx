// date: 2026-08-27
// dev: ox-alpha
// R11: Monitor 视图增强 —— 端边云节点面板 + 调度沙盒

import { useAppStore } from "@/lib/store";
import { InfraNodePanel } from "@/components/InfraNodePanel";
import { DispatchSandbox } from "@/components/DispatchSandbox";

export function MonitorView() {
  const agents = useAppStore((s) => s.agents);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Monitor</h2>
        <p className="view__desc">
          端边云资源状态 · Agent 实时监控 · 调度沙盒
        </p>
      </header>

      <div className="view__body" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {/* R11: 端边云节点面板 */}
        <InfraNodePanel />

        {/* R11: 调度沙盒 */}
        <DispatchSandbox />

        {/* 原有 Agent 列表 */}
        <div>
          <h3 className="view__section-title">Agent 列表</h3>
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
      </div>
    </section>
  );
}