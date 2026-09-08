// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/cyber/CyberView.tsx，攻防演练主视图（红/蓝/紫面板 + 威胁情报）
// changelog: 2026-09-04 R5 追加 Drill tab（多轮攻防演练面板）

import { useState, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import { CyberDrillPanel } from "./CyberDrillPanel";
import { RedTeamPanel } from "./RedTeamPanel";
import { BlueTeamPanel } from "./BlueTeamPanel";
import { PurpleTeamPanel } from "./PurpleTeamPanel";
import { ThreatIntelPanel } from "./ThreatIntelPanel";

type TabId = "red" | "blue" | "purple" | "threat" | "drill";

const TABS: { id: TabId; label: string }[] = [
  { id: "red", label: "Red Team" },
  { id: "blue", label: "Blue Team" },
  { id: "purple", label: "Purple Review" },
  { id: "threat", label: "Threat Intel" },
  { id: "drill", label: "Drill" },
];

export function CyberView() {
  const [activeTab, setActiveTab] = useState<TabId>("red");
  const [targetRange, setTargetRange] = useState("10.0.0.0/24");

  const currentRange = useAppStore((s) => s.currentRange);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const cyberError = useAppStore((s) => s.cyberError);
  const setCurrentRange = useAppStore((s) => s.setCurrentRange);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const handleStartRange = useCallback(async () => {
    setCyberLoading(true);
    setCyberError(null);
    try {
      const range = await cyberApi.startRange({ target_range: targetRange });
      setCurrentRange(range);
    } catch (err) {
      setCyberError(err instanceof Error ? err.message : "Failed to start range");
    } finally {
      setCyberLoading(false);
    }
  }, [targetRange, setCurrentRange, setCyberLoading, setCyberError]);

  return (
    <section className="view cyber-view">
      <header className="view__header">
        <h2 className="view__title">Cyber Defense Operations</h2>
        <p className="view__desc">
          Red→Blue→Purple team orchestration with ATT&CK threat intelligence.
          Start a range session, execute attack/defense chains, and review
          cross-artifact consistency.
        </p>
      </header>

      {/* Range controls */}
      <div className="cyber-view__range-bar">
        <input
          className="cyber-view__range-input"
          type="text"
          value={targetRange}
          onChange={(e) => setTargetRange(e.target.value)}
          placeholder="e.g. 10.0.0.0/24"
          disabled={cyberLoading}
        />
        <button
          className="cyber-view__btn cyber-view__btn--primary"
          onClick={() => void handleStartRange()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Starting…" : "Start Range"}
        </button>
        {currentRange ? (
          <span className="cyber-view__range-id">
            Range: <code>{currentRange.range_id}</code>
            <span className={`badge badge--${currentRange.status}`}>
              {currentRange.status}
            </span>
          </span>
        ) : null}
      </div>

      {cyberError ? (
        <div className="cyber-view__error">{cyberError}</div>
      ) : null}

      {/* Tabs */}
      <div className="cyber-view__tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`cyber-view__tab${activeTab === tab.id ? " cyber-view__tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="cyber-view__content">
        {activeTab === "red" && <RedTeamPanel />}
        {activeTab === "blue" && <BlueTeamPanel />}
        {activeTab === "purple" && <PurpleTeamPanel />}
        {activeTab === "threat" && <ThreatIntelPanel />}
        {activeTab === "drill" && <CyberDrillPanel />}
      </div>
    </section>
  );
}
