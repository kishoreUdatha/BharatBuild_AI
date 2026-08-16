import { evaluateCommandPolicy } from "./command-policy.js";
import { isProtectedPath } from "./path-policy.js";
import { requestApproval, type ApprovalDecision } from "./approval-manager.js";
import { loadConfig, type CLIConfig } from "../config/config.js";

/**
 * Decide whether a tool call may proceed.
 *
 * `config` is the session's configuration. It used to be re-read from disk
 * here, which meant a runtime that set permissionMode: "auto" was ignored, and
 * a headless run would open an interactive prompt on a stdin nobody was
 * reading - hanging the agent indefinitely rather than failing.
 */
export async function checkPermission(
  toolName: string,
  input: Record<string, unknown>,
  config?: CLIConfig,
): Promise<ApprovalDecision> {
  const cfg = config ?? loadConfig();
  const mode = cfg.permissionMode;

  // Never prompt when there is nobody to answer. Deny rather than
  // auto-allow: silently escalating to full access because a TTY is absent is
  // how an unattended run does something destructive.
  const canPrompt = !cfg.nonInteractive && process.stdin.isTTY === true;
  const ask = async (): Promise<ApprovalDecision> => {
    if (canPrompt) return requestApproval(toolName, input);
    return "deny";
  };

  if (toolName === "execute_command") {
    const cmd = String(input["command"] ?? "");
    const p = evaluateCommandPolicy(cmd, mode);
    if (p === "allow") return "allow";
    if (p === "deny") return "deny";
    if (mode === "ask") return ask();
  }

  if ((toolName === "write_file" || toolName === "delete_file") && isProtectedPath(String(input["path"] ?? ""))) {
    return "deny";
  }

  if (mode === "ask") return ask();
  return "allow";
}

/** True when an "ask" policy cannot actually reach a human. */
export function canPromptInteractively(config?: CLIConfig): boolean {
  const cfg = config ?? loadConfig();
  return !cfg.nonInteractive && process.stdin.isTTY === true;
}
