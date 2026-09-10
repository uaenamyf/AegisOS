// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/replay/ReplayView.tsx，回放时间线占位

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

export function ReplayView() {
  const events = useAppStore((s) => s.events);
  const setEvents = useAppStore((s) => s.setEvents);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);

  const loadDemoEvents = () => {
    const now = Date.now();
    setEvents([
      { event_id: "demo-1", event_type: "agent.start", task_id: "recon", timestamp: now - 3000 },
      { event_id: "demo-2", event_type: "tool.call", task_id: "recon", timestamp: now - 2000 },
      { event_id: "demo-3", event_type: "agent.finish", task_id: "recon", timestamp: now - 1000 },
      { event_id: "demo-4", event_type: "graph.update", task_id: "vuln", timestamp: now },
    ]);
    setCursor(0);
  };

  useEffect(() => {
    if (!playing || !events.length) return;
    const timer = window.setInterval(() => setCursor((current) => current >= events.length - 1 ? 0 : current + 1), 1200);
    return () => window.clearInterval(timer);
  }, [events.length, playing]);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Replay</h2>
        <p className="view__desc">
          Deterministic event-stream replay timeline with playback controls and
          state snapshots.
        </p>
      </header>

      <div className="view__body view__empty replay-shell">
        {events.length === 0 ? (
          <div>
          <p className="view__empty-text">
            No events captured. Replay becomes available once the event stream
            is active.
          </p>
          <button type="button" className="canvas-demo-cta" onClick={loadDemoEvents}>加载演示回放</button>
          </div>
        ) : (
          <>
          <div className="replay-controls">
            <button type="button" onClick={() => setPlaying((value) => !value)}>{playing ? "暂停" : "播放"}</button>
            <button type="button" onClick={() => setCursor((value) => Math.max(0, value - 1))}>上一步</button>
            <button type="button" onClick={() => setCursor((value) => Math.min(events.length - 1, value + 1))}>下一步</button>
            <input aria-label="回放进度" type="range" min="0" max={Math.max(0, events.length - 1)} value={cursor} onChange={(event) => setCursor(Number(event.target.value))} />
            <span>{cursor + 1} / {events.length}</span>
          </div>
          <ul className="view__timeline">
            {events.map((e, index) => (
              <li key={e.event_id ?? `${e.event_type}-${e.timestamp}`} className={`timeline__item${index === cursor ? " timeline__item--active" : ""}`}>
                <span className="timeline__type">{e.event_type}</span>
                {e.task_id ? (
                  <span className="timeline__task">{e.task_id}</span>
                ) : null}
              </li>
            ))}
          </ul>
          </>
        )}
      </div>
    </section>
  );
}
