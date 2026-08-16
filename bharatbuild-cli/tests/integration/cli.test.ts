import { describe, it, expect } from "vitest";
import { execSync } from "child_process";
describe("CLI integration", () => {
  it("should print version", () => {
    const out = execSync("node dist/cli.js --version 2>&1").toString();
    expect(out).toMatch(/\d+\.\d+\.\d+/);
  });
});
