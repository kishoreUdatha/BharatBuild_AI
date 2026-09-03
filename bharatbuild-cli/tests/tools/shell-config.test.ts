/**
 * Which shell runs a command.
 *
 * It was cmd.exe on Windows and /bin/sh elsewhere, and both hurt:
 *
 *   - cmd.exe eats the inner quotes of a nested invocation, so
 *     `powershell -Command "Write-Output ok"` came back as its own text.
 *     Indistinguishable from a command that prints that text, so the agent
 *     retried variants that all "worked" and did nothing — including a
 *     90-second sleep that never elapsed.
 *   - /bin/sh is not bash, and models write bash.
 *
 * The Windows console also defaults to a legacy codepage, so a program
 * printing anything outside cp1252 dies with UnicodeEncodeError. That
 * happened, and the agent "fixed" it by deleting the offending characters
 * from the program it had just written.
 */
import { describe, it, expect } from "vitest";
import {
  getShellConfiguration, withUtf8, describeShell, resolveExecutable,
} from "../../src/tools/shell/shell-config.js";
import { executeCommand } from "../../src/tools/shell/index.js";

const onWindows = process.platform === "win32";

describe("choosing the shell", () => {
  it("never picks cmd.exe on Windows", () => {
    const c = getShellConfiguration("win32");
    expect(c.executable.toLowerCase()).not.toContain("cmd.exe");
    expect(c.kind).toBe("powershell");
  });

  it("passes -NoProfile so a user profile cannot alter the run", () => {
    expect(getShellConfiguration("win32").argsPrefix).toContain("-NoProfile");
  });

  it("prefers bash over sh on unix", () => {
    const c = getShellConfiguration("linux");
    expect(["bash", "sh"]).toContain(c.kind);
    if (resolveExecutable("bash")) expect(c.kind).toBe("bash");
  });

  it("takes the command as one argument, not a re-parsed string", () => {
    // The cmd.exe failure was quote re-parsing; both replacements accept the
    // command whole.
    expect(getShellConfiguration("win32").argsPrefix.at(-1)).toBe("-Command");
    expect(getShellConfiguration("linux").argsPrefix.at(-1)).toBe("-c");
  });
});

describe("telling the model which shell it has", () => {
  it("names PowerShell, and says what it is not", () => {
    const d = describeShell(getShellConfiguration("win32"));
    expect(d).toMatch(/PowerShell/);
    expect(d).toMatch(/not cmd\.exe/);
    expect(d).toMatch(/not bash/);
  });
});

describe("console encoding", () => {
  it("switches PowerShell to UTF-8 before the command", () => {
    const out = withUtf8("Write-Output hi", getShellConfiguration("win32"));
    expect(out).toContain("chcp 65001");
    expect(out.indexOf("chcp")).toBeLessThan(out.indexOf("Write-Output"));
  });

  it("leaves unix alone, where UTF-8 is already the default", () => {
    expect(withUtf8("echo hi", getShellConfiguration("linux"))).toBe("echo hi");
  });
});

describe("the commands that failed before", () => {
  it.runIf(onWindows)("runs a nested PowerShell command instead of echoing it", async () => {
    const r = await executeCommand({ command: `powershell -NoProfile -Command "Write-Output ok"` });
    expect(r.content).toContain("ok");
    expect(r.content).not.toContain("Write-Output ok");
  });

  it.runIf(onWindows)("actually sleeps when told to", async () => {
    const began = Date.now();
    await executeCommand({ command: "Start-Sleep -Milliseconds 400; Write-Output slept" });
    expect(Date.now() - began).toBeGreaterThan(300);
  });

  it.runIf(onWindows)("prints characters outside the legacy codepage", async () => {
    const r = await executeCommand({ command: `Write-Output "check ✓"` });
    expect(r.content).toContain("✓");
  });

  it("still runs an ordinary command", async () => {
    const r = await executeCommand({ command: "node -v" });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/v\d+/);
  });

  it("still reports a failure as a failure", async () => {
    const r = await executeCommand({ command: "node -e \"process.exit(3)\"" });
    expect(r.isError).toBe(true);
  });
});
