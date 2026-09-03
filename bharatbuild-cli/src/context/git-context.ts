/**
 * Git state for the system prompt.
 *
 * The agent had a `git_status` tool but started every turn blind, so it spent a
 * round trip discovering what was already modified before it could do anything
 * useful. Knowing the branch and the dirty files up front removes that turn.
 *
 * This lands in the system prompt on every request, so it is deliberately
 * small: a branch line and capped file lists, not a full status dump.
 */

import { execFileSync } from "child_process";

const MAX_FILES_PER_GROUP = 12;
const GIT_TIMEOUT_MS = 2_000;

function git(args: string[], cwd: string): string | null {
  try {
    const out = execFileSync("git", args, {
      cwd,
      encoding: "utf8",
      timeout: GIT_TIMEOUT_MS,
      stdio: ["ignore", "pipe", "ignore"],
    });
    // Trailing whitespace only. `--porcelain=v1` encodes the index state in
    // column 1 and the worktree state in column 2, so an unstaged change looks
    // like " M file". A full trim() ate that leading space on the first line,
    // shifting every column: the file was read as "ase.txt" and reported as
    // staged when it was only modified.
    return out.replace(/\s+$/, "");
  } catch {
    // Not a repo, git missing, or too slow — all mean "no git context".
    return null;
  }
}

function group(label: string, files: string[]): string | null {
  if (files.length === 0) return null;
  const shown = files.slice(0, MAX_FILES_PER_GROUP);
  const extra = files.length - shown.length;
  return `${label}: ${shown.join(", ")}${extra > 0 ? ` (+${extra} more)` : ""}`;
}

/**
 * A compact git summary, or null when the directory is not a git repo.
 * Never throws — a broken git install must not stop a session starting.
 */
export function gitContextSummary(workingDir: string): string | null {
  if (git(["rev-parse", "--git-dir"], workingDir) === null) return null;

  const branch = git(["branch", "--show-current"], workingDir) || "(detached)";
  const porcelain = git(["status", "--porcelain=v1"], workingDir);
  if (porcelain === null) return null;

  const modified: string[] = [];
  const staged: string[] = [];
  const untracked: string[] = [];
  const conflicted: string[] = [];

  for (const line of porcelain.split("\n")) {
    if (!line.trim()) continue;
    const x = line[0] ?? " ";
    const y = line[1] ?? " ";
    const file = line.slice(3).trim();
    if (!file) continue;

    if (x === "?" && y === "?") untracked.push(file);
    else if (x === "U" || y === "U" || (x === "A" && y === "A") || (x === "D" && y === "D")) conflicted.push(file);
    else {
      // The index column and the worktree column are independent: a file can
      // be both staged and modified again since staging.
      if (x !== " " && x !== "?") staged.push(file);
      if (y !== " " && y !== "?") modified.push(file);
    }
  }

  const lines = [`branch: ${branch}`];
  for (const g of [
    group("conflicted", conflicted),
    group("staged", staged),
    group("modified", modified),
    group("untracked", untracked),
  ]) {
    if (g) lines.push(g);
  }
  if (lines.length === 1) lines.push("working tree clean");

  return lines.join("\n");
}
