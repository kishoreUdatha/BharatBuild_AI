import { describe, it, expect } from "vitest";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";

// dist/cli.js only exports helpers — the executable entry is dist/index.js,
// which is what package.json `bin` points at. The old test shelled out to
// cli.js, got empty output, and had been failing since it was written.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ENTRY = path.join(ROOT, "dist", "index.js");

function run(...args: string[]): string {
  return execFileSync(process.execPath, [ENTRY, ...args], {
    encoding: "utf8",
    timeout: 60_000,
    cwd: ROOT,
  });
}

describe("CLI integration", () => {
  it("prints a semver version", () => {
    expect(run("--version")).toMatch(/\d+\.\d+\.\d+/);
  });

  it("lists its top-level commands in help", () => {
    const out = run("--help");
    for (const cmd of ["chat", "login", "doctor", "projects", "settings"]) {
      expect(out).toContain(cmd);
    }
  });

  it("exposes the chat command with its TUI-relevant flags", () => {
    const out = run("chat", "--help");
    expect(out).toContain("--no-interactive");
    expect(out).toContain("--model");
    expect(out).toContain("--agent");
  });
});
