// date: 2026-08-27
// dev: ox-alpha
// R11: 调度沙盒 —— 拖动 latency_budget 滑块 + privacy 开关，实时预览会被调度到哪一层

import { useState } from "react";

const SCHEDULE_RULES = [
  { tier: "device", label: "端 (Device)", color: "#3fb950", emoji: "🖥️" },
  { tier: "edge", label: "边 (Edge)", color: "#2f81f7", emoji: "🌐" },
  { tier: "cloud", label: "云 (Cloud)", color: "#d29922", emoji: "☁️" },
] as const;

/** 本地复算调度四规则（前端不调后端，体现透明度） */
function predictTier(latencyBudget: number, privacy: string): string {
  if (privacy === "local") return "device";
  if (latencyBudget <= 0.5) return "device";
  if (latencyBudget <= 3.0) return "edge";
  return "cloud";
}

export function DispatchSandbox() {
  const [latency, setLatency] = useState(1.5);
  const [privacy, setPrivacy] = useState("standard");
  const predicted = predictTier(latency, privacy);

  return (
    <div className="dispatch-sandbox">
      <h3 className="dispatch-sandbox__title">调度沙盒</h3>
      <p className="dispatch-sandbox__desc">
        拖动滑杆 + 切换隐私，实时预览调度决策
      </p>

      <div className="dispatch-sandbox__controls">
        <label className="dispatch-sandbox__label">
          延迟预算: <strong>{latency.toFixed(1)}s</strong>
        </label>
        <input
          type="range"
          min={0.1}
          max={10.0}
          step={0.1}
          value={latency}
          onChange={(e) => setLatency(Number(e.target.value))}
          className="dispatch-sandbox__slider"
        />

        <label className="dispatch-sandbox__label">隐私级别:</label>
        <div className="dispatch-sandbox__radios">
          {[
            { value: "unrestricted", label: "可上云" },
            { value: "standard", label: "标准" },
            { value: "local", label: "本地" },
          ].map((opt) => (
            <label key={opt.value} className="dispatch-sandbox__radio">
              <input
                type="radio"
                name="privacy"
                value={opt.value}
                checked={privacy === opt.value}
                onChange={() => setPrivacy(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>

        <div className="dispatch-sandbox__result">
          <span className="dispatch-sandbox__result-label">预测落点: </span>
          {SCHEDULE_RULES.map((rule) => (
            <span
              key={rule.tier}
              className={`dispatch-sandbox__tier ${predicted === rule.tier ? "dispatch-sandbox__tier--active" : ""}`}
              style={{
                borderColor: rule.color,
                backgroundColor: predicted === rule.tier ? `${rule.color}33` : "transparent",
              }}
            >
              {rule.emoji} {rule.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}