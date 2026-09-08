// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R7 新建 LlmModeBadge 组件测试（mock systemApi 断言模式展示与切换）

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// vi.mock 工厂会被提升到文件顶部，变量必须用 vi.hoisted 提前声明
const { getMode, setMode } = vi.hoisted(() => ({
  getMode: vi.fn(),
  setMode: vi.fn(),
}));

vi.mock("@/services/api/system", () => ({
  systemApi: { getMode, setMode },
}));

import { LlmModeBadge } from "../LlmModeBadge";

beforeEach(() => {
  getMode.mockReset();
  setMode.mockReset();
});

describe("LlmModeBadge", () => {
  it("shows real mode with provider/model when backend reports real", async () => {
    getMode.mockResolvedValue({
      mode: "real",
      model: "deepseek-chat",
      provider: "deepseek",
      has_key: true,
      available: ["mock", "real"],
    });
    render(<LlmModeBadge />);
    expect(await screen.findByText("LLM: deepseek (deepseek-chat)")).toBeDefined();
    expect(getMode).toHaveBeenCalledTimes(1);
  });

  it("shows mock mode when backend reports mock", async () => {
    getMode.mockResolvedValue({
      mode: "mock",
      model: "",
      provider: "openai",
      has_key: false,
      available: ["mock"],
    });
    render(<LlmModeBadge />);
    expect(await screen.findByText("LLM: Mock")).toBeDefined();
  });

  it("toggles to mock when clicked in real mode", async () => {
    getMode.mockResolvedValue({
      mode: "real",
      model: "deepseek-chat",
      provider: "deepseek",
      has_key: true,
      available: ["mock", "real"],
    });
    setMode.mockResolvedValue({
      mode: "mock",
      model: "",
      provider: "openai",
      has_key: true,
      available: ["mock", "real"],
    });
    render(<LlmModeBadge />);
    const badge = await screen.findByText("LLM: deepseek (deepseek-chat)");
    fireEvent.click(badge);
    await waitFor(() => expect(setMode).toHaveBeenCalledWith("mock"));
    expect(await screen.findByText("LLM: Mock")).toBeDefined();
  });

  it("does not offer toggle when only mock is available", async () => {
    getMode.mockResolvedValue({
      mode: "mock",
      model: "",
      provider: "openai",
      has_key: false,
      available: ["mock"],
    });
    render(<LlmModeBadge />);
    const badge = await screen.findByText("LLM: Mock");
    expect((badge as HTMLButtonElement).disabled).toBe(true);
  });
});
