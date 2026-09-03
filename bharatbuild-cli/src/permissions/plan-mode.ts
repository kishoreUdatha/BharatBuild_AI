/**
 * Which tools plan mode refuses.
 *
 * This lived in the TUI, so plan mode only held while the ink UI was on
 * screen. `checkPermission` fell through `if (mode === "ask") … return "allow"`
 * for every other mode, which meant a headless run under
 * BHARATBUILD_MODE=plan happily created files. Verified: a "plan mode" run
 * wrote should-not-exist.txt.
 *
 * It belongs here instead, next to the single gate every caller goes through.
 */

/**
 * Tools that change something outside the process: the filesystem, the shell,
 * or the repository. Reads and searches stay available so a planning agent can
 * still investigate before it proposes.
 *
 * Aliases matter here. edit_file/apply_patch and shell/execute_command are the
 * same capability under two names, and listing only one leaves a hole the
 * model can walk straight through.
 */
const MUTATING = new Set([
  "write", "write_file", "edit_file", "apply_patch", "delete_file",
  "shell", "execute_command", "run_tests",
  "git_add", "git_commit",
]);

export function isMutating(toolName: string): boolean {
  return MUTATING.has(toolName);
}

/**
 * Every name under which the toolset can run an arbitrary shell command.
 *
 * The command policy used to test `toolName === "execute_command"` only, so
 * calling the identical capability as `shell` skipped the dangerous-command
 * check entirely. Gates belong on the capability, not on one of its spellings.
 * "bash" is here because the backend's own tool list advertises that name.
 */
const SHELL_TOOLS = new Set(["shell", "execute_command", "bash", "run_terminal"]);

export function isShellTool(toolName: string): boolean {
  return SHELL_TOOLS.has(toolName);
}

/**
 * Names under which a tool creates, edits or deletes a file.
 *
 * The protected-path check tested `write_file` and `delete_file` only, so
 * `write`, `apply_patch` and `edit_file` could all write to C:\Windows or /etc
 * unchallenged. Verified before the fix: write_file → deny, write → allow, for
 * the identical target.
 */
const FILE_WRITE_TOOLS = new Set([
  "write", "write_file", "create_file",
  "edit_file", "apply_patch", "str_replace",
  "delete_file",
]);

/**
 * Tool calls that publish something other people can see.
 *
 * Every other tool changes this machine. Opening a pull request or an issue
 * is visible to everyone with access to the repository and cannot be quietly
 * undone, so it is confirmed even in auto mode - auto-accept was chosen for
 * local edits, not for posting to a shared repo under the user's name.
 */
const PUBLISHING_TOOLS = new Set(["github_issue", "github_pr"]);
const PUBLISHING_ACTIONS = new Set(["create", "comment", "close", "reopen", "merge"]);

export function isPublishingAction(
  toolName: string,
  input: Record<string, unknown>,
): boolean {
  if (!PUBLISHING_TOOLS.has(toolName)) return false;
  const action = typeof input["action"] === "string" ? input["action"] : "";
  return PUBLISHING_ACTIONS.has(action);
}

export function isFileWriteTool(toolName: string): boolean {
  return FILE_WRITE_TOOLS.has(toolName);
}

/**
 * The path a file tool is acting on, under whichever key it uses.
 *
 * apply_patch takes `file_path` while write_file takes `path`; a check reading
 * only `input.path` saw an empty string for the former and passed it.
 */
export function targetPath(input: Record<string, unknown>): string {
  for (const key of ["path", "file_path", "filePath", "file"]) {
    const value = input[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return "";
}

/**
 * What to tell the model. A bare "denied" reads as a transient failure and it
 * retries the same call until the turn limit; naming the mode and forbidding
 * the retry turns a wasted turn into a plan.
 */
export function planDenialReason(toolName: string): string {
  return (
    `Plan mode is active, so '${toolName}' is unavailable. Do not retry it ` +
    `or any other tool that writes files or runs commands. Investigate with ` +
    `read-only tools and reply with the plan you would carry out.`
  );
}

/**
 * Tools that only look at things.
 *
 * "ask" mode fell through to a prompt for *every* tool, reads included, so a
 * question that read forty files asked forty times. That is not a safety
 * feature — it is how a user learns to hold Enter, or gives up and switches
 * the whole session to auto, which is what happened here.
 *
 * An allowlist rather than "not in the mutating set", so the failure direction
 * is safe: a tool nobody has classified — an MCP tool from a third-party
 * server, say — is asked about rather than waved through.
 */
const READ_ONLY_TOOLS = new Set([
  // Filesystem reads
  "read", "read_file", "list_files", "glob", "grep", "find_files",
  "search_code", "search_files", "code", "introspect",
  // Inspecting something already running; starting and stopping are not here.
  "read_process_output",
  // Git queries. git_add and git_commit are mutations and stay gated.
  "git_status", "git_diff", "git_log",
  // Agent bookkeeping — no effect outside the session.
  "todo_list", "thinking", "goal", "knowledge", "guide",
  // Its own UI is the confirmation; a prompt in front of it asks twice.
  "ask_user",
]);

export function isReadOnlyTool(toolName: string): boolean {
  return READ_ONLY_TOOLS.has(toolName);
}
