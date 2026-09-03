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
export type PermissionAsker = (
  toolName: string,
  input: Record<string, unknown>,
) => Promise<ApprovalDecision>;

let externalAsk: PermissionAsker | null = null;

/**
 * Let a full-screen UI answer approval prompts itself.
 *
 * The ink TUI holds stdin in raw mode and repaints the whole screen, so the
 * readline-based prompt was invisible and unanswerable — every tool call ended
 * up denied and the agent stopped after saying what it planned to do.
 */
export function setPermissionAsker(asker: PermissionAsker | null): void {
  externalAsk = asker;
}

/** The installed asker, if any. Used by the built-in tool approval gate too. */
export function getPermissionAsker(): PermissionAsker | null {
  return externalAsk;
}

import { isMutating, isShellTool, isFileWriteTool, isPublishingAction, isReadOnlyTool, targetPath, planDenialReason } from "./plan-mode.js";
import { setDenyReason } from "./deny-reason.js";
import { evaluateRules, matchingRule } from "./rules.js";

export async function checkPermission(
  toolName: string,
  input: Record<string, unknown>,
  config?: CLIConfig,
): Promise<ApprovalDecision> {
  const cfg = config ?? loadConfig();
  const mode = cfg.permissionMode;

  // --trust-all-tools sets this. It only reached the built-in tool registry
  // before, so the flag appeared to do nothing: this gate still returned
  // "deny" and the agent silently skipped every tool call.
  // Protected paths below are deliberately still enforced.
  const trustAll = process.env["BHARATBUILD_TRUST_ALL_TOOLS"] === "1";

  // Never prompt when there is nobody to answer. Deny rather than
  // auto-allow: silently escalating to full access because a TTY is absent is
  // how an unattended run does something destructive.
  const canPrompt = !cfg.nonInteractive && process.stdin.isTTY === true;
  const ask = async (): Promise<ApprovalDecision> => {
    // A UI that owns the terminal (the ink TUI) installs its own asker;
    // falling back to readline here would fight it for stdin and the prompt
    // would be painted over before the user could answer it.
    if (externalAsk) return externalAsk(toolName, input);
    if (canPrompt) return requestApproval(toolName, input);
    return "deny";
  };

  // Protected paths are never trusted away — for any tool that writes, under
  // any of its names. This tested write_file/delete_file only, so `write`,
  // `apply_patch` and `edit_file` reached C:\Windows and /etc unchallenged.
  if (isFileWriteTool(toolName) && isProtectedPath(targetPath(input))) {
    return "deny";
  }

  // Plan mode is read-only, and that has to hold on every path - not just
  // while the ink TUI happens to be mounted. It sits above trustAll on
  // purpose: asking for a read-only session is the more specific instruction,
  // so --trust-all-tools does not silently undo it.
  if (mode === "plan" && isMutating(toolName)) {
    setDenyReason(planDenialReason(toolName));
    return "deny";
  }

  /*
   * Explicit rules come before the blanket mode, and before trustAll.
   *
   * They are the specific instruction: someone who wrote `deny: [WebFetch]`
   * meant it, and --trust-all-tools is a convenience that must not quietly
   * undo it. Protected paths and plan mode still sit above, because those are
   * safety rails rather than preferences.
   */
  const ruled = evaluateRules(cfg.permissions, toolName, input);
  if (ruled === "deny") {
    setDenyReason(`Denied by a permission rule (${matchingRule(cfg.permissions, toolName, input)}).`);
    return "deny";
  }
  if (ruled === "allow") return "allow";
  if (ruled === "ask") return ask();

  // Opening a pull request or an issue is visible to the whole repository and
  // cannot be quietly undone, so it is confirmed even in auto mode. Auto-accept
  // was chosen for local edits, not for posting under the user's name.
  if (isPublishingAction(toolName, input)) {
    if (trustAll) return "allow";
    return ask();
  }

  // Any tool that runs a shell command goes through the command policy.
  //
  // This checked the single name "execute_command", while the toolset also
  // registers "shell" and the backend advertises "bash" — all three run
  // arbitrary commands. `shell` with `rm -rf /` was allowed outright while
  // `execute_command` with the same string was denied, so the gate came down
  // to which spelling the model happened to pick.
  if (isShellTool(toolName)) {
    const cmd = String(input["command"] ?? "");
    const p = evaluateCommandPolicy(cmd, mode);
    if (p === "allow") return "allow";
    if (p === "deny") return "deny";
    if (trustAll) return "allow";
    if (mode === "ask") return ask();
  }

  if (trustAll) return "allow";

  // Reading is not worth a prompt. Gating every tool made "ask" mode prompt
  // before each read_file, glob and grep — forty times for one repo question —
  // which teaches the user to approve without looking, and pushes them to turn
  // the whole session to auto. What is worth confirming is a change to the
  // machine, and those are handled above or fall through below.
  if (isReadOnlyTool(toolName)) return "allow";

  if (mode === "ask") return ask();
  return "allow";
}

/** True when an "ask" policy cannot actually reach a human. */
export function canPromptInteractively(config?: CLIConfig): boolean {
  const cfg = config ?? loadConfig();
  return !cfg.nonInteractive && process.stdin.isTTY === true;
}
