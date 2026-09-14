// date: 2026-09-14
// dev: OpenSquilla
// changelog: R19f 回归测试——切页卸载后恢复，ref 不再被卸载清理置空：
// Stop 可用、3s 兜底轮询活着、快照进度（CoT/阶段/耗时）恢复展示。

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";

// Mock cyberApi (no real network / EventSource in jsdom)
vi.mock("@/services/api/cyber", () => ({
  cyberApi: {
    startRange: vi.fn(),
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

const roundData = (round: number) => ({
  round,
  red: {
    ok: true,
    assets: ["asset-1"],
    finding_count: 1,
    steps: [],
    new_steps: [{ step_id: `s-${round}`, technique: "T1190", from_asset: "asset-1", to_asset: "asset-2", success: true }],
  },
  blue: { ok: true, alerts: [], triaged_count: 1, plan: { plan_id: `p-${round}`, actions: [] } },
  purple: {
    ok: true,
    critique: { valid: false, issues: ["x"], suggestion: "keep" },
    review: {},
    converged: false,
    valid: false,
    new_issue_count: 1,
  },
  event_stream: [],
  convergence_code: "exploring",
});

const runningRecord = () => ({
  drill_id: "drill-abc",
  target_range: "10.0.0.0/24",
  status: "running",
  max_rounds: 5,
  rounds_executed: 1,
  convergence_code: null,
  rounds: [roundData(1)],
  summary: null,
  current_stage: "blue",
  current_round: 2,
  elapsed: 42,
  agent_trace: [
    { round: 1, stage: "red", agent: "recon", label: "侦察资产", ts: 1 },
    { round: 1, stage: "blue", agent: "detector", label: "检测入侵", ts: 2 },
  ],
});

beforeEach(() => {
  mockState = {
    cyberLoading: false,
    cyberError: null,
    currentRange: null,
    setCyberLoading: vi.fn(),
    setCyberError: vi.fn(),
    setCurrentRange: vi.fn(),
  };
  vi.clearAllMocks();
  sessionStorage.clear();
  mockGetDrill.mockResolvedValue(runningRecord());
  capturedOnEvent = null;
  mockOpenStream.mockImplementation((_id: string, onEvent: any) => {
    capturedOnEvent = onEvent;
    return () => {};
  });
  mockStartDrill.mockResolvedValue({ drill_id: "drill-abc", status: "running", max_rounds: 5 });
  mockAbortDrill.mockResolvedValue({ drill_id: "drill-abc", status: "aborted" });
});

describe("CyberDrillPanel R19f 切页恢复", () => {
  it("运行中切页再切回：进度立即还原，Stop 可用（ref 不被卸载清理置空）", async () => {
    // 第一段：开始一场演练
    const { unmount } = render(<CyberDrillPanel />);
    fireEvent.click(screen.getByRole("button", { name: "▶ 开始演练" }));
    await waitFor(() => expect(mockOpenStream).toHaveBeenCalledWith("drill-abc", expect.anything(), expect.anything()));
    // 模拟收到一轮
    act(() => {
      capturedOnEvent!({ name: "drill_round", data: roundData(1) });
    });
    expect(screen.getByText("Round 1")).toBeDefined();
    unmount();

    // 第二段：切回页面，重新挂载（快照恢复 running → 接管）
    render(<CyberDrillPanel />);
    // 快照里有 Round 1，接管 getDrill 成功
    await waitFor(() => expect(screen.getByText("Round 1")).toBeDefined());
    // 关键回归断言：Stop 按钮存在且未被禁用——旧 bug 下 drillIdRef 被卸载
    // 清理置空，handleStop 直接 return，点击毫无反应
    const stopBtn = screen.getByText("⏹ Stop") as HTMLButtonElement;
    expect(stopBtn.disabled).toBe(false);
    fireEvent.click(stopBtn);
    await waitFor(() => expect(mockAbortDrill).toHaveBeenCalledWith("drill-abc"));
  });

  it("运行中切回后兜底轮询持续工作：3s 内拉取服务端实时进度", async () => {
    vi.useFakeTimers();
    try {
      // 直接预置 running 快照（模拟切走时面板正在跑）
      sessionStorage.setItem(
        "aegis.cyber-drill.snapshot",
        JSON.stringify({
          drillId: "drill-abc",
          phase: "running",
          rounds: [roundData(1)],
          summary: null,
          reportMd: null,
          agentTrace: [],
          stage: null,
          elapsed: 30,
          liveMaxRounds: 5,
        }),
      );
      render(<CyberDrillPanel />);
      // 挂载后接管 effect 拉取一次
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(mockGetDrill).toHaveBeenCalledWith("drill-abc");
      const callsAfterMount = mockGetDrill.mock.calls.length;
      // 3s 兜底轮询应继续触发（旧 bug：drillIdRef 为 null → tick 直接 return）
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3100);
      });
      expect(mockGetDrill.mock.calls.length).toBeGreaterThan(callsAfterMount);
    } finally {
      vi.useRealTimers();
    }
  });

  it("接管后 CoT 时间线与阶段进度从服务端补齐，不再停留「等待首个 agent 启动」", async () => {
    sessionStorage.setItem(
      "aegis.cyber-drill.snapshot",
      JSON.stringify({
        drillId: "drill-abc",
        phase: "running",
        rounds: [roundData(1)],
        summary: null,
        reportMd: null,
        agentTrace: [],
        stage: null,
        elapsed: 30,
        liveMaxRounds: 5,
      }),
    );
    render(<CyberDrillPanel />);
    await waitFor(() => expect(screen.getByText(/检测入侵/)).toBeDefined());
    // 空态文案必须消失
    expect(screen.queryByText("等待首个 agent 启动…")).toBeNull();
    // 阶段徽标显示服务端 current_stage=blue
    await waitFor(() => expect(screen.getAllByText(/蓝队防御/).length).toBeGreaterThanOrEqual(1));
  });
});
