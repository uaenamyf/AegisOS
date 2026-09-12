// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 ThreatIntelPanel——ATT&CK 威胁情报查询面板

import { useCallback, useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import type { ThreatIntel } from "@/protocol/types";

const LAST_CACHE_KEY = "aegis.threatIntel.v2.last";

/**
 * 威胁情报面板。
 *
 * 展示 ATT&CK 技战术映射：技术 ID、子技术、战术、检测建议、
 * 缓解措施和风险等级。支持按战术过滤。
 *
 * R15 增强：文本搜索过滤 + 本地缓存恢复（刷新秒回，离线可用）。
 */

const TACTICS = [
  "All",
  "Initial Access",
  "Execution",
  "Persistence",
  "Discovery",
  "Credential Access",
  "Lateral Movement",
  "Exfiltration",
  "Impact",
];

const riskColor = (level: string): string => {
  switch (level) {
    case "critical": return "danger";
    case "high": return "danger";
    case "medium": return "warning";
    case "low": return "success";
    default: return "warning";
  }
};

export function ThreatIntelPanel() {
  const threatIntel = useAppStore((s) => s.threatIntel);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setThreatIntel = useAppStore((s) => s.setThreatIntel);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [selectedTactic, setSelectedTactic] = useState("All");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [cacheMode, setCacheMode] = useState<string | null>(null);

  // 中断恢复：挂载时若 store 无情报数据，从 localStorage 恢复最近一次查询
  useEffect(() => {
    if (threatIntel.length > 0) return;
    try {
      const raw = localStorage.getItem(LAST_CACHE_KEY);
      if (raw) {
        const snap = JSON.parse(raw) as { tactic: string; data: ThreatIntel[] };
        setThreatIntel(snap.data);
        setSelectedTactic(snap.tactic);
        setCacheMode(snap.tactic);
      }
    } catch {
      /* 缓存损坏时忽略 */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchTechniques = useCallback(
    async (tactic?: string) => {
      setCyberLoading(true);
      setCyberError(null);
      try {
        const tech = await cyberApi.getAttackTechniques(
          tactic === "All" ? undefined : tactic,
        );
        setThreatIntel(tech);
        setCacheMode(null);
        try {
          localStorage.setItem(
            LAST_CACHE_KEY,
            JSON.stringify({ tactic: tactic ?? "All", data: tech }),
          );
        } catch {
          /* 存储配额等异常时忽略 */
        }
      } catch (err) {
        setCyberError(
          err instanceof Error ? err.message : "Failed to fetch threat intel",
        );
      } finally {
        setCyberLoading(false);
      }
    },
    [setThreatIntel, setCyberLoading, setCyberError],
  );

  useEffect(() => {
    void fetchTechniques();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTacticChange = (tactic: string) => {
    setSelectedTactic(tactic);
    void fetchTechniques(tactic);
  };

  const toggleExpand = (techId: string) => {
    setExpandedId(expandedId === techId ? null : techId);
  };

  // R15：文本搜索过滤（技术名 / 编号 / 战术）
  const query = searchTerm.trim().toLowerCase();
  const visible = query
    ? threatIntel.filter((t) =>
        [t.technique, t.technique_id, t.tactic, t.sub_technique]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(query)),
      )
    : threatIntel;

  return (
    <div className="cyber-panel">
      {/* Action bar */}
      <div className="cyber-panel__actions">
        <div className="cyber-tactics">
          {TACTICS.map((tactic) => (
            <button
              key={tactic}
              className={`cyber-tactic${selectedTactic === tactic ? " cyber-tactic--active" : ""}`}
              onClick={() => handleTacticChange(tactic)}
              disabled={cyberLoading}
            >
              {tactic}
            </button>
          ))}
        </div>
        <button
          className="cyber-view__btn cyber-view__btn--small"
          onClick={() => void fetchTechniques(selectedTactic)}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Loading…" : "↻ Refresh"}
        </button>
      </div>

      {/* R15：文本搜索 + 缓存来源 */}
      <div className="cyber-meta">
        <input
          className="cyber-view__textarea cyber-view__textarea--inline cyber-search"
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="🔍 搜索技术名 / 编号 / 战术…"
          disabled={cyberLoading}
        />
        {cacheMode ? (
          <span className="cyber-meta__chip cyber-meta__chip--warn">
            ↻ 已从浏览器缓存恢复（{cacheMode}）
          </span>
        ) : null}
      </div>

      {/* Stats */}
      <div className="cyber-panel__stats">
        <span className="cyber-stat">
          <span className="cyber-stat__value">{visible.length}</span>
          <span className="cyber-stat__label">techniques</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">
            {visible.filter((t) => t.risk_level === "critical").length}
          </span>
          <span className="cyber-stat__label">critical</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">
            {visible.filter((t) => t.risk_level === "high").length}
          </span>
          <span className="cyber-stat__label">high</span>
        </span>
      </div>

      {/* Techniques table */}
      {visible.length === 0 ? (
        <p className="cyber-panel__empty">
          {cyberLoading ? "加载中…" : query ? `无匹配「${searchTerm}」的结果` : "暂无威胁情报数据。"}
        </p>
      ) : (
        <div className="cyber-table cyber-table--intel">
          {visible.map((tech) => (
            <div
              key={tech.technique_id ?? tech.technique}
              className="cyber-table__row cyber-table__row--intel"
              onClick={() => toggleExpand(tech.technique_id ?? tech.technique ?? "")}
            >
              <div className="cyber-intel__summary">
                <span className="cyber-intel__id">{tech.technique_id || "—"}</span>
                <span className="cyber-intel__name">{tech.technique}</span>
                <span className="cyber-intel__tactic">{tech.tactic}</span>
                <span className={`badge badge--${riskColor(tech.risk_level ?? "medium")}`}>
                  {tech.risk_level}
                </span>
                <span className="cyber-intel__expand">
                  {expandedId === (tech.technique_id ?? tech.technique) ? "▲" : "▼"}
                </span>
              </div>
              {expandedId === (tech.technique_id ?? tech.technique) ? (
                <div className="cyber-intel__detail">
                  {tech.sub_technique ? (
                    <div className="cyber-intel__field">
                      <span className="cyber-intel__field-label">Sub-technique</span>
                      <span className="cyber-intel__field-value">{tech.sub_technique}</span>
                    </div>
                  ) : null}
                  {tech.detection ? (
                    <div className="cyber-intel__field">
                      <span className="cyber-intel__field-label">Detection</span>
                      <span className="cyber-intel__field-value">{tech.detection}</span>
                    </div>
                  ) : null}
                  {tech.mitigation ? (
                    <div className="cyber-intel__field">
                      <span className="cyber-intel__field-label">Mitigation</span>
                      <span className="cyber-intel__field-value">{tech.mitigation}</span>
                    </div>
                  ) : null}
                  {tech.refs && tech.refs.length > 0 ? (
                    <div className="cyber-intel__field">
                      <span className="cyber-intel__field-label">References</span>
                      <span className="cyber-intel__field-value">
                        {tech.refs.map((ref: any, i: number) => (
                          <code key={i} className="cyber-intel__ref">{ref}</code>
                        ))}
                      </span>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
