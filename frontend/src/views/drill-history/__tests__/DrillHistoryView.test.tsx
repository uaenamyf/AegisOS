import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DrillHistoryView } from "../DrillHistoryView";

const { mockListDrills, mockGetDrill, mockGetDrillReport } = vi.hoisted(() => ({
  mockListDrills: vi.fn(),
  mockGetDrill: vi.fn(),
  mockGetDrillReport: vi.fn(),
}));

vi.mock("@/services/api/cyber", () => ({
  cyberApi: {
    listDrills: mockListDrills,
    getDrill: mockGetDrill,
    getDrillReport: mockGetDrillReport,
  },
}));

const meta = {
  drill_id: "drill-demo-01",
  target_range: "10.0.0.0/24",
  rounds_executed: 1,
  convergence_code: "max_rounds",
  created_at: "2026-09-10T10:00:00",
};

const record = {
  ...meta,
  max_rounds: 1,
  summary: { conclusion: "演练完成", convergence_code: "max_rounds", rounds_executed: 1 },
  rounds: [{
    round: 1,
    convergence_code: "max_rounds",
    red: { finding_count: 2, new_steps: [{ technique: "T1190" }], agent_trace: [{ agent: "recon", input: "Scan target", output: { assets: ["asset-1"] } }] },
    blue: { triaged_count: 1, plan: { actions: [{ action_id: "a1" }] }, agent_trace: [] },
    purple: { valid: false, new_issue_count: 1, agent_trace: [{ agent: "critic", input: "Critique chain", output: { valid: false } }] },
    event_stream: [],
  }],
};

describe("DrillHistoryView", () => {
  it("loads history and shows red blue purple evidence", async () => {
    mockListDrills.mockResolvedValue({ drills: [meta] });
    mockGetDrill.mockResolvedValue(record);
    render(<DrillHistoryView />);

    expect(await screen.findByText("drill-demo-01")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /drill-demo-01/ }));

    await waitFor(() => expect(screen.getByText("第 1 轮")).toBeDefined());
    expect(screen.getByText("红队")).toBeDefined();
    expect(screen.getByText("蓝队")).toBeDefined();
    expect(screen.getByText("紫队")).toBeDefined();
    expect(screen.getByText("1 个缺口")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /第 1 轮/ }));
    expect(screen.getByText("recon")).toBeDefined();
    expect(screen.getByText("critic")).toBeDefined();
    expect(screen.getByText("Scan target")).toBeDefined();
    expect(screen.getByText(/"valid": false/)).toBeDefined();

    mockGetDrillReport.mockResolvedValue({ drill_id: meta.drill_id, report_md: "# 演练报告\n\n内容" });
    const createObjectURL = vi.fn().mockReturnValue("blob:report");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const createElement = vi.spyOn(document, "createElement");
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    fireEvent.click(screen.getByRole("button", { name: "↓ 导出 Markdown" }));
    await waitFor(() => expect(mockGetDrillReport).toHaveBeenCalledWith(meta.drill_id));
    expect(click).toHaveBeenCalled();
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:report");
    const anchorResult = createElement.mock.results.find((result) => result.type === "return" && result.value instanceof HTMLAnchorElement);
    const anchor = anchorResult?.type === "return" ? anchorResult.value as HTMLAnchorElement : null;
    expect(anchor).not.toBeNull();
    if (!anchor) throw new Error("download anchor was not created");
    expect(anchor.download).toBe(`${meta.drill_id}.md`);
    createElement.mockRestore();
    click.mockRestore();
  });
});
