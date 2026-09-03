/**
 * BharatBuild CLI — Git Tools
 * git_status, git_diff, git_log, git_add, git_commit
 */

import { execFile } from "child_process";
import { promisify } from "util";
import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

const execFileAsync = promisify(execFile);

/** Strip trailing whitespace only - leading columns are significant in porcelain. */
function trimEnd(s: string): string {
  return s.replace(/\s+$/, "");
}

async function runGit(
  args: string[],
  cwd?: string
): Promise<{ stdout: string; stderr: string; ok: boolean }> {
  const gitBin = process.platform === "win32" ? "git.exe" : "git";
  try {
    const { stdout, stderr } = await execFileAsync(gitBin, args, {
      cwd: cwd ?? process.cwd(),
      timeout: 30_000,
      maxBuffer: 1_000_000,
    });
    // Trailing only. `--porcelain` encodes the staged state in column 1 and
    // the unstaged state in column 2, so an unstaged change starts with a
    // space: " M alpha.txt". A full .trim() ate that column on the first line,
    // which shifted everything left by one - the file was reported as staged
    // when it was not, and `line.slice(3)` returned "lpha.txt" instead of
    // "alpha.txt". The model then went looking for a file that did not exist.
    return { stdout: trimEnd(stdout), stderr: trimEnd(stderr), ok: true };
  } catch (err: unknown) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    return { stdout: trimEnd(e.stdout ?? ""), stderr: trimEnd(e.stderr ?? e.message ?? ""), ok: false };
  }
}

// ── git_status ────────────────────────────────────────────────────────────────

export const gitStatusDefinition: ToolDefinition = {
  name: "git_status",
  description: "Show the working tree status — staged, unstaged, and untracked files.",
  input_schema: {
    type: "object",
    properties: { working_dir: { type: "string", description: "Git repo directory (default: cwd)" } },
    required: [],
  },
};

function codeLabel(c: string): string {
  switch (c) {
    case "M": return "modified:  ";
    case "A": return "new file:  ";
    case "D": return "deleted:   ";
    case "R": return "renamed:   ";
    case "C": return "copied:    ";
    case "U": return "conflict:  ";
    default: return `${c}:         `;
  }
}

export async function gitStatus(input: { working_dir?: string }): Promise<ToolResult> {
  const check = await runGit(["rev-parse", "--git-dir"], input.working_dir);
  if (!check.ok) return { content: "Not a git repository (or git is not installed).", isError: true };

  const [status, branch] = await Promise.all([
    runGit(["status", "--porcelain=v1"], input.working_dir),
    runGit(["branch", "--show-current"], input.working_dir),
  ]);

  const branchName = branch.stdout || "detached HEAD";
  if (!status.stdout) return { content: `On branch ${branchName}\n\nNothing to commit, working tree clean.`, isError: false };

  const lines = status.stdout.split("\n");
  const staged: string[] = [], unstaged: string[] = [], untracked: string[] = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    const x = line[0] ?? " ", y = line[1] ?? " ", file = line.slice(3);
    if (x !== " " && x !== "?") staged.push(`  ${codeLabel(x)}${file}`);
    if (y !== " " && y !== "?") unstaged.push(`  ${codeLabel(y)}${file}`);
    if (x === "?" && y === "?") untracked.push(`  ?? ${file}`);
  }
  let out = `On branch ${branchName}\n`;
  if (staged.length) out += `\nChanges staged for commit:\n${staged.join("\n")}`;
  if (unstaged.length) out += `\nChanges not staged:\n${unstaged.join("\n")}`;
  if (untracked.length) out += `\nUntracked files:\n${untracked.join("\n")}`;
  return { content: out, isError: false };
}

// ── git_diff ──────────────────────────────────────────────────────────────────

export const gitDiffDefinition: ToolDefinition = {
  name: "git_diff",
  description: "Show changes between working tree and index (or staged changes).",
  input_schema: {
    type: "object",
    properties: {
      file_path: { type: "string", description: "Specific file to diff (optional)" },
      staged: { type: "boolean", description: "Show staged changes (default: false)" },
      working_dir: { type: "string", description: "Git repo directory" },
    },
    required: [],
  },
};

