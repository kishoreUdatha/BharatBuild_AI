/**
 * Per-tool permission rules.
 *
 * The gate had one setting for everything: ask, auto, or plan. That cannot
 * express what people actually want — "never touch the network, always confirm
 * a shell command, editing files is fine" — so the choice was between being
 * asked about every write and being asked about nothing. Most people picked
 * nothing, and then an agent wrote nine files unprompted.
 *
 * Rules are matched against a tool call and answer allow / ask / deny. A
 * command can be matched too, so `Bash(git *)` is a different rule from
 * `Bash(curl *)`, which is the distinction that matters most.
 *
 * Shaped after claude-code's settings.json so the concepts, and the config,
 * are recognisable to anyone who has used it.
 */

export type RuleDecision = "allow" | "ask" | "deny";

export interface PermissionRules {
  allow?: string[];
  ask?: string[];
  deny?: string[];
}

/** A rule as written: a tool name, optionally narrowed by an argument pattern. */
interface ParsedRule {
  tool: string;
  /** The text inside the parentheses, if any: `git *` from `Bash(git *)`. */
  pattern?: string;
}

/**
 * Tool names people will write, mapped to the ones this CLI dispatches.
 *
 * A rule saying `Bash` has to gate `execute_command`, or the config is a lie —
 * and someone coming from claude-code will write `Bash`, `Edit` and `Read`.
 */
const ALIASES: Record<string, string[]> = {
  bash: ["execute_command", "shell", "bash", "run_terminal"],
  edit: ["apply_patch", "edit_file", "str_replace"],
  write: ["write_file", "write", "create_file"],
  read: ["read_file", "read"],
  websearch: ["web_search"],
  webfetch: ["web_fetch"],
  task: ["subagent", "delegate"],
  notebookedit: ["edit_notebook"],
};

export function parseRule(raw: string): ParsedRule | null {
  const text = raw.trim();
  if (!text) return null;
  const m = text.match(/^([A-Za-z_][\w-]*)\s*(?:\(([^)]*)\))?$/);
  if (!m) return null;
  return { tool: m[1]!.toLowerCase(), pattern: m[2]?.trim() || undefined };
}

/** True when a rule's tool name refers to this tool, alias or not. */
function toolMatches(ruleTool: string, toolName: string): boolean {
  const t = toolName.toLowerCase();
  if (ruleTool === t) return true;
  if (ruleTool === "*") return true;
  return (ALIASES[ruleTool] ?? []).includes(t);
}

/**
 * Glob match for an argument pattern.
 *
 * Only `*` is supported, and it spans anything — these patterns are written by
 * hand in a config file, so a full glob syntax would be more to get wrong than
 * it is worth. Matching is anchored: `git *` must not match `mygit push`.
 */
function patternMatches(pattern: string, value: string): boolean {
  const escaped = pattern.replace(/[.+^${}()|[\]\\?]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp("^" + escaped + "$", "i").test(value.trim());
}

/** The part of a call a pattern is matched against. */
function subjectOf(input: Record<string, unknown>): string {
  for (const key of ["command", "cmd", "path", "file_path", "file", "url", "pattern", "query"]) {
    const v = input[key];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}

function ruleApplies(raw: string, toolName: string, input: Record<string, unknown>): boolean {
  const rule = parseRule(raw);
  if (!rule) return false;
  if (!toolMatches(rule.tool, toolName)) return false;
  if (!rule.pattern) return true;
  return patternMatches(rule.pattern, subjectOf(input));
}

/**
 * Decide a tool call against the configured rules, or null when none apply.
 *
 * Deny wins, then ask, then allow. A user who has written both `Bash` under
 * allow and `Bash(curl *)` under deny means "shell is fine except curl" — and
 * reading them in the other order would hand back exactly the hole the deny
 * rule was added to close.
 */
export function evaluateRules(
  rules: PermissionRules | undefined,
  toolName: string,
  input: Record<string, unknown>,
): RuleDecision | null {
  if (!rules) return null;

  const matches = (list: string[] | undefined) =>
    Array.isArray(list) && list.some((r) => ruleApplies(r, toolName, input));

  if (matches(rules.deny)) return "deny";
  if (matches(rules.ask)) return "ask";
  if (matches(rules.allow)) return "allow";
  return null;
}

/** The rule that decided a call, for explaining the decision. */
export function matchingRule(
  rules: PermissionRules | undefined,
  toolName: string,
  input: Record<string, unknown>,
): string | null {
  if (!rules) return null;
  for (const list of [rules.deny, rules.ask, rules.allow]) {
    const hit = (list ?? []).find((r) => ruleApplies(r, toolName, input));
    if (hit) return hit;
  }
  return null;
}
