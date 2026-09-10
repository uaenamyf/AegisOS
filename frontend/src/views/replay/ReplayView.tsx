// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/replay/ReplayView.tsx，回放时间线占位

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import type { Event } from "@/protocol/types";

export function ReplayView() {
  const events = useAppStore((s) => s.events);
  const currentSession = useAppStore((s) => s.currentSession);
  const tasks = useAppStore((s) => s.tasks);
  const setEvents = useAppStore((s) => s.setEvents);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const currentEvent = events[cursor];

  useEffect(() => {
    const sessionId = currentSession?.id;
    if (!sessionId) return;
    void apiClient
      .get<{ timeline: Event[] }>(`/replay/${encodeURIComponent(sessionId)}`)
      .then((response) => {
        if (response.timeline?.length) setEvents(response.timeline);
        else if (tasks.length) {
          setEvents(tasks.flatMap((task) => task.task_id ? [
            { event_id: `${task.task_id}-start`, event_type: "agent.start", task_id: task.task_id, payload: { goal: task.goal, session_id: sessionId }, timestamp: Date.now() },
            ...(task.status === "succeeded" || task.status === "failed" ? [{ event_id: `${task.task_id}-finish`, event_type: "agent.finish", task_id: task.task_id, payload: { output: task.result, session_id: sessionId }, timestamp: Date.now() }] : []),
          ] : []));
        }
      })
      .catch(() => { /* SSE 前端事件仍可用于即时回放 */ });
  }, [currentSession?.id, setEvents, tasks]);

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
        <h2 className="view__title">事件回放</h2>
        <p className="view__desc">
          按时间回看当前会话的 Agent 执行事件与状态变化。
        </p>
      </header>

      <div className="view__body view__empty replay-shell">
        {events.length === 0 ? (
          <div className="replay-empty-state">
          <p className="view__empty-text">
            当前会话还没有可回放事件。开始一次 Chat 任务后，这里会自动记录执行轨迹。
          </p>
          <button type="button" className="canvas-demo-cta" onClick={loadDemoEvents}>加载演示回放</button>
          </div>
        ) : (
          <>
          <div className="view__metrics">
            <div className="metric"><span className="metric__value">{events.length}</span><span className="metric__label">实时事件</span></div>
            <div className="metric"><span className="metric__value">{new Set(events.map((event) => event.task_id).filter(Boolean)).size}</span><span className="metric__label">关联任务</span></div>
          </div>
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
          {currentEvent ? <aside className="replay-detail" aria-label="当前事件详情">
            <span className="canvas-inspector__eyebrow">当前事件</span>
            <h3>{currentEvent.event_type}</h3>
            <dl className="canvas-inspector__facts">
              <div><dt>任务</dt><dd>{currentEvent.task_id ?? "全局事件"}</dd></div>
              <div><dt>来源</dt><dd>{currentEvent.source?.node_id ?? "系统"}</dd></div>
              <div><dt>时间</dt><dd>{currentEvent.timestamp ? new Date(currentEvent.timestamp).toLocaleTimeString() : "—"}</dd></div>
            </dl>
            {currentEvent.payload ? <pre>{JSON.stringify(currentEvent.payload, null, 2)}</pre> : null}
          </aside> : null}
          </>
        )}
      </div>
    </section>
  );
}
