import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

const state = {
  tasks: [
    { task_id: "recon", goal: "侦察目标", status: "succeeded", priority: 3, dependency: [] },
    { task_id: "correlate", goal: "关联漏洞", status: "running", priority: 2, dependency: ["recon"] },
    { task_id: "review", goal: "审查结果", status: "pending", priority: 1, dependency: ["correlate"] },
  ],
};

vi.mock("@/lib/store", () => ({
  useAppStore: (selector: (value: typeof state) => unknown) => selector(state),
}));

describe("CanvasView", () => {
  it("renders tasks in dependency stages", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    expect(screen.getByText("阶段 1")).toBeDefined();
    expect(screen.getByText("阶段 2")).toBeDefined();
    expect(screen.getByText("阶段 3")).toBeDefined();
    expect(screen.getAllByText("侦察目标").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("审查结果")).toBeDefined();
  });

  it("filters tasks by status", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    fireEvent.click(screen.getByRole("button", { name: "执行中" }));
    expect(screen.getByText("1 个任务")).toBeDefined();
    expect(screen.getAllByText("关联漏洞").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("侦察目标")).toBeNull();
  });

  it("shows selected task details after clicking a node", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    fireEvent.click(screen.getByRole("button", { name: /审查结果/ }));
    expect(screen.getByRole("complementary", { name: "任务详情" })).toBeDefined();
    expect(screen.getByText("correlate")).toBeDefined();
  });
});
