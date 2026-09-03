import { describe, it, expect } from "vitest";
import path from "path";
import { isProtectedPath, isOutsideProject } from "../../src/permissions/path-policy.js";

const isWindows = process.platform === "win32";

describe("isProtectedPath", () => {
  it("blocks POSIX system roots", () => {
    // On Windows these resolve onto the current drive, which used to make the
    // whole POSIX list dead code.
    for (const p of ["/etc/passwd", "/sys/kernel", "/proc/1/mem", "/boot/grub"]) {
      expect(isProtectedPath(p), p).toBe(true);
    }
  });

  it("does not treat a lookalike prefix as protected", () => {
    // "/etcetera" is not inside "/etc".
    expect(isProtectedPath("/etcetera/notes.txt")).toBe(false);
  });

  it("allows ordinary project files", () => {
    expect(isProtectedPath("src/index.ts")).toBe(false);
    expect(isProtectedPath("./README.md")).toBe(false);
  });

  it("ignores empty input", () => {
    expect(isProtectedPath("")).toBe(false);
    expect(isProtectedPath("   ")).toBe(false);
  });

  it.runIf(isWindows)("blocks Windows system directories regardless of case", () => {
    expect(isProtectedPath("C:\\Windows\\System32\\drivers\\etc\\hosts")).toBe(true);
    expect(isProtectedPath("c:\\windows\\system32\\cmd.exe")).toBe(true);
    expect(isProtectedPath("C:\\Program Files\\app\\x.dll")).toBe(true);
  });

  it.runIf(isWindows)("blocks system directories on non-C drives", () => {
    expect(isProtectedPath("D:\\Windows\\System32\\x")).toBe(true);
  });

  it.runIf(isWindows)("allows a normal path on the same drive", () => {
    expect(isProtectedPath("C:\\Users\\me\\project\\src\\a.ts")).toBe(false);
  });
});

describe("isOutsideProject", () => {
  const root = path.resolve("project-root");

  it("accepts files inside the project", () => {
    expect(isOutsideProject(path.join(root, "src", "a.ts"), root)).toBe(false);
  });

  it("rejects a parent-directory escape", () => {
    expect(isOutsideProject(path.join(root, "..", "secrets.txt"), root)).toBe(true);
  });

  it("does not confuse a sibling with the same prefix", () => {
    // A plain startsWith check called "project-root-2" part of "project-root".
    expect(isOutsideProject(path.resolve("project-root-2", "a.ts"), root)).toBe(true);
  });
});
