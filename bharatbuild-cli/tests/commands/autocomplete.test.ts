/**
 * `bharatbuild autocomplete bash` installed a PowerShell script and then told
 * the user to `source` the .ps1 from ~/.bashrc. The shell argument was
 * effectively ignored on Windows:
 *
 *   detected.includes("powershell") || process.platform === "win32"
 *
 * The second clause swallowed every non-zsh shell. The platform is a fallback
 * for when no shell was requested, not an override of one that was.
 */
import { describe, it, expect, afterEach } from "vitest";
import { resolveShell, completionFor, SUPPORTED_SHELLS } from "../../src/infra/autocomplete.js";

const originalShell = process.env["SHELL"];
afterEach(() => {
  if (originalShell === undefined) delete process.env["SHELL"];
  else process.env["SHELL"] = originalShell;
});

describe("an explicitly requested shell", () => {
  it("is honoured, whatever the platform", () => {
    // The whole bug in one assertion: on win32 this returned "powershell".
    expect(resolveShell("bash")).toBe("bash");
    expect(resolveShell("zsh")).toBe("zsh");
    expect(resolveShell("powershell")).toBe("powershell");
  });

  it("accepts pwsh as powershell", () => {
    expect(resolveShell("pwsh")).toBe("powershell");
  });

  it("ignores case and stray whitespace", () => {
    expect(resolveShell("  BASH ")).toBe("bash");
  });

  it("refuses a shell it cannot generate for, naming the options", () => {
    // fish silently received a PowerShell script before.
    expect(() => resolveShell("fish")).toThrow(/unsupported shell 'fish'/i);
    expect(() => resolveShell("fish")).toThrow(/bash, zsh, powershell/);
  });
});

describe("auto-detection when nothing was requested", () => {
  it("follows $SHELL when it is set", () => {
    process.env["SHELL"] = "/usr/bin/zsh";
    expect(resolveShell()).toBe("zsh");
    process.env["SHELL"] = "/bin/bash";
    expect(resolveShell()).toBe("bash");
  });

  it("handles a Windows-style path in $SHELL", () => {
    process.env["SHELL"] = "C:\\Program Files\\Git\\bin\\bash.exe";
    expect(resolveShell()).toBe("bash");
  });

  it("falls back to the platform only when $SHELL says nothing", () => {
    delete process.env["SHELL"];
    expect(resolveShell()).toBe(process.platform === "win32" ? "powershell" : "bash");
  });
});

describe("the script matches the shell", () => {
  it("gives each shell its own script and location", () => {
    const bash = completionFor("bash");
    const zsh = completionFor("zsh");
    const ps = completionFor("powershell");

    expect(bash.script).not.toBe(ps.script);
    expect(bash.installPath).not.toBe(ps.installPath);
    expect(zsh.installPath).not.toBe(bash.installPath);
  });

  it("does not hand a bash user a .ps1", () => {
    // The exact wrong pairing that shipped.
    expect(completionFor("bash").installPath).not.toMatch(/\.ps1$/);
    expect(completionFor("powershell").installPath).toMatch(/\.ps1$/);
  });

  it("gives bash a bashrc hint and powershell a profile hint", () => {
    expect(completionFor("bash").hint).toMatch(/bashrc/);
    expect(completionFor("powershell").hint).toMatch(/profile/i);
    expect(completionFor("bash").hint).not.toMatch(/profile/i);
  });

  it("covers every shell it advertises", () => {
    // A shell in the list with no case here would throw at runtime.
    for (const shell of SUPPORTED_SHELLS) {
      expect(() => completionFor(shell), shell).not.toThrow();
      expect(completionFor(shell).script.length, shell).toBeGreaterThan(0);
    }
  });
});
