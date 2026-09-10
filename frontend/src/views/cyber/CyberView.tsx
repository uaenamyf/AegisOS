// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/cyber/CyberView.tsx，攻防演练主视图（红/蓝/紫面板 + 威胁情报）
// changelog: 2026-09-04 R5 追加 Drill tab（多轮攻防演练面板）
// changelog: 2026-09-04 R7 头部加运行时模式徽标（mock/真实 LLM 切换）

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { LlmModeBadge } from "./LlmModeBadge";
import { CyberDrillPanel } from "./CyberDrillPanel";
import { RedTeamPanel } from "./RedTeamPanel";
import { BlueTeamPanel } from "./BlueTeamPanel";
import { PurpleTeamPanel } from "./PurpleTeamPanel";
import { ThreatIntelPanel } from "./ThreatIntelPanel";

type TabId = "red" | "blue" | "purple" | "threat" | "drill";

const TABS: { id: TabId; label: string }[] = [
  { id: "red", label: "红队攻击" },
  { id: "blue", label: "蓝队防御" },
  { id: "purple", label: "紫队审查" },
  { id: "threat", label: "威胁情报" },
  { id: "drill", label: "自动演练" },
];

export function CyberView() {
  // 默认落在循环对抗 tab：产品定位是「一键多轮自动对抗」，红/蓝/紫为单链演示
  const [activeTab, setActiveTab] = useState<TabId>("drill");
  const currentRange = useAppStore((s) => s.currentRange);
  const cyberError = useAppStore((s) => s.cyberError);

  return (
    <section className="view cyber-view">
      <header className="view__header">
        <h2 className="view__title">Cyber Defense Operations</h2>
        <LlmModeBadge />
        <p className="view__desc">
          红队攻击、蓝队防御与紫队审查的协同态势，以及 ATT&CK 威胁情报。
          演练由 Chat 创建，这里用于查看过程、证据和收敛结果。
        </p>
      </header>

      <div className="cyber-view__range-bar">
        <span className="cyber-view__range-id">
          {currentRange ? <>当前靶场：<code>{currentRange.range_id}</code></> : "演练只能从 Chat 创建"}
        </span>
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
