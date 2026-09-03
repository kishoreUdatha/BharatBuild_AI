/**
 * Tool cards showed whatever absolute path the model sent:
 *
 *   ● write_file(C:\Users\user\PalindromeChecker.java)
 *
 * Most of that is noise. The reference CLIs show the path relative to the
 * working directory, which is also how a person would refer to the file.
 */
import { describe, it, expect } from "vitest";
import path from "node:path";
import os from "node:os";
import { displayPath, looksLikePath } from "../../src/infra/display-path.js";

const CWD = path.resolve(path.sep === "\\" ? "C:\\proj\\app" : "/proj/app");

describe("paths inside the project", () => {
  it("drops the leading directories", () => {
    expect(displayPath(path.join(CWD, "src", "Login.tsx"), CWD)).toBe("src/Login.tsx");
  });

  it("uses forward slashes whatever the platform", () => {
    // A path is read, quoted and pasted; mixed separators make that awkward.
    expect(displayPath(path.join(CWD, "a", "b", "c.ts"), CWD)).toBe("a/b/c.ts");
  });

  it("leaves an already-relative path alone", () => {
    expect(displayPath("src/index.ts", CWD)).toBe("src/index.ts");
  });
});

describe("paths outside the project", () => {
  it("keeps a system path intact rather than shortening it", () => {
    // Collapsing /etc/hosts to "hosts" would hide the one case most worth
    // noticing — a write landing outside the project.
    const target = path.sep === "\\"
      ? "C:\\Windows\\System32\\drivers\\etc\\hosts"
      : "/etc/hosts";
    const shown = displayPath(target, CWD);
    expect(shown).toContain("etc");
    expect(shown).not.toBe("hosts");
  });

  it("uses ~ for the home directory", () => {
    const target = path.join(os.homedir(), "PalindromeChecker.java");
    expect(displayPath(target, CWD)).toBe("~/PalindromeChecker.java");
  });

  it("does not claim a sibling directory is inside the project", () => {
    // "../other/x.ts" must not be reported as "other/x.ts".
    const sibling = path.join(path.dirname(CWD), "other", "x.ts");
    expect(displayPath(sibling, CWD)).not.toBe("other/x.ts");
  });
});

describe("degenerate input", () => {
  it("passes an empty string through", () => {
    expect(displayPath("", CWD)).toBe("");
  });

  it("handles the working directory itself", () => {
    expect(() => displayPath(CWD, CWD)).not.toThrow();
  });
});

describe("telling a path from a command", () => {
  it("recognises paths", () => {
    expect(looksLikePath("src/a.ts")).toBe(true);
    expect(looksLikePath("App.java")).toBe(true);
    expect(looksLikePath("C:\\Users\\user\\x.py")).toBe(true);
  });

  it("does not mistake a shell command for one", () => {
    // A command is shown exactly as written: shortening it would misreport
    // what actually ran.
    expect(looksLikePath("npm run build")).toBe(false);
    expect(looksLikePath("git status")).toBe(false);
    expect(looksLikePath("")).toBe(false);
  });
});
