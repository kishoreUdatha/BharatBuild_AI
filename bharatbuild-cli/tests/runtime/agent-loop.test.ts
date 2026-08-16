import { describe, it, expect } from "vitest";
describe("agent-loop", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/runtime/agent-loop.js");
    expect(mod).toBeDefined();
  });
});
