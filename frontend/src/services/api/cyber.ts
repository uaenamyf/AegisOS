// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/api/cyber.ts，攻防演练 REST API 服务（range/attack/defense/threat）

import { apiClient } from "@/lib/api-client";
import type {
  BlueDefenseResponse,
  PurpleReviewResponse,
  RangeResponse,
  RedAttackResponse,
  ThreatIntel,
  TopologyResponse,
} from "@/protocol/types";

export interface StartRangeRequest {
  target_range?: string;
  label?: string;
}

export interface RedAttackRequest {
  target_range?: string;
}

export interface BlueDefenseRequest {
  event_stream?: Record<string, unknown>[];
}

export interface PurpleReviewRequest {
  attack_chain: Record<string, any>;
  response_plan: Record<string, any>;
  alerts: Record<string, any>[];
}

export const cyberApi = {
  startRange: (body: StartRangeRequest): Promise<RangeResponse> =>
    apiClient.post<RangeResponse>("/range/start", body),

  getRange: (rangeId: string): Promise<RangeResponse> =>
    apiClient.get<RangeResponse>(`/range/${encodeURIComponent(rangeId)}`),

  getTopology: (rangeId: string): Promise<TopologyResponse> =>
    apiClient.get<TopologyResponse>(
      `/range/${encodeURIComponent(rangeId)}/topology`,
    ),

  redAttack: (body: RedAttackRequest): Promise<RedAttackResponse> =>
    apiClient.post<RedAttackResponse>("/attack", body),

  getAttackChain: (rangeId: string): Promise<RedAttackResponse> =>
    apiClient.get<RedAttackResponse>(
      `/attack/chain/${encodeURIComponent(rangeId)}`,
    ),

  blueDefense: (body: BlueDefenseRequest): Promise<BlueDefenseResponse> =>
    apiClient.post<BlueDefenseResponse>("/defense", body),

  getDefense: (rangeId: string): Promise<BlueDefenseResponse> =>
    apiClient.get<BlueDefenseResponse>(`/defense/${encodeURIComponent(rangeId)}`),

  purpleReview: (body: PurpleReviewRequest): Promise<PurpleReviewResponse> =>
    apiClient.post<PurpleReviewResponse>("/defense/purple-review", body),

  getAttackTechniques: (tactic?: string): Promise<ThreatIntel[]> =>
    apiClient.get<ThreatIntel[]>(
      `/threat/attack-techniques${tactic ? `?tactic=${encodeURIComponent(tactic)}` : ""}`,
    ),
};
