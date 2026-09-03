/**
 * GitHub pull request and issue tools.
 *
 * These differ from every other tool in the set: `write_file` changes a file on
 * this machine, but opening a pull request or an issue is visible to everyone
 * with access to the repository, and cannot be quietly undone. That is why the
 * writing actions are classified as publishing and go to the approval prompt
 * even in auto mode — see isPublishingAction in permissions/plan-mode.ts.
 *
 * Reading is unrestricted: listing issues or viewing a PR changes nothing.
 */

import type { ToolDefinition, ToolResult } from "../filesystem/index.js";
import { runGh, githubUnavailableReason, explainGhFailure } from "./gh-cli.js";

/** Actions that create or change something other people can see. */
export const GITHUB_WRITE_ACTIONS = new Set(["create", "comment", "close", "reopen", "merge"]);

export interface GithubIssueInput {
  action: "list" | "view" | "create" | "comment" | "close" | "reopen";
  number?: number;
  title?: string;
  body?: string;
  labels?: string[];
  limit?: number;
  state?: "open" | "closed" | "all";
  repo?: string;
  working_dir?: string;
}

export const githubIssueDefinition: ToolDefinition = {
  name: "github_issue",
  description:
    "Work with GitHub issues: list, view, create, comment, close, reopen. " +
    "Requires the gh CLI to be installed and authenticated. " +
    "Creating, commenting and closing are visible to everyone on the repository " +
    "and will ask for confirmation before they run.",
  input_schema: {
    type: "object",
    properties: {
      action: {
        type: "string",
        enum: ["list", "view", "create", "comment", "close", "reopen"],
        description: "What to do.",
      },
      number: { type: "number", description: "Issue number, for view/comment/close/reopen." },
      title: { type: "string", description: "Title, for create." },
      body: { type: "string", description: "Body text, for create and comment." },
      labels: { type: "array", items: { type: "string" }, description: "Labels, for create." },
      limit: { type: "number", description: "How many to list (default 20)." },
      state: { type: "string", enum: ["open", "closed", "all"], description: "Filter, for list." },
      repo: { type: "string", description: "owner/name. Defaults to the current repository." },
      working_dir: { type: "string", description: "Directory to run in." },
    },
    required: ["action"],
  },
};

export interface GithubPrInput {
  action: "list" | "view" | "create" | "comment" | "diff" | "checks";
  number?: number;
  title?: string;
  body?: string;
  base?: string;
  head?: string;
  draft?: boolean;
  limit?: number;
  state?: "open" | "closed" | "merged" | "all";
  repo?: string;
  working_dir?: string;
}

export const githubPrDefinition: ToolDefinition = {
  name: "github_pr",
  description:
    "Work with GitHub pull requests: list, view, create, comment, diff, checks. " +
    "Requires the gh CLI to be installed and authenticated. " +
    "Creating and commenting are visible to everyone on the repository and will " +
    "ask for confirmation before they run.",
  input_schema: {
    type: "object",
    properties: {
      action: {
        type: "string",
        enum: ["list", "view", "create", "comment", "diff", "checks"],
        description: "What to do.",
      },
      number: { type: "number", description: "PR number, for view/comment/diff/checks." },
      title: { type: "string", description: "Title, for create." },
      body: { type: "string", description: "Description, for create and comment." },
      base: { type: "string", description: "Branch to merge into. Defaults to the repo default." },
      head: { type: "string", description: "Branch with the changes. Defaults to the current one." },
      draft: { type: "boolean", description: "Open as a draft." },
      limit: { type: "number", description: "How many to list (default 20)." },
      state: { type: "string", enum: ["open", "closed", "merged", "all"], description: "Filter, for list." },
      repo: { type: "string", description: "owner/name. Defaults to the current repository." },
      working_dir: { type: "string", description: "Directory to run in." },
    },
    required: ["action"],
  },
};

/** `--repo owner/name` when one was given. */
function repoArgs(repo?: string): string[] {
  return repo ? ["--repo", repo] : [];
}

