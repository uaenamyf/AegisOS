// date: 2026-09-13
// dev: OpenSquilla
// changelog: 新增记忆子系统面板——展示分层记忆/检查点/快照/持久化/向量通道统计

import { useEffect, useState } from "react";
import { memoryApi, type MemoryStats } from "@/services/api/memory";

const POLL_MS = 5000;

/** 记忆层 → 中文名 + 说明，用于面板展示 */
const LAYERS: Array<{ key: keyof Omit<MemoryStats, "recent_decisions">; label: string; desc: string }> = [
  { key: "working_sessions", label: "工作记忆", desc: "当前会话上下文栈" },
  { key: "episodic_total", label: "情景记忆", desc: "跨会话决策经验(长期)" },
  { key: "semantic_total", label: "语义记忆", desc: "ATT&CK/CVE 知识库" },
  { key: "vector_total", label: "向量记忆", desc: "语义相似度索引" },
  { key: "archive_total", label: "归档记忆", desc: "冷数据长期存储" },
  { key: "checkpoint_total", label: "检查点", desc: "任务中断恢复点" },
  { key: "snapshot_total", label: "快照", desc: "全局时间点固化" },
];

export function MemoryPanel() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const s = await memoryApi.stats();
        if (!cancelled) {
          setStats(s);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    void load();
    const timer = window.setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="memory-panel">
      <h3 className="view__section-title">
        记忆子系统
        {stats?.persisted ? (
          <span className="badge badge--succeeded">已落盘</span>
        ) : (
          <span className="badge">内存态</span>
        )}
        {stats?.auto_embed ? (
          <span className="badge badge--running">向量通道</span>
        ) : null}
      </h3>
      {error ? (
        <p className="view__empty-text">记忆统计加载失败：{error}</p>
      ) : !stats ? (
        <p className="view__empty-text">加载记忆统计中…</p>
      ) : (
        <div className="memory-panel__grid">
          {LAYERS.map(({ key, label, desc }) => (
            <div key={key} className="memory-panel__cell">
              <div className="memory-panel__value">{stats[key]}</div>
              <div className="memory-panel__label">{label}</div>
              <div className="memory-panel__desc">{desc}</div>
            </div>
          ))}
          {stats.recent_decisions && stats.recent_decisions.length > 0 && (
            <div className="memory-panel__recent">
              <div className="memory-panel__label">最近决策经验</div>
              <ul className="view__list">
                {stats.recent_decisions.slice(0, 3).map((d, i) => (
                  <li key={i} className="view__list-item">
                    {String(d.summary ?? d.task_id ?? `决策 ${i + 1}`).slice(0, 80)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}