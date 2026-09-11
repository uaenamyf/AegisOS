/** Chat 意图识别与演练参数槽位提取。 */

export type ChatIntentKind = "cyber_drill" | "task";

export interface ChatIntent {
  kind: ChatIntentKind;
  confidence: number;
  targetRange: string;
  maxRounds: number;
  needsClarification: boolean;
  clarification?: string;
  reason: string;
}

export interface ChatMemoryHints {
  preferred_target_range?: string;
  preferred_max_rounds?: number;
}

const DEFAULT_TARGET_RANGE = "10.0.0.0/24";
const DEFAULT_ROUNDS = 5;
const DRILL_PATTERN = /模拟.*攻防|红蓝紫|攻防演练|自动演练|完整.*演练|安全靶场|red.?blue.?purple/i;
const CYBER_CONTEXT_PATTERN = /攻击|防御|检测|响应|靶场|轮次|红队|蓝队|紫队/i;
const CIDR_PATTERN = /\b(?:\d{1,3}\.){3}\d{1,3}\/\d{1,2}\b/;
const ROUND_PATTERN = /(?:完成|跑|执行|进行|最多|至多)\s*(\d{1,2})\s*轮|(?:rounds?|轮次?)\s*[:：]?\s*(\d{1,2})|(?:for|最多)\s*(\d{1,2})\s*(?:rounds?|轮)/i;

function isPrivateCidr(value: string): boolean {
  const [address, prefixText] = value.split("/");
  const octets = address.split(".").map(Number);
  const prefix = Number(prefixText);
  if (octets.length !== 4 || octets.some((item) => !Number.isInteger(item) || item < 0 || item > 255)) return false;
  if (!Number.isInteger(prefix) || prefix < 8 || prefix > 32) return false;
  return octets[0] === 10 || octets[0] === 192 && octets[1] === 168 || octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31;
}

function extractRounds(goal: string, fallback = DEFAULT_ROUNDS): number {
  const match = goal.match(ROUND_PATTERN);
  const value = Number(match?.[1] ?? match?.[2] ?? match?.[3] ?? fallback);
  return Number.isInteger(value) ? Math.min(10, Math.max(1, value)) : fallback;
}

export function parseChatIntent(goal: string, hints: ChatMemoryHints = {}): ChatIntent {
  const normalized = goal.trim();
  const hasExplicitDrill = DRILL_PATTERN.test(normalized);
  const hasCyberContext = CYBER_CONTEXT_PATTERN.test(normalized);
  const targetMatch = normalized.match(CIDR_PATTERN)?.[0];
  const rememberedTarget = hints.preferred_target_range && isPrivateCidr(hints.preferred_target_range)
    ? hints.preferred_target_range
    : DEFAULT_TARGET_RANGE;
  const rememberedRounds = Number.isInteger(hints.preferred_max_rounds)
    ? Math.min(10, Math.max(1, hints.preferred_max_rounds as number))
    : DEFAULT_ROUNDS;
  const targetRange = targetMatch ?? rememberedTarget;
  const hasUnsafeTarget = Boolean(targetMatch && !isPrivateCidr(targetRange));

  if (!hasExplicitDrill && !hasCyberContext) {
    return {
      kind: "task",
      confidence: 0.98,
      targetRange: DEFAULT_TARGET_RANGE,
      maxRounds: rememberedRounds,
      needsClarification: false,
      reason: "未检测到攻防演练语义，按普通任务处理。",
    };
  }

  if (hasUnsafeTarget) {
    return {
      kind: "cyber_drill",
      confidence: 0.2,
      targetRange,
      maxRounds: extractRounds(normalized, rememberedRounds),
      needsClarification: true,
      clarification: "演练只能在私有安全靶场网段内执行，请提供 10.x、172.16-31.x 或 192.168.x 网段。",
      reason: "目标网段不满足安全靶场约束。",
    };
  }

  const confidence = hasExplicitDrill ? 0.96 : 0.72;
  return {
    kind: "cyber_drill",
    confidence,
    targetRange,
    maxRounds: extractRounds(normalized, rememberedRounds),
    needsClarification: !hasExplicitDrill,
    clarification: hasExplicitDrill ? undefined : "请确认是否启动完整红蓝紫攻防演练？演练将在安全演示靶场内执行。",
    reason: hasExplicitDrill ? "检测到明确的完整攻防演练指令。" : "检测到攻防相关词汇，但缺少明确的启动意图。",
  };
}