/**
 * Talking to GitHub through the `gh` CLI.
 *
 * Deliberately not a REST client. Authentication is the hard part of GitHub
 * integration — tokens, SSO, enterprise hosts, keyring storage — and `gh`
 * already solves it, per-machine, outside this codebase. Reimplementing that
 * would mean storing credentials we have no business holding.
 *
 * The cost is a dependency the user must install. That is worth stating
 * plainly when it is missing rather than failing with a confusing error.
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const GH_TIMEOUT_MS = 30_000;

export interface GhResult {
  ok: boolean;
  stdout: string;
  stderr: string;
}

/** Run `gh` with the given arguments. Never goes through a shell. */
export async function runGh(args: string[], cwd?: string): Promise<GhResult> {
  try {
    const { stdout, stderr } = await execFileAsync("gh", args, {
      cwd: cwd ?? process.cwd(),
      timeout: GH_TIMEOUT_MS,
      maxBuffer: 4_000_000,
      // No shell: arguments are passed as an array, so a title containing
      // quotes or semicolons cannot turn into extra commands.
      shell: false,
    });
    return { ok: true, stdout: stdout.trim(), stderr: stderr.trim() };
  } catch (err: unknown) {
    const e = err as { stdout?: string; stderr?: string; message?: string; code?: string };
    return {
      ok: false,
      stdout: (e.stdout ?? "").trim(),
      stderr: (e.stderr ?? e.message ?? "").trim(),
    };
  }
}

/**
 * Why a GitHub call cannot proceed, or null when it can.
 *
 * Checked before every call so the failure names the actual problem — "gh is
 * not installed" rather than a spawn error, and "not logged in" rather than a
 * 401 buried in stderr.
 */
export async function githubUnavailableReason(cwd?: string): Promise<string | null> {
  const version = await runGh(["--version"], cwd);
  if (!version.ok) {
    return (
      "The GitHub CLI (gh) is not installed or not on PATH. " +
      "Install it from https://cli.github.com, then run: gh auth login"
    );
  }

  const auth = await runGh(["auth", "status"], cwd);
  if (!auth.ok) {
    return "Not logged in to GitHub. Run: gh auth login";
  }

  return null;
}

/**
 * Turn a `gh` failure into something the model can act on.
 *
 * gh writes its real message to stderr and exits non-zero; passing the raw
 * text through means a missing remote reads the same as a permissions error.
 */
export function explainGhFailure(result: GhResult): string {
  const text = `${result.stderr}\n${result.stdout}`.trim();

  if (/could not determine.*repository|not a git repository/i.test(text)) {
    return (
      "No GitHub repository found here. Run this inside a clone with a GitHub " +
      "remote, or pass repo as owner/name."
    );
  }
  if (/authentication|401|not logged/i.test(text)) {
    return "GitHub rejected the credentials. Run: gh auth login";
  }
  if (/403|permission|forbidden/i.test(text)) {
    return "GitHub refused the request — the account lacks permission on this repository.";
  }
  if (/404|not found/i.test(text)) {
    return "Not found — check the number, and that the repository is one this account can see.";
  }
  if (/no commits between|no commits/i.test(text)) {
    return "No commits between those branches, so there is nothing to open a pull request for.";
  }
  return text || "The GitHub CLI failed without a message.";
}
