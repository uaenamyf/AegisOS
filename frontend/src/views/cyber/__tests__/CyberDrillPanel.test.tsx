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
