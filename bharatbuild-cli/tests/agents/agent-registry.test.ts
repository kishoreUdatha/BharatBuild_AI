import { describe, it, expect } from "vitest";
describe("agent-registry", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/agents/agent-registry.js");
    expect(mod).toBeDefined();
  });
});
