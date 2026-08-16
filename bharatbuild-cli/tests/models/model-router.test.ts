import { describe, it, expect } from "vitest";
describe("model-router", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/models/model-router.js");
    expect(mod).toBeDefined();
  });
});
