import { describe, expect, it } from "vitest";
import { parseChatIntent } from "../chatIntent";

describe("parseChatIntent", () => {
  it("识别明确的中文演练并提取网段和轮数", () => {
    expect(parseChatIntent("请模拟一次完整红蓝紫攻防演练，在 192.168.1.0/24 内完成 3 轮")).toMatchObject({
      kind: "cyber_drill",
      confidence: 0.96,
      targetRange: "192.168.1.0/24",
      maxRounds: 3,
      needsClarification: false,
    });
  });

  it("英文 red-blue-purple 也能启动演练", () => {
    expect(parseChatIntent("run a red-blue-purple drill for 2 rounds")).toMatchObject({
      kind: "cyber_drill",
      maxRounds: 2,
      needsClarification: false,
    });
  });

  it("普通任务不误触发演练", () => {
    expect(parseChatIntent("分析今天的登录异常并生成报告")).toMatchObject({
      kind: "task",
      needsClarification: false,
    });
  });

  it("使用记忆中的安全靶场和轮数作为默认槽位", () => {
    expect(parseChatIntent("模拟一次完整红蓝紫攻防演练", {
      preferred_target_range: "172.16.0.0/16",
      preferred_max_rounds: 4,
    })).toMatchObject({
      targetRange: "172.16.0.0/16",
      maxRounds: 4,
    });
  });

  it("只提到防御但未明确启动时要求确认", () => {
    expect(parseChatIntent("帮我分析这个攻击并给出防御建议")).toMatchObject({
      kind: "cyber_drill",
      confidence: 0.72,
      needsClarification: true,
    });
  });

  it("拒绝公共网段并要求改用安全靶场", () => {
    const intent = parseChatIntent("模拟攻防演练，目标 8.8.8.0/24");
    expect(intent.needsClarification).toBe(true);
    expect(intent.clarification).toContain("私有安全靶场");
  });
});