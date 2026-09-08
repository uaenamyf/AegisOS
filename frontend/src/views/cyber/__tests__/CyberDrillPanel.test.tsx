// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R5 新建 CyberDrillPanel 组件测试——开始/停止 + SSE 轮次时间线 + 总结 + 断线兜底

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";

// Mock cyberApi (no real network / EventSource in jsdom)
vi.mock("@/services/api/cyber", () => ({
  cyberApi: {
    startDrill: vi.fn(),
    abortDrill: vi.fn(),
    getDrill: vi.fn(),
    getDrillSummary: vi.fn(),
    openDrillStream: vi.fn(),
    listDrills: vi.fn().mockResolvedValue({ drills: [] }),
    getDrillReport: vi.fn().mockResolvedValue({ report: "" }),
    getDrillReportPdf: vi.fn().mockResolvedValue(new Blob()),
  },
}));

// Mock zustand store
let mockState: Record<string, unknown> = {};

vi.mock("@/lib/store", () => ({
  useAppStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector(mockState),
}));

import { cyberApi } from "@/services/api/cyber";
import { CyberDrillPanel } from "../CyberDrillPanel";

const mockStartDrill = cyberApi.startDrill as ReturnType<typeof vi.fn>;
const mockAbortDrill = cyberApi.abortDrill as ReturnType<typeof vi.fn>;
const mockGetDrill = cyberApi.getDrill as ReturnType<typeof vi.fn>;
const mockOpenStream = cyberApi.openDrillStream as ReturnType<typeof vi.fn>;

// capture onEvent/onError passed to openDrillStream
let capturedOnEvent: ((ev: any) => void) | null = null;
let capturedOnError: (() => void) | null = null;

const roundData = (round: number, converged = false) => ({
  round,
  red: {
    ok: true,
    assets: ["asset-1", "asset-2"],
    finding_count: 2,
    steps: [],
    new_steps: [{ step_id: `s-${round}`, technique: "T1190", from_asset: "asset-1", to_asset: "asset-2", success: true }],
  },
  blue: {
    ok: true,
    alerts: [],
    triaged_count: 1,
    plan: { plan_id: `p-${round}`, actions: [{ action: "isolate", target: "asset-2" }] },
  },
  purple: {
    ok: true,
    critique: { valid: converged, issues: [], suggestion: "keep probing" },
    review: { consistent: true, overall_assessment: "chain consistent" },
    converged,
    valid: converged,
    new_issue_count: converged ? 0 : 1,
  },
  event_stream: [],
  convergence_code: converged ? "converged" : "exploring",
});

// R18g：缺口闭环循环视图专用轮次数据（含红队新增步 / 蓝队告警与处置 / 紫队缺口）。
const closureRound = (
  round: number,
  opts: {
    issue: string;
    newSteps: { technique: string; from_asset: string; to_asset: string }[];
    valid: boolean;
  },
) => ({
  round,
  red: {
    ok: true,
    assets: ["asset-001", "asset-004"],
    finding_count: opts.newSteps.length,
    steps: [],
    new_steps: opts.newSteps.map((s, i) => ({ ...s, step_id: `r${round}-${i}`, success: true })),
  },
  blue: {
    ok: true,
    alerts: opts.newSteps.map((s, i) => ({ alert_id: `a-${round}-${i}`, technique: s.technique })),
    triaged_count: opts.newSteps.length,
    plan: { actions: [{ action_id: `ACT-00${round}`, kind: "isolate", target: "asset-001" }] },
  },
  purple: {
    ok: true,
    critique: {
      valid: opts.valid,
      issues: opts.valid ? [] : [opts.issue],
      severity: opts.valid ? "low" : "high",
      suggestion: "keep probing",
    },
    review: {},
    converged: opts.valid,
    valid: opts.valid,
    new_issue_count: opts.valid ? 0 : 1,
  },
  event_stream: [],
  convergence_code: opts.valid ? "converged" : "exploring",
});