export async function gitDiff(input: { file_path?: string; staged?: boolean; working_dir?: string }): Promise<ToolResult> {
  const check = await runGit(["rev-parse", "--git-dir"], input.working_dir);
  if (!check.ok) return { content: "Not a git repository.", isError: true };
  const args = ["diff"];
  if (input.staged) args.push("--staged");
  if (input.file_path) args.push("--", input.file_path);
  const result = await runGit(args, input.working_dir);
  if (!result.stdout && !result.stderr) {
    return { content: `No ${input.staged ? "staged" : "unstaged"} changes.`, isError: false };
  }
  if (!result.ok) return { content: `git diff failed: ${result.stderr}`, isError: true };
  return { content: result.stdout, isError: false };
}

// ── git_log ───────────────────────────────────────────────────────────────────

export const gitLogDefinition: ToolDefinition = {
  name: "git_log",
  description: "Show the commit log with author, date, and message.",
  input_schema: {
    type: "object",
    properties: {
      limit: { type: "number", description: "Number of commits (default: 10)" },
      file_path: { type: "string", description: "Show commits for specific file" },
      working_dir: { type: "string", description: "Git repo directory" },
    },
    required: [],
  },
};

export async function gitLog(input: { limit?: number; file_path?: string; working_dir?: string }): Promise<ToolResult> {
  const check = await runGit(["rev-parse", "--git-dir"], input.working_dir);
  if (!check.ok) return { content: "Not a git repository.", isError: true };
  const args = ["log", `--max-count=${input.limit ?? 10}`, "--format=%H|%an|%ar|%s"];
  if (input.file_path) args.push("--", input.file_path);
  const result = await runGit(args, input.working_dir);
  if (!result.ok) return { content: `git log failed: ${result.stderr}`, isError: true };
  if (!result.stdout) return { content: "No commits found.", isError: false };
  const lines = result.stdout.split("\n").map((line) => {
    const [hash, author, time, ...msg] = line.split("|");
    return `${(hash ?? "").slice(0, 7)}  ${(author ?? "").padEnd(16)}  ${(time ?? "").padEnd(14)}  ${msg.join("|")}`;
  });
  const header = `${"HASH   ".padEnd(9)}${"AUTHOR".padEnd(18)}${"WHEN".padEnd(16)}MESSAGE\n${"─".repeat(70)}`;
  return { content: `${header}\n${lines.join("\n")}`, isError: false };
}

// ── git_add ───────────────────────────────────────────────────────────────────

export const gitAddDefinition: ToolDefinition = {
  name: "git_add",
  description: "Stage files for commit. Use paths=['.'] to stage all changes.",
  input_schema: {
    type: "object",
    properties: {
      paths: { type: "array", items: { type: "string" }, description: "File paths to stage. Use ['.'] for all." },
      working_dir: { type: "string", description: "Git repo directory" },
    },
    required: ["paths"],
  },
};

export async function gitAdd(input: { paths: string[]; working_dir?: string }): Promise<ToolResult> {
  const check = await runGit(["rev-parse", "--git-dir"], input.working_dir);
  if (!check.ok) return { content: "Not a git repository.", isError: true };
  if (!input.paths.length) return { content: "No paths specified.", isError: true };
  const result = await runGit(["add", ...input.paths], input.working_dir);
  if (!result.ok) return { content: `git add failed: ${result.stderr}`, isError: true };
  const status = await runGit(["status", "--short"], input.working_dir);
  return { content: `Staged: ${input.paths.join(", ")}\n\nStatus:\n${status.stdout || "(clean)"}`, isError: false };
}

// ── git_commit ────────────────────────────────────────────────────────────────

export const gitCommitDefinition: ToolDefinition = {
  name: "git_commit",
  description: "Commit staged changes. Will NOT push.",
  input_schema: {
    type: "object",
    properties: {
      message: { type: "string", description: "Commit message (required)" },
      working_dir: { type: "string", description: "Git repo directory" },
    },
    required: ["message"],
  },
};

export async function gitCommit(input: { message: string; working_dir?: string }): Promise<ToolResult> {
  const check = await runGit(["rev-parse", "--git-dir"], input.working_dir);
  if (!check.ok) return { content: "Not a git repository.", isError: true };
  if (!input.message.trim()) return { content: "Commit message cannot be empty.", isError: true };
  const staged = await runGit(["diff", "--staged", "--name-only"], input.working_dir);
  if (!staged.stdout) return { content: "Nothing staged to commit. Use git_add first.", isError: true };
  const result = await runGit(["commit", "-m", input.message], input.working_dir);
  if (!result.ok) return { content: `git commit failed: ${result.stderr}`, isError: true };
  const hash = (await runGit(["rev-parse", "--short", "HEAD"], input.working_dir)).stdout;
  return { content: `Committed [${hash}]: ${input.message}\n\n${result.stdout}`, isError: false };
}
