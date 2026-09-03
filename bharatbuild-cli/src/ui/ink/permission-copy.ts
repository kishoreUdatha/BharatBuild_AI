/**
 * What the approval prompt says.
 *
 * The prompt used to read `apply_patch needs approval` over a dump of the raw
 * arguments, which asks the user to approve a function call rather than an
 * action. The decision is about what happens to the machine — a file being
 * rewritten, a command being run, an issue being posted — so the question names
 * that, and shows the change itself.
 *
 * Kept apart from the component so the wording can be tested without a
 * terminal, and so a tool added later fails here rather than silently
 * rendering as its own function name.
 */

import { isShellTool, isFileWriteTool, targetPath } from "../../permissions/plan-mode.js";
import { displayPath } from "../../infra/display-path.js";
import { buildUnifiedDiff } from "../../tools/filesystem/diff.js";

/** The change itself, in whatever form suits the tool. */
export type Preview =
  | { kind: "diff"; patch: string }
  | { kind: "command"; text: string }
  | { kind: "lines"; lines: string[] }
  | { kind: "none" };

export interface PermissionCopy {
  /** Box heading — the kind of action, in the user's terms. */
  title: string;
  /** The actual question, naming the specific target. */
  question: string;
  /** Label for "yes, and stop asking" — scoped to the capability, not the tool. */
  alwaysLabel: string;
  preview: Preview;
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");

/** Longest string argument, for tools whose payload key we do not know. */
function fallbackDetail(input: Record<string, unknown>): string[] {
  const lines: string[] = [];
  for (const [k, v] of Object.entries(input)) {
    if (typeof v === "string" && v.trim()) lines.push(`${k}: ${v}`);
    else if (typeof v === "number" || typeof v === "boolean") lines.push(`${k}: ${String(v)}`);
  }
  return lines;
}

const DELETE_TOOLS = new Set(["delete_file", "remove_file"]);

export function permissionCopy(
  toolName: string,
  input: Record<string, unknown>,
  cwd: string = process.cwd(),
): PermissionCopy {
  const rawPath = targetPath(input);
  const path = rawPath ? displayPath(rawPath, cwd) : "";
  const name = path ? path.split(/[/\\]/).pop()! : "";

  // Shell first: a command is the one case where the argument *is* the action,
  // and it carries the most risk of being approved without being read.
  if (isShellTool(toolName)) {
    const command = str(input["command"]) || str(input["cmd"]);
    const background = input["background"] === true;
    return {
      title: background ? "Run command in the background" : "Run command",
      question: "Do you want to run this command?",
      // Scoped to the program, not the whole shell: approving `npm test` for
      // the session should not also approve `rm -rf`.
      alwaysLabel: `Yes, and allow ${programOf(command) || "commands"} for the rest of this session`,
      preview: { kind: "command", text: command },
    };
  }

  if (DELETE_TOOLS.has(toolName)) {
    return {
      title: "Delete file",
      question: `Do you want to delete ${name || "this file"}?`,
      alwaysLabel: "Yes, and allow deletions for the rest of this session",
      preview: path ? { kind: "lines", lines: [path] } : { kind: "none" },
    };
  }

  if (toolName === "github_issue" || toolName === "github_pr") {
    const action = str(input["action"]) || "create";
    const what = toolName === "github_pr" ? "pull request" : "issue";
    const title = str(input["title"]);
    return {
      // Publishing leaves the machine, so it says so plainly.
      title: `${action === "create" ? "Create" : action} ${what} on GitHub`,
      question: `Do you want to ${action} this ${what}? This posts to GitHub.`,
      alwaysLabel: `Yes, and allow GitHub ${what}s for the rest of this session`,
      preview: {
        kind: "lines",
        lines: [
          str(input["repo"]) ? `repo:  ${str(input["repo"])}` : "",
          title ? `title: ${title}` : "",
          str(input["body"]) ? "" : "",
          ...str(input["body"]).split("\n").slice(0, 8),
        ].filter((l) => l !== ""),
      },
    };
  }

  if (isFileWriteTool(toolName)) {
    const oldText = str(input["old_string"]);
    const newText = str(input["new_string"]);
    const content = str(input["content"]);

    // A replacement is a real edit; show it as one rather than as two opaque
    // blobs the reader has to diff in their head.
    if (oldText || newText) {
      const { patch } = buildUnifiedDiff(oldText, newText, rawPath || "file", { contextLines: 2 });
      return {
        title: newText && !oldText ? "Add to file" : "Edit file",
        question: `Do you want to make this edit to ${name || "this file"}?`,
        alwaysLabel: "Yes, and allow edits for the rest of this session",
        preview: patch ? { kind: "diff", patch } : { kind: "none" },
      };
    }

    // A create or overwrite: every line is new, so it reads as a diff of adds.
    if (content) {
      const { patch } = buildUnifiedDiff("", content, rawPath || "file", { contextLines: 2 });
      return {
        title: "Create file",
        question: `Do you want to create ${name || "this file"}?`,
        alwaysLabel: "Yes, and allow writing files for the rest of this session",
        preview: patch ? { kind: "diff", patch } : { kind: "none" },
      };
    }

    return {
      title: "Write file",
      question: `Do you want to write ${name || "this file"}?`,
      alwaysLabel: "Yes, and allow writing files for the rest of this session",
      preview: path ? { kind: "lines", lines: [path] } : { kind: "none" },
    };
  }

  // Anything else still gets a sentence rather than a schema dump.
  return {
    title: toolName,
    question: `Do you want to run ${toolName}?`,
    alwaysLabel: `Yes, and allow ${toolName} for the rest of this session`,
    preview: { kind: "lines", lines: fallbackDetail(input).slice(0, 8) },
  };
}

/** The program a command actually invokes, for the "don't ask again" label. */
export function programOf(command: string): string {
  const first = command.trim().split(/[\s;|&]+/).find((t) => t && !/^\w+=/.test(t));
  if (!first) return "";
  return first.split(/[/\\]/).pop() ?? "";
}

/**
 * What "yes, and stop asking" actually grants.
 *
 * This has to match what the option says. Keyed on the tool name alone,
 * approving `npm test` for the session also approved `rm -rf` — the same tool
 * carries both — while the prompt said "allow npm". A shell approval is
 * therefore scoped to the program that was shown, and every other tool keeps
 * its own name, which is the granularity its label describes.
 */
export function alwaysAllowKey(toolName: string, input: Record<string, unknown>): string {
  if (isShellTool(toolName)) {
    const program = programOf(str(input["command"]) || str(input["cmd"]));
    // No identifiable program means no blanket grant: it falls back to a key
    // nothing else matches, so the next command asks again.
    return program ? `shell:${program}` : `shell:${JSON.stringify(input["command"] ?? "")}`;
  }
  return toolName;
}
