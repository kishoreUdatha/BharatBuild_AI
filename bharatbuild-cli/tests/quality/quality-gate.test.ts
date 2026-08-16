import { describe, it, expect } from "vitest";
describe("quality-gate", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/quality/quality-gate.js");
    expect(mod).toBeDefined();
  });
});
