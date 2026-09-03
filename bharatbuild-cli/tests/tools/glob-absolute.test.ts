/**
 * A glob pattern that carries its own absolute root.
 *
 * Models write patterns this way constantly — `D:\proj\**\*.json` with no
 * separate `path` argument. The root was taken from `path` alone, so the walk
 * started in the current directory while the pattern was anchored somewhere
 * else, and nothing ever matched. The reported failure said it out loud
 * without anyone noticing:
 *
 *   No files found matching 'D:\Smartgrow Projects\BharatBuild_AI\**\*.json'
 *   in 'C:\Users\user'
 *
 * Two different places in one sentence.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { splitAbsolutePattern } from "../../src/tools/built-in/glob.js";
import { globTool } from "../../src/tools/built-in/glob.js";

describe("splitting an absolute pattern", () => {
  it("separates the root from the wildcard tail", () => {
    const posix = splitAbsolutePattern("/home/me/proj/**/*.json");
    expect(posix.root).toBe("/home/me/proj");
    expect(posix.pattern).toBe("**/*.json");
  });

  it("handles a windows path with backslashes", () => {
    const win = splitAbsolutePattern("D:\\proj\\src\\**\\*.ts");
    expect(win.root).toBe("D:/proj/src");
    expect(win.pattern).toBe("**/*.ts");
  });

  it("splits at the first wildcard, not the last", () => {
    const r = splitAbsolutePattern("/a/b/**/c/*.ts");
    expect(r.root).toBe("/a/b");
    expect(r.pattern).toBe("**/c/*.ts");
  });

  it("leaves a relative pattern alone", () => {
    // The overwhelmingly common case must be untouched.
    const rel = splitAbsolutePattern("src/**/*.ts");
    expect(rel.root).toBeUndefined();
    expect(rel.pattern).toBe("src/**/*.ts");
  });

  it("treats an absolute path with no wildcard as one named file", () => {
    const r = splitAbsolutePattern("/etc/hosts");
    expect(r.root).toBe("/etc");
    expect(r.pattern).toBe("hosts");
  });

  it("recognises a brace group as a wildcard segment", () => {
    const r = splitAbsolutePattern("/a/b/{x,y}/*.ts");
    expect(r.root).toBe("/a/b");
  });
});

describe("the tool, end to end", () => {
  let dir: string;
  let elsewhere: string;

  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-glob-"));
    elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), "bb-elsewhere-"));
    fs.mkdirSync(path.join(dir, "src"));
    fs.writeFileSync(path.join(dir, "src", "a.json"), "{}");
    fs.writeFileSync(path.join(dir, "src", "b.ts"), "x");
  });
  afterEach(() => {
    for (const d of [dir, elsewhere]) {
      try { fs.rmSync(d, { recursive: true, force: true }); } catch { /* windows lock */ }
    }
  });

  it("finds files when the pattern carries the root and no path is given", async () => {
    // The exact failure from the transcript: absolute pattern, no `path`.
    const res = await globTool.execute({ pattern: path.join(dir, "**", "*.json") });
    expect(res.content).toContain("a.json");
  });

  it("does not search the current directory for an absolute pattern", async () => {
    const res = await globTool.execute({ pattern: path.join(dir, "**", "*.json") });
    expect(res.content).not.toContain(process.cwd());
  });

  it("still honours an explicit path argument", async () => {
    // `path` is the caller being specific, so it wins over the pattern's root.
    const res = await globTool.execute({ pattern: "**/*.ts", path: dir });
    expect(res.content).toContain("b.ts");
  });

  it("reports the directory it actually searched when nothing matches", async () => {
    // The old message named the pattern's root while having searched cwd.
    const res = await globTool.execute({ pattern: path.join(elsewhere, "**", "*.json") });
    expect(res.content).toMatch(/No files found/);
    expect(res.content).toContain(elsewhere.replace(/\\/g, path.sep));
  });

  it("still works with an ordinary relative pattern", async () => {
    const res = await globTool.execute({ pattern: "**/*.json", path: dir });
    expect(res.content).toContain("a.json");
  });
});
