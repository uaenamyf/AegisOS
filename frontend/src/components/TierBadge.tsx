// date: 2026-08-27
// dev: ox-alpha
// R11: 执行落点徽标 —— D/E/C 三色角标，标识该步推理发生在哪一层

const TIER_CONFIG: Record<string, { label: string; color: string; emoji: string }> = {
  device: { label: "D", color: "#3fb950", emoji: "🖥️" },
  edge: { label: "E", color: "#2f81f7", emoji: "🌐" },
  cloud: { label: "C", color: "#d29922", emoji: "☁️" },
};

interface TierBadgeProps {
  tier: string;
  /** 显示完整标签（含 emoji），默认仅显示字母 */
  full?: boolean;
}

export function TierBadge({ tier, full = false }: TierBadgeProps) {
  const cfg = TIER_CONFIG[tier];
  if (!cfg) return null;

  return (
    <span
      className="tier-badge"
      style={{
        backgroundColor: `${cfg.color}22`,
        borderColor: cfg.color,
        color: cfg.color,
      }}
      title={`执行于 ${tier === "device" ? "端侧" : tier === "edge" ? "边侧" : "云侧"}`}
    >
      {full ? `${cfg.emoji} ${cfg.label}` : cfg.label}
    </span>
  );
}

export { TIER_CONFIG };