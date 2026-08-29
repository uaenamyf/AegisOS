// date: 2026-08-27
// dev: ox-alpha
// R11: 调度沙盒 —— 拖动 latency_budget 滑块 + privacy 开关，实时预览调度决策
// date: 2026-08-29 —— 升级：新增"真实派发"按钮，实际调用 /infra/dispatch 验证落点

import { useState } from "react";
import { infraApi } from "@/services/api/infra";

const SCHEDULE_RULES = [
  { tier: "device", label: "端 (Device)", color: "#3fb950", emoji: "🖥️" },
  { tier: "edge", label: "边 (Edge)", color: "#2f81f7", emoji: "🌐" },
  { tier: "cloud", label: "云 (Cloud)", color: "#d29922", emoji: "☁️" },
] as const;

/** 本地复算调度四规则（前端预览用） */
function predictTier(latencyBudget: number, privacy: string): string {
  if (privacy === "local") return "device";
  if (latencyBudget <= 0.5) return "device";
  if (latencyBudget <= 3.0) return "edge";
  return "cloud";
}

export function DispatchSandbox() {
  const [latency, setLatency] = useState(1.5);
  const [privacy, setPrivacy] = useState("standard");
  const [dispatching, setDispatching] = useState(false);
  const [result, setResult] = useState<{
    tier: string;
    latency_ms: number;
    text: string;
    privacy_note: string;
    attempts: Array<{ tier?: string; actual_tier?: string; target_tier?: string; ok: boolean; latency_ms: number }>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const predicted = predictTier(latency, privacy);

  const runDispatch = async () => {
    setDispatching(true);
    setError(null);
    setResult(null);
    try {
      const res = await infraApi.dispatch({
        goal: "用一句话解释什么是网络防火墙",
        latency_budget: latency,
        privacy,
        system_prompt: "请用中文简洁回答",
      });
      setResult({
        tier: res.tier,
        latency_ms: res.latency_ms,
        text: res.text,
        privacy_note: res.privacy_note || "",
        attempts: res.attempts || [],
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "派发失败");
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="dispatch-sandbox">
      <h3 className="dispatch-sandbox__title">调度沙盒</h3>
      <p className="dispatch-sandbox__desc">
        拖动滑杆 + 切换隐私，实时预览调度决策；点"真实派发"实际调用后端验证落点
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

        <button
          className="dispatch-sandbox__run"
          onClick={runDispatch}
          disabled={dispatching}
        >
          {dispatching ? "派发中..." : "🚀 真实派发（调后端验证落点）"}
        </button>

        {error && (
          <div className="dispatch-sandbox__error">Error: {error}</div>
        )}

        {result && (
          <div className="dispatch-sandbox__actual">
            <div className="dispatch-sandbox__actual-head">
              <span
                className={`tier-banner tier-banner--${result.tier}`}
                style={{ marginBottom: 0 }}
              >
                {result.tier === "device"
                  ? "🖥️ 端侧推理"
                  : result.tier === "edge"
                    ? "🌐 边侧推理"
                    : "☁️ 云侧推理"}
              </span>
              <span className="dispatch-sandbox__latency">
                {result.latency_ms.toFixed(0)} ms
              </span>
            </div>
            {result.privacy_note && (
              <div className="dispatch-sandbox__note">🔒 {result.privacy_note}</div>
            )}
            <div className="dispatch-sandbox__text">{result.text}</div>
            {result.attempts.length > 0 && (
              <details className="dispatch-sandbox__attempts">
                <summary>调度轨迹（{result.attempts.length} 跳）</summary>
                <ol>
                  {result.attempts.map((a, i) => (
                    <li key={i}>
                      {a.actual_tier || a.tier || a.target_tier} —{" "}
                      {a.ok ? "✅" : "❌"} {a.latency_ms.toFixed(0)}ms
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