/**
 * The gh arguments for an issue action.
 *
 * Split out from execution so the argument building can be tested without
 * touching GitHub — a test that creates real issues is not a test anyone can
 * run twice.
 */
export function buildIssueArgs(input: GithubIssueInput): { args: string[] } | { error: string } {
  const repo = repoArgs(input.repo);

  switch (input.action) {
    case "list":
      return {
        args: [
          "issue", "list", ...repo,
          "--limit", String(input.limit ?? 20),
          "--state", input.state ?? "open",
        ],
      };

    case "view":
      if (!input.number) return { error: "'number' is required to view an issue." };
      return { args: ["issue", "view", String(input.number), ...repo, "--comments"] };

    case "create": {
      if (!input.title) return { error: "'title' is required to create an issue." };
      const args = ["issue", "create", ...repo, "--title", input.title, "--body", input.body ?? ""];
      for (const label of input.labels ?? []) args.push("--label", label);
      return { args };
    }

    case "comment":
      if (!input.number) return { error: "'number' is required to comment." };
      if (!input.body) return { error: "'body' is required to comment." };
      return { args: ["issue", "comment", String(input.number), ...repo, "--body", input.body] };

    case "close":
      if (!input.number) return { error: "'number' is required to close an issue." };
      return { args: ["issue", "close", String(input.number), ...repo] };

    case "reopen":
      if (!input.number) return { error: "'number' is required to reopen an issue." };
      return { args: ["issue", "reopen", String(input.number), ...repo] };

    default:
      return { error: `Unknown action '${String(input.action)}'.` };
  }
}

/** The gh arguments for a pull request action. */
export function buildPrArgs(input: GithubPrInput): { args: string[] } | { error: string } {
  const repo = repoArgs(input.repo);

  switch (input.action) {
    case "list":
      return {
        args: [
          "pr", "list", ...repo,
          "--limit", String(input.limit ?? 20),
          "--state", input.state ?? "open",
        ],
      };

    case "view":
      if (!input.number) return { error: "'number' is required to view a pull request." };
      return { args: ["pr", "view", String(input.number), ...repo, "--comments"] };

    case "diff":
      if (!input.number) return { error: "'number' is required to show a diff." };
      return { args: ["pr", "diff", String(input.number), ...repo] };

    case "checks":
      if (!input.number) return { error: "'number' is required to show checks." };
      return { args: ["pr", "checks", String(input.number), ...repo] };

    case "create": {
      if (!input.title) return { error: "'title' is required to create a pull request." };
      const args = ["pr", "create", ...repo, "--title", input.title, "--body", input.body ?? ""];
      if (input.base) args.push("--base", input.base);
      if (input.head) args.push("--head", input.head);
      if (input.draft) args.push("--draft");
      return { args };
    }

    case "comment":
      if (!input.number) return { error: "'number' is required to comment." };
      if (!input.body) return { error: "'body' is required to comment." };
      return { args: ["pr", "comment", String(input.number), ...repo, "--body", input.body] };

    default:
      return { error: `Unknown action '${String(input.action)}'.` };
  }
}

async function runBuilt(
  built: { args: string[] } | { error: string },
  workingDir: string | undefined,
): Promise<ToolResult> {
  if ("error" in built) return { content: `Error: ${built.error}`, isError: true };

  const unavailable = await githubUnavailableReason(workingDir);
  if (unavailable) return { content: unavailable, isError: true };

  const result = await runGh(built.args, workingDir);
  if (!result.ok) return { content: explainGhFailure(result), isError: true };

  return {
    content: result.stdout || "(no output)",
    isError: false,
  };
}

export async function githubIssue(input: GithubIssueInput): Promise<ToolResult> {
  return runBuilt(buildIssueArgs(input), input.working_dir);
}

export async function githubPr(input: GithubPrInput): Promise<ToolResult> {
  return runBuilt(buildPrArgs(input), input.working_dir);
}
