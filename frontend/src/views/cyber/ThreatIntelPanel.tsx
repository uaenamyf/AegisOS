// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 ThreatIntelPanel——ATT&CK 威胁情报查询面板

import { useCallback, useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";

/**
 * 威胁情报面板。
 *
 * 展示 ATT&CK 技战术映射：技术 ID、子技术、战术、检测建议、
 * 缓解措施和风险等级。支持按战术过滤。
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

  const fetchTechniques = useCallback(
    async (tactic?: string) => {
      setCyberLoading(true);
      setCyberError(null);
      try {
        const tech = await cyberApi.getAttackTechniques(
          tactic === "All" ? undefined : tactic,
        );
        setThreatIntel(tech);
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

      {/* Stats */}
      <div className="cyber-panel__stats">
        <span className="cyber-stat">
          <span className="cyber-stat__value">{threatIntel.length}</span>
          <span className="cyber-stat__label">techniques</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">
            {threatIntel.filter((t) => t.risk_level === "critical").length}
          </span>
          <span className="cyber-stat__label">critical</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">
            {threatIntel.filter((t) => t.risk_level === "high").length}
          </span>
          <span className="cyber-stat__label">high</span>
        </span>
      </div>

      {/* Techniques table */}
      {threatIntel.length === 0 ? (
        <p className="cyber-panel__empty">
          {cyberLoading ? "Loading…" : "No threat intel data."}
        </p>
      ) : (
        <div className="cyber-table cyber-table--intel">
          {threatIntel.map((tech) => (
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
