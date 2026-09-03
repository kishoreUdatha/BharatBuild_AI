/**
 * Bugs found by executing every registered tool rather than reading it.
 *
 * Two were silent: git_status returned a filename with its first character
 * missing and misreported unstaged work as staged, and find_files answered
 * "No files found" (isError:false) for any pattern containing a slash. A
 * confident wrong answer is worse than a crash - the model acts on it.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { gitStatus } from "../../src/tools/git/index.js";
import { findFiles } from "../../src/tools/filesystem/index.js";

let dir: string;

beforeAll(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-audit-"));
  const git = (...a: string[]) => execFileSync("git", a, { cwd: dir, stdio: "ignore" });
  git("init", "-q");
  git("config", "user.email", "a@b.c");
  git("config", "user.name", "t");
  fs.writeFileSync(path.join(dir, "alpha.txt"), "one\ntwo\n");
  fs.mkdirSync(path.join(dir, "sub"));
  fs.writeFileSync(path.join(dir, "sub", "gamma.ts"), "export const g = 1;\n");
  git("add", "-A");
  git("commit", "-q", "-m", "initial");
  // Unstaged edit: porcelain writes " M alpha.txt" with a leading space.
  fs.writeFileSync(path.join(dir, "alpha.txt"), "one\nCHANGED\n");
});

afterAll(() => { fs.rmSync(dir, { recursive: true, force: true }); });

describe("git_status", () => {
  it("keeps the whole filename", async () => {
    // runGit did stdout.trim(), which ate porcelain's leading status column on
    // the first line. slice(3) then returned "lpha.txt".
    const r = await gitStatus({ working_dir: dir });
    expect(r.content).toContain("alpha.txt");
    expect(r.content).not.toContain("lpha.txt\n");
    expect(r.isError).toBe(false);
  });

  it("reports an unstaged edit as unstaged", async () => {
    // The same shift moved the unstaged column into the staged one, so an
    // uncommitted edit looked ready to commit.
    const r = await gitStatus({ working_dir: dir });
    const staged = r.content.indexOf("staged for commit");
    const notStaged = r.content.indexOf("not staged");
    expect(notStaged).toBeGreaterThan(-1);
    if (staged > -1) expect(r.content.slice(staged, notStaged)).not.toContain("alpha.txt");
  });
});

describe("find_files", () => {
  const find = async (pattern: string) => (await findFiles({ pattern, directory: dir })).content;

  it("matches a recursive glob", async () => {
    expect(await find("**/*.ts")).toContain("gamma.ts");
  });

  it("matches a directory-qualified glob", async () => {
    // Patterns with a slash were tested against the basename, which can never
    // contain one, so these always came back empty.
    expect(await find("sub/*.ts")).toContain("gamma.ts");
    expect(await find("sub/**")).toContain("gamma.ts");
  });

  it("still matches a bare basename glob at any depth", async () => {
    expect(await find("*.ts")).toContain("gamma.ts");
    expect(await find("*.txt")).toContain("alpha.txt");
  });

  it("keeps substring search working", async () => {
    expect(await find("gamma")).toContain("gamma.ts");
  });

  it("honours ? as a single character", async () => {
    expect(await find("alpha.???")).toContain("alpha.txt");
  });

  it("does not match a single star across a separator", async () => {
    // "*" must stop at "/" or the qualified patterns above mean nothing.
    expect(await find("*/nothing.ts")).toContain("No files found");
  });

  it("reports genuinely absent files as absent", async () => {
    expect(await find("**/nope.*")).toContain("No files found");
  });
});
