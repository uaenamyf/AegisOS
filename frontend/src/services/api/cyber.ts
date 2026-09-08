// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/api/cyber.ts，攻防演练 REST API 服务（range/attack/defense/threat）
// changelog: 2026-09-04 R4 新增 drill 方法——start/get/summary/abort + SSE 订阅（对齐 backend/routers/drill.py）

import { apiClient } from "@/lib/api-client";
import { config } from "@/config";
import type {
  BlueDefenseResponse,
  BlueDefenseStreamEvent,
  BlueDefenseStreamEventName,
  DrillEvent,
  DrillEventName,
  DrillMeta,
  DrillRecord,
  DrillSummaryResponse,
  PurpleReviewResponse,
  RangeResponse,
  RedAttackResponse,
  RedAttackStreamEvent,
  RedAttackStreamEventName,
  StartDrillRequest,
  StartDrillResponse,
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

  /**
   * 红队攻击链 SSE 流式执行（渐进展示）。
   *
   * 事件名：``stage_start``（recon/vuln/exploit）→ ``stage_done``（各步产出）
   * → ``done``（完整结果）；失败时 ``attack_error``。POST body 走
   * fetch + ReadableStream 解析 SSE（EventSource 无法携带 Header/body）。
   * 返回关闭函数（AbortController）供组件卸载时调用。
   */
  redAttackStream: (
    body: RedAttackRequest,
    onEvent: (event: RedAttackStreamEvent) => void,
    onError?: (err: Error) => void,
  ): (() => void) => {
    const controller = new AbortController();
    void fetch(`${config.apiBaseUrl}/attack/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        [config.apiKeyHeader]: config.apiKey,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok || !res.body) {
          throw new Error(`attack stream failed: HTTP ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        const pump = (): void => {
          void reader
            .read()
            .then(({ done, value }) => {
              if (done) return;
              buffer += decoder.decode(value, { stream: true });
              const frames = buffer.split("\n\n");
              buffer = frames.pop() ?? "";
              for (const frame of frames) {
                const evLine = frame.split("\n").find((l) => l.startsWith("event:"));
                const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
                if (!evLine || !dataLine) continue;
                try {
                  onEvent({
                    name: evLine.slice(6).trim() as RedAttackStreamEventName,
                    data: JSON.parse(dataLine.slice(5).trim()),
                  });
                } catch {
                  /* ignore malformed frames */
                }
              }
              pump();
            })
            .catch((err) => onError?.(err as Error));
        };
        pump();
      })
      .catch((err) => onError?.(err as Error));
    return () => controller.abort();
  },

  getAttackChain: (rangeId: string): Promise<RedAttackResponse> =>
    apiClient.get<RedAttackResponse>(
      `/attack/chain/${encodeURIComponent(rangeId)}`,
    ),

  blueDefense: (body: BlueDefenseRequest): Promise<BlueDefenseResponse> =>
    apiClient.post<BlueDefenseResponse>("/defense", body),

  /**
   * 蓝队防御链 SSE 流式执行（渐进展示）。
   *
   * 事件名：``stage_start``（detect/triage/hunt/ir）→ ``stage_done``
   * （各步产出）→ ``done``（完整结果）；失败时 ``defense_error``。
   * 与红队流式同构（fetch + ReadableStream 解析 SSE）。
   * 返回关闭函数（AbortController）供组件卸载时调用。
   */
  blueDefenseStream: (
    body: BlueDefenseRequest,
    onEvent: (event: BlueDefenseStreamEvent) => void,
    onError?: (err: Error) => void,
  ): (() => void) => {
    const controller = new AbortController();
    void fetch(`${config.apiBaseUrl}/defense/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        [config.apiKeyHeader]: config.apiKey,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok || !res.body) {
          throw new Error(`defense stream failed: HTTP ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        const pump = (): void => {
          void reader
            .read()
            .then(({ done, value }) => {
              if (done) return;
              buffer += decoder.decode(value, { stream: true });
              const frames = buffer.split("\n\n");
              buffer = frames.pop() ?? "";
              for (const frame of frames) {
                const evLine = frame.split("\n").find((l) => l.startsWith("event:"));
                const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
                if (!evLine || !dataLine) continue;
                try {
                  onEvent({
                    name: evLine.slice(6).trim() as BlueDefenseStreamEventName,
                    data: JSON.parse(dataLine.slice(5).trim()),
                  });
                } catch {
                  /* ignore malformed frames */
                }
              }
              pump();
            })
            .catch((err) => onError?.(err as Error));
        };
        pump();
      })
      .catch((err) => onError?.(err as Error));
    return () => controller.abort();
  },

  getDefense: (rangeId: string): Promise<BlueDefenseResponse> =>
    apiClient.get<BlueDefenseResponse>(`/defense/${encodeURIComponent(rangeId)}`),

  purpleReview: (body: PurpleReviewRequest): Promise<PurpleReviewResponse> =>
    apiClient.post<PurpleReviewResponse>("/defense/purple-review", body),

  getAttackTechniques: (tactic?: string): Promise<ThreatIntel[]> =>
    apiClient.get<ThreatIntel[]>(
      `/threat/attack-techniques${tactic ? `?tactic=${encodeURIComponent(tactic)}` : ""}`,
    ),

  // ---- CyberDrill（多轮攻防演练，R3/R4）----

  startDrill: (body: StartDrillRequest): Promise<StartDrillResponse> =>
    apiClient.post<StartDrillResponse>("/drill/start", body),

  // T7: 列出本地持久化的历史演练（元信息，按时间倒序）
  listDrills: (): Promise<{ drills: DrillMeta[] }> =>
    apiClient.get<{ drills: DrillMeta[] }>("/drill/list"),

  getDrill: (drillId: string): Promise<DrillRecord> =>
    apiClient.get<DrillRecord>(`/drill/${encodeURIComponent(drillId)}`),

  getDrillSummary: (drillId: string): Promise<DrillSummaryResponse> =>
    apiClient.get<DrillSummaryResponse>(
      `/drill/${encodeURIComponent(drillId)}/summary`,
    ),

  /**
   * 获取 Auto Drill 运行记录报告（每轮红/蓝/紫产物 + 卸载轨迹 + 收敛总结）。
   * 返回 Markdown 文本（report_md），前端可折叠展示 / 复制存档。
   */
  getDrillReport: (
    drillId: string,
  ): Promise<{
    drill_id: string;
    report_md: string;
    rounds_executed: number;
    convergence_code: string;
    raw_json_path: string;
  }> =>
    apiClient.get(`/drill/${encodeURIComponent(drillId)}/report`),

  /**
   * R18d：下载演练报告为真正的 PDF 文件（后端 reportlab 渲染，非浏览器打印预览）。
   * 返回 Blob，前端用 URL.createObjectURL 触发下载。
   */
  async getDrillReportPdf(drillId: string): Promise<Blob> {
    const url = `${apiClient.baseUrl}/drill/${encodeURIComponent(drillId)}/report.pdf`;
    const headers: Record<string, string> = {
      [config.apiKeyHeader]: config.apiKey,
    };
    const res = await fetch(url, { headers });
    if (!res.ok) {
      throw new Error(`报告导出失败（HTTP ${res.status}）`);
    }
    return res.blob();
  },

  abortDrill: (drillId: string): Promise<{ drill_id: string; status: string }> =>
    apiClient.post<{ drill_id: string; status: string }>(
      `/drill/${encodeURIComponent(drillId)}/abort`,
    ),

  /**
   * 订阅一场演练的 SSE 战报流。
   *
   * 按 ``event:`` 名分发 ``drill_start / drill_round / drill_summary /
   * drill_done / drill_error`` 到 ``onEvent`` 回调；返回关闭函数供组件
   * 卸载时调用。EventSource 无法携带自定义 Header，故 API Key 走
   * query 参数（与 backend.core.auth.verify_api_key 的 Query 兜底一致）。
   *
   * ``onError`` 可选；触发时流已断开（EventSource 已 close），调用方可
   * 用 ``getDrill`` 轮询补拉已发生轮次。
   */
  openDrillStream: (
    drillId: string,
    onEvent: (event: DrillEvent) => void,
    onError?: () => void,
  ): (() => void) => {
    const url =
      `${config.apiBaseUrl}/drill/${encodeURIComponent(drillId)}/stream` +
      `?api_key=${encodeURIComponent(config.apiKey)}`;
    const source = new EventSource(url);
    const names: DrillEventName[] = [
      "drill_start",
      "drill_round",
      "drill_summary",
      "drill_done",
      "drill_error",
    ];
    names.forEach((name) => {
      source.addEventListener(name, (msg) => {
        try {
          const data = JSON.parse((msg as MessageEvent).data) as Record<
            string,
            any
          >;
          onEvent({ name, data });
        } catch {
          /* ignore malformed payloads */
        }
      });
    });
    if (onError) {
      source.onerror = () => {
        source.close();
        onError();
      };
    }
    return () => source.close();
  },
};
