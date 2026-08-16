import { describe, it, expect } from "vitest";
describe("filesystem tools", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/tools/filesystem/index.js");
    expect(mod).toBeDefined();
  });
});