const summaryData = {
  conclusion: "多轮红蓝紫对抗后达成收敛：攻击链覆盖全部暴露面并通过紫队一致性校验。",
  convergence_code: "converged",
  rounds_executed: 3,
};

beforeEach(() => {
  mockState = {
    cyberLoading: false,
    cyberError: null,
    setCyberLoading: vi.fn(),
    setCyberError: vi.fn(),
  };
  vi.clearAllMocks();
  // 组件挂载时会用 sessionStorage 里的历史 drillId 补拉 getDrill；
  // clearAllMocks 后必须给默认解析值，否则 .then 报 undefined。
  mockGetDrill.mockResolvedValue({
    drill_id: "drill-abc",
    target_range: "10.0.0.0/24",
    max_rounds: 5,
    rounds_executed: 0,
    convergence_code: "converged",
    rounds: [],
    summary: null,
  });
  capturedOnEvent = null;
  capturedOnError = null;
  mockOpenStream.mockImplementation((_id: string, onEvent: any, onError?: any) => {
    capturedOnEvent = onEvent;
    capturedOnError = onError ?? null;
    return () => {};
  });
});

describe("CyberDrillPanel", () => {
  it("renders start button and inputs", () => {
    render(<CyberDrillPanel />);
    expect(screen.getByText("▶ Start Drill")).toBeDefined();
    expect(screen.getByLabelText("Target range")).toBeDefined();
    expect(screen.getByLabelText("Max rounds")).toBeDefined();
  });

  it("starts drill and subscribes SSE stream", async () => {
    mockStartDrill.mockResolvedValue({
      drill_id: "drill-abc",
      status: "running",
      max_rounds: 5,
    });
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));

    await waitFor(() => {
      expect(mockStartDrill).toHaveBeenCalledWith({
        target_range: "10.0.0.0/24",
        max_rounds: 5,
      });
      expect(mockOpenStream).toHaveBeenCalledWith(
        "drill-abc",
        expect.any(Function),
        expect.any(Function),
      );
    });
    expect(screen.getByText("⏹ Stop")).toBeDefined();
  });

  it("appends round cards from drill_round events", async () => {
    mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 5 });
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));
    await waitFor(() => expect(capturedOnEvent).toBeTruthy());

    act(() => {
      capturedOnEvent!({ name: "drill_round", data: roundData(1) });
      capturedOnEvent!({ name: "drill_round", data: roundData(2) });
    });
    expect(screen.getByText("Round 1")).toBeDefined();
    expect(screen.getByText("Round 2")).toBeDefined();
    // 两个轮次卡都有同构统计 → 用 getAllByText
    expect(screen.getAllByText(/Red: 2 findings/).length).toBe(2);
  });

  it("renders summary report after drill_summary", async () => {
    mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 5 });
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));
    await waitFor(() => expect(capturedOnEvent).toBeTruthy());

    act(() => {
      capturedOnEvent!({ name: "drill_round", data: roundData(3, true) });
      capturedOnEvent!({ name: "drill_summary", data: summaryData });
      capturedOnEvent!({ name: "drill_done", data: { drill_id: "drill-abc" } });
    });
    expect(screen.getByText("Drill Summary")).toBeDefined();
    // round3 徽标 + summary 徽标都可能显示 converged → getAllByText
    expect(screen.getAllByText("converged").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("3 rounds")).toBeDefined();
    expect(screen.getByText(/多轮红蓝紫对抗后达成收敛/)).toBeDefined();
    // 结束后恢复开始按钮
    expect(screen.getByText("▶ Start Drill")).toBeDefined();
  });

  it("stop aborts running drill", async () => {
    mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 5 });
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));
    await waitFor(() => expect(screen.getByText("⏹ Stop")).toBeDefined());

    fireEvent.click(screen.getByText("⏹ Stop"));
    await waitFor(() => expect(mockAbortDrill).toHaveBeenCalledWith("drill-abc"));
  });

  it("gap closure loop shows all three teams in ascending round order", async () => {
    // R18g 重构：闭环模块改为「循环骶架 + 逐轮升序流水」。
    // 断言：① 三队职责齐备；② 每轮恰好出现一次、严格升序；
    // ③ 旧版「按缺口展开 N 条链」的穿插文案彻底消失。
    mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 4 });
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));
    await waitFor(() => expect(capturedOnEvent).toBeTruthy());

    act(() => {
      capturedOnEvent!({
        name: "drill_round",
        data: closureRound(1, {
          issue: "STEP-001: 未覆盖横向移动路径（T1021），链止步于 asset-002",
          newSteps: [{ technique: "T1190", from_asset: "asset-001", to_asset: "asset-002" }],
          valid: false,
        }),
      });
      capturedOnEvent!({
        name: "drill_round",
        data: closureRound(2, {
          issue: "已抵达 asset-003，但尚未对域控 asset-004 建立利用路径",
          newSteps: [{ technique: "T1021", from_asset: "asset-002", to_asset: "asset-003" }],
          valid: false,
        }),
      });
      capturedOnEvent!({
        name: "drill_round",
        data: closureRound(3, {
          issue: "未执行凭据窃取（T1003），目标达成步缺失",
          newSteps: [{ technique: "T1078", from_asset: "asset-003", to_asset: "asset-004" }],
          valid: false,
        }),
      });
      capturedOnEvent!({
        name: "drill_round",
        data: closureRound(4, {
          issue: "",
          newSteps: [{ technique: "T1003", from_asset: "asset-004", to_asset: "asset-004" }],
          valid: true,
        }),
      });
    });

    // ① 循环骶架：红/蓝/紫三队职责都在（旧版蓝队缺席）
    expect(screen.getByText("红队·攻击")).toBeDefined();
    expect(screen.getByText("蓝队·防御")).toBeDefined();
    expect(screen.getByText("紫队·判定")).toBeDefined();
    expect(screen.getByText("缺口反馈")).toBeDefined();

    // ② 每轮恰好一行、严格升序（按 DOM 文本顺序取出轮次号验证）
    const roundLabels = screen.getAllByText(/^第 \d 轮$/).map((el) => el.textContent);
    expect(roundLabels).toEqual(["第 1 轮", "第 2 轮", "第 3 轮", "第 4 轮"]);

    // ③ 蓝队逐轮告警/处置、紫队逐轮缺口都渲染在轮行里
    expect(screen.getAllByText(/蓝队 告警 \d+ · 处置 \d+/).length).toBe(4);
    expect(screen.getAllByText(/紫队 判定 ✓ 链路成立/).length).toBe(1);

    // ④ 旧版穿插式单链文案已移除
    expect(screen.queryByText(/第 \d+ 轮 · 紫队判定/)).toBeNull();
    expect(screen.queryByText(/本缺口已闭合，但紫队提出新缺口/)).toBeNull();

    // ⑤ 收敛结论行：缺口数趋势 + 末轮收敛判定
    expect(screen.getByText(/末轮紫队判定通过，循环收敛终止/)).toBeDefined();
  });

  it("polls getDrill to backfill after SSE disconnect", async () => {
    mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 5 });
    mockGetDrill.mockResolvedValue({
      drill_id: "drill-abc",
      target_range: "10.0.0.0/24",
      max_rounds: 5,
      rounds_executed: 2,
      convergence_code: "converged",
      rounds: [roundData(1), roundData(2, true)],
      summary: summaryData,
    });
    vi.useFakeTimers();
    render(<CyberDrillPanel />);
    fireEvent.click(screen.getByText("▶ Start Drill"));
    // 刷掉 startDrill 的 microtask，拿到 openDrillStream 回调
    await act(async () => {
      await Promise.resolve();
    });
    expect(capturedOnError).toBeTruthy();

    act(() => {
      capturedOnError!();
    });
    await act(async () => {
      vi.advanceTimersByTime(2500);
      await Promise.resolve();
    });
    expect(mockGetDrill).toHaveBeenCalledWith("drill-abc");
    expect(screen.getByText("Round 1")).toBeDefined();
    expect(screen.getByText("Drill Summary")).toBeDefined();
    vi.useRealTimers();
  });
});
