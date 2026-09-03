/**
 * The agent had a git_status tool but began every turn blind, so it burned a
 * round trip discovering what was already modified. This puts branch + dirty
 * files in the system prompt instead.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { execFileSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { gitContextSummary } from "../../src/context/git-context.js";

let dir: string;

const git = (...args: string[]) =>
  execFileSync("git", args, { cwd: dir, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-git-"));
});
afterEach(() => {
  fs.rmSync(dir, { recursive: true, force: true });
});

function initRepo() {
  git("init", "-q");
  git("config", "user.email", "t@example.com");
  git("config", "user.name", "T");
  git("config", "commit.gpgsign", "false");
  fs.writeFileSync(path.join(dir, "base.txt"), "base\n");
  git("add", ".");
  git("commit", "-q", "-m", "init");
}

describe("gitContextSummary", () => {
  it("returns null outside a git repository", () => {
    expect(gitContextSummary(dir)).toBeNull();
  });

  it("returns null for a path that does not exist", () => {
    expect(gitContextSummary(path.join(dir, "nope"))).toBeNull();
  });

  it("reports the branch on a clean tree", () => {
    initRepo();
    const s = gitContextSummary(dir)!;
    expect(s).toContain("branch:");
    expect(s).toContain("working tree clean");
  });

  it("lists modified files", () => {
    initRepo();
    fs.writeFileSync(path.join(dir, "base.txt"), "changed\n");
    const s = gitContextSummary(dir)!;
    expect(s).toContain("modified: base.txt");
    expect(s).not.toContain("working tree clean");
  });

  it("lists untracked files", () => {
    initRepo();
    fs.writeFileSync(path.join(dir, "fresh.txt"), "x\n");
    expect(gitContextSummary(dir)!).toContain("untracked: fresh.txt");
  });

  it("separates staged from unstaged", () => {
    initRepo();
    fs.writeFileSync(path.join(dir, "staged.txt"), "a\n");
    git("add", "staged.txt");
    fs.writeFileSync(path.join(dir, "base.txt"), "edited\n");
    const s = gitContextSummary(dir)!;
    expect(s).toContain("staged: staged.txt");
    expect(s).toContain("modified: base.txt");
  });

  it("caps long file lists so the prompt stays small", () => {
    initRepo();
    for (let i = 0; i < 30; i++) fs.writeFileSync(path.join(dir, `f${i}.txt`), "x\n");
    const s = gitContextSummary(dir)!;
    expect(s).toMatch(/\(\+\d+ more\)/);
    // 30 untracked files must not produce 30 entries.
    expect(s.split("untracked:")[1]!.split(",").length).toBeLessThanOrEqual(13);
  });

  it("stays compact enough to sit in every request", () => {
    initRepo();
    for (let i = 0; i < 30; i++) fs.writeFileSync(path.join(dir, `f${i}.txt`), "x\n");
    expect(gitContextSummary(dir)!.length).toBeLessThan(2000);
  });
});
