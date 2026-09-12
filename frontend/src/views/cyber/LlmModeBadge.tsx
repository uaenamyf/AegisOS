// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R7 新建 LlmModeBadge——运行时模式可视化徽标（mock/真实 LLM 切换）

import { useCallback, useEffect, useState } from "react";
import { systemApi } from "@/services/api/system";
import type { RuntimeMode, SystemModeInfo } from "@/protocol/types";

/**
 * 运行时模式徽标：展示当前 LLM 运行模式（mock 预置响应 / 真实模型），
 * 点击可切换。挂在 CyberView 头部，让用户/评委一眼看出当前走的是
 * mock 还是真实大模型，并可一键切换（演示时 mock 兜底、真实验证切换）。
 */
export function LlmModeBadge() {
  const [info, setInfo] = useState<SystemModeInfo | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const next = await systemApi.getMode();
      setInfo(next);
    } catch {
      /* 后端离线时徽标保持未知态 */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleToggle = useCallback(async () => {
    if (!info || busy) return;
    const target: RuntimeMode = info.mode === "real" ? "mock" : "real";
    if (!info.available.includes(target)) return;
    setBusy(true);
    try {
      const next = await systemApi.setMode(target);
      setInfo(next);
    } catch {
      /* 切换失败保持当前显示 */
    } finally {
      setBusy(false);
    }
  }, [info, busy]);

  if (!info) {
    return <span className="llm-badge llm-badge--unknown">模型状态：读取中…</span>;
  }

  const isReal = info.mode === "real";
  const canToggle = info.available.length > 1;
  const label = isReal
    ? `LLM: ${info.provider}${info.model ? ` (${info.model})` : ""}`
    : "模型状态：演示模式";
  const displayLabel = isReal ? `模型：${info.provider}${info.model ? `（${info.model}）` : ""}` : label;

  return (
    <button
      type="button"
      className={`llm-badge llm-badge--${info.mode}${canToggle ? " llm-badge--switchable" : ""}`}
      onClick={() => void handleToggle()}
      disabled={!canToggle || busy}
      title={
        canToggle
          ? `当前${isReal ? "真实模型" : "演示模式"}，点击切换到${isReal ? "演示模式" : "真实模型"}`
          : info.mode === "real"
            ? "真实模型（不可切换）"
            : "演示模式（未配置 API Key，不可切换到真实模型）"
      }
      aria-label={`LLM mode: ${info.mode}${canToggle ? ", click to toggle" : ""}`}
    >
      <span className={`llm-badge__dot llm-badge__dot--${info.mode}`} />
      {displayLabel}
      {canToggle ? <span className="llm-badge__hint">{busy ? "…" : "⇄"}</span> : null}
    </button>
  );
}
