/**
 * BharatBuild CLI — Tool Approval System
 * Handles approval prompting, session-level permissions, and policy enforcement.
 * Matches Kiro CLI's "◌ approval required" pattern.
 */

import chalk from "chalk";
import readline from "readline";
import type { ApprovalStatus, ToolApprovalConfig } from "./types.js";
import { BuiltInToolRegistry } from "./registry.js";

export type ApprovalDecision = "allow" | "deny" | "allow_always" | "cancel";

/**
 * Check if a tool can proceed, prompting the user if needed.
 */
export async function checkToolApproval(
  registry: BuiltInToolRegistry,
  toolName: string,
  params: Record<string, unknown>,
  options?: { nonInteractive?: boolean }
): Promise<ApprovalDecision> {
  const status = registry.getApprovalStatus(toolName);

  if (status === "allowed") return "allow";
  if (status === "denied") return "deny";

  // Status is "approval_required" — need to prompt
  if (options?.nonInteractive || !process.stdin.isTTY) {
    // Can't prompt — deny by default in non-interactive mode
    return "deny";
  }

  return promptForApproval(toolName, params);
}

/**
 * Prompt the user for tool approval.
 */
async function promptForApproval(
  toolName: string,
  params: Record<string, unknown>
): Promise<ApprovalDecision> {
  const paramSummary = formatParams(toolName, params);

  console.log("");
  console.log(chalk.yellow(`  ◌ Tool requires approval: ${chalk.bold(toolName)}`));
  console.log(chalk.dim(`    ${paramSummary}`));
  console.log("");
  console.log(chalk.cyan("    [y] Allow once  [a] Allow always  [n] Deny  [c] Cancel"));

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  return new Promise<ApprovalDecision>((resolve) => {
    rl.question(chalk.cyan("    > "), (answer) => {
      rl.close();
      const a = answer.trim().toLowerCase();

      switch (a) {
        case "y":
        case "yes":
          resolve("allow");
          break;
        case "a":
        case "always":
          resolve("allow_always");
          break;
        case "n":
        case "no":
          resolve("deny");
          break;
        case "c":
        case "cancel":
          resolve("cancel");
          break;
        default:
          // Default to allow (like Kiro's behavior)
          resolve("allow");
      }
    });
  });
}

/**
 * Format tool parameters for display in the approval prompt.
 */
function formatParams(toolName: string, params: Record<string, unknown>): string {
  switch (toolName) {
    case "shell":
      return `Command: ${String(params["command"] ?? "").slice(0, 100)}`;
    case "write":
      return `${params["command"]} → ${params["path"]}`;
    case "read":
      return `Reading ${(params["operations"] as unknown[])?.length ?? 0} operation(s)`;
    case "glob":
      return `Pattern: ${params["pattern"]} in ${params["path"] ?? "."}`;
    case "grep":
      return `Pattern: ${params["pattern"]}`;
    case "web_fetch":
      return `URL: ${params["url"]}`;
    case "web_search":
      return `Query: ${params["query"]}`;
    case "use_aws":
      return `${params["service_name"]} ${params["operation_name"]} (${params["label"]})`;
    case "code":
      return `${params["operation"]}${params["symbol_name"] ? `: ${params["symbol_name"]}` : ""}`;
    case "subagent":
      return `Task: ${String(params["task"] ?? "").slice(0, 80)}`;
    case "knowledge":
      return `${params["command"]}${params["query"] ? `: ${params["query"]}` : ""}`;
    default:
      return JSON.stringify(params).slice(0, 120);
  }
}

/**
 * Apply an approval decision to the registry (for "allow_always").
 */
export function applyApprovalDecision(
  registry: BuiltInToolRegistry,
  toolName: string,
  decision: ApprovalDecision
): void {
  if (decision === "allow_always") {
    registry.allowTool(toolName);
  }
}
