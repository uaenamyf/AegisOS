// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/replay/ReplayView.tsx，回放时间线占位

import { useAppStore } from "@/lib/store";

export function ReplayView() {
  const events = useAppStore((s) => s.events);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Replay</h2>
        <p className="view__desc">
          Deterministic event-stream replay timeline with playback controls and
          state snapshots.
        </p>
      </header>

      <div className="view__body view__empty">
        {events.length === 0 ? (
          <p className="view__empty-text">
            No events captured. Replay becomes available once the event stream
            is active.
          </p>
        ) : (
          <ul className="view__timeline">
            {events.map((e) => (
              <li key={e.event_id ?? `${e.event_type}-${e.timestamp}`} className="timeline__item">
                <span className="timeline__type">{e.event_type}</span>
                {e.task_id ? (
                  <span className="timeline__task">{e.task_id}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
