/**
 * BharatBuild CLI - Slash command registry
 *
 * The CLI ships two interactive surfaces, and they do not share a command set:
 *
 *   repl  - the platform REPL (`bharatbuild`), oriented around modes,
 *           accounts and projects
 *   tui   - the coding-agent session (`bharatbuild chat`), oriented around
 *           context, tools and the agent runtime
 *
 * Only /exit, /help, /model and /quit exist in both. That is defensible - they
 * are different products - but it used to be invisible: typing /context in the
 * platform REPL produced a bare "Unknown command", giving no hint that the
 * command exists one surface over.
 *
 * This module is the single declaration of what exists and where. Both
 * dispatchers consult it for unknown commands, and the help panel renders from
 * it, so the help text cannot advertise a command that is not implemented.
 */

export type Surface = "repl" | "tui";

export interface SlashCommand {
  /** Canonical name, without the leading slash. */
  name: string;
  aliases?: string[];
  /** Argument hint shown in help, e.g. "<id>". */
  args?: string;
  description: string;
  /** Surfaces that actually implement it. */
  surfaces: Surface[];
}

export const SURFACE_LABEL: Record<Surface, string> = {
  repl: "the platform REPL (`bharatbuild`)",
  tui: "the agent session (`bharatbuild chat`)",
};

/**
 * Keep each entry's `surfaces` honest - `findUnimplemented()` below is used by
 * the drift check to assert this table matches the dispatchers.
 */
export const SLASH_COMMANDS: SlashCommand[] = [
  // ── shared ────────────────────────────────────────────────────────────────
  { name: "help", aliases: ["h"], description: "Show available commands", surfaces: ["repl", "tui"] },
  { name: "exit", aliases: ["quit", "q"], description: "Exit the session", surfaces: ["repl", "tui"] },
  { name: "model", args: "[id]", description: "Show or set the active model", surfaces: ["repl", "tui"] },

  // ── platform REPL ─────────────────────────────────────────────────────────
  { name: "mode", args: "<mode>", description: "Switch platform mode (student|developer|founder|college|api-partner)", surfaces: ["repl"] },
  { name: "modes", description: "List available platform modes", surfaces: ["repl"] },
  { name: "menu", description: "Show the interactive mode menu", surfaces: ["repl"] },
  { name: "login", description: "Log in / re-authenticate", surfaces: ["repl"] },
  { name: "logout", description: "Clear stored credentials", surfaces: ["repl"] },
  { name: "whoami", description: "Show the logged-in account", surfaces: ["repl"] },
  { name: "projects", description: "List your projects", surfaces: ["repl"] },
  { name: "tokens", description: "Show your token balance", surfaces: ["repl"] },
  { name: "session", args: "<list|save|load>", description: "Manage saved sessions", surfaces: ["repl"] },
  { name: "reset", description: "Clear context and start fresh", surfaces: ["repl"] },

  // ── agent TUI ─────────────────────────────────────────────────────────────
  { name: "context", args: "[add|remove|show|clear]", description: "Inspect and edit the context window", surfaces: ["tui"] },
  { name: "tools", args: "[reset]", description: "View and reset tool permissions", surfaces: ["tui"] },
  { name: "mcp", description: "MCP server status", surfaces: ["tui"] },
  { name: "usage", description: "Token usage and session cost", surfaces: ["tui"] },
  { name: "agent", args: "[name]", description: "Show or switch the active agent", surfaces: ["tui"] },
  { name: "plan", description: "Enter plan mode (read-only)", surfaces: ["tui"] },
  { name: "effort", args: "<level>", description: "Set reasoning effort: low|medium|high|xhigh|max", surfaces: ["tui"] },
  { name: "spawn", args: "<task>", description: "Run a parallel agent session", surfaces: ["tui"] },
  { name: "rewind", description: "Fork the conversation at an earlier turn", surfaces: ["tui"] },
  { name: "chat", description: "Switch between previous sessions", surfaces: ["tui"] },
  { name: "clear", description: "Clear the conversation display", surfaces: ["tui"] },
  { name: "compact", description: "Toggle compact message display", surfaces: ["tui"] },
  { name: "transcript", description: "Open the transcript in a pager", surfaces: ["tui"] },
  { name: "editor", description: "Open $EDITOR for multi-line input", surfaces: ["tui"] },
  { name: "theme", args: "[name]", description: "Switch theme: dark|light|safe", surfaces: ["tui"] },
  { name: "paste", description: "Paste from the system clipboard", surfaces: ["tui"] },
  { name: "copy", description: "Copy the last response to the clipboard", surfaces: ["tui"] },
  { name: "hooks", description: "View configured hooks", surfaces: ["tui"] },
  { name: "settings", description: "Configure display, history, keybindings", surfaces: ["tui"] },
  
  // ── Missing Kiro CLI commands ─────────────────────────────────────────────
  { name: "checkpoint", args: "<init|list|restore|diff>", description: "Create and manage file restore points", surfaces: ["tui"] },
  { name: "goal", args: "[status|complete|cancel]", description: "Track and manage session goals", surfaces: ["tui"] },
  { name: "knowledge", args: "<show|add|search|remove>", description: "Manage knowledge base entries", surfaces: ["tui"] },
  { name: "session-id", description: "Show the current session ID", surfaces: ["tui"] },
  { name: "reply", description: "Open editor with last response quoted", surfaces: ["tui"] },
  { name: "guide", args: "[query]", description: "Get help from the built-in guide agent", surfaces: ["tui"] },
  { name: "todos", args: "[list|add|complete|remove]", description: "Manage task lists", surfaces: ["tui"] },
  { name: "code", args: "<init|overview|status|logs>", description: "Code intelligence and project tools", surfaces: ["tui"] },
  { name: "prompts", args: "<list|get|create|edit>", description: "Manage prompt templates", surfaces: ["tui"] },
  { name: "upgrade-agent", description: "Update agent capabilities and tools", surfaces: ["tui"] },
  { name: "logdump", description: "Export debug logs for troubleshooting", surfaces: ["tui"] },
  { name: "changelog", description: "Show recent changes and updates", surfaces: ["tui"] },
  { name: "tangent", description: "Enter tangent mode for exploration", surfaces: ["tui"] },
  { name: "title", args: "[new-title]", description: "Get or set the session title", surfaces: ["tui"] },
  { name: "spec", args: "[new|run|view|analyze]", description: "Specification and requirements management", surfaces: ["tui"] },
];

/** Key shortcuts, declared here so the help panel cannot advertise a phantom. */
export const KEY_SHORTCUTS: Array<{ key: string; description: string; surfaces: Surface[] }> = [
  { key: "Ctrl+C", description: "Cancel the current turn (twice to exit)", surfaces: ["tui"] },
  { key: "Ctrl+D", description: "Exit the session", surfaces: ["tui"] },
  { key: "Ctrl+O", description: "Expand/collapse tool output", surfaces: ["tui"] },
  { key: "Ctrl+X", description: "Toggle the activity tray", surfaces: ["tui"] },
  { key: "Ctrl+R", description: "Reverse history search", surfaces: ["tui"] },
  { key: "Ctrl+T", description: "Open the transcript in a pager", surfaces: ["tui"] },
  { key: "Ctrl+G", description: "Open crew monitor panel", surfaces: ["tui"] },
  { key: "Ctrl+S", description: "Fuzzy search and queue steering", surfaces: ["tui"] },
  { key: "Shift+Tab", description: "Toggle plan mode", surfaces: ["tui"] },
  { key: "!<command>", description: "Run a shell command directly", surfaces: ["tui"] },
  { key: "@<path>", description: "Reference a file or directory", surfaces: ["tui"] },
];

const BY_KEY = new Map<string, SlashCommand>();
for (const c of SLASH_COMMANDS) {
  BY_KEY.set(c.name, c);
  for (const a of c.aliases ?? []) BY_KEY.set(a, c);
}

export function lookupSlash(cmd: string): SlashCommand | undefined {
  return BY_KEY.get(cmd.replace(/^\//, "").toLowerCase());
}

export function commandsFor(surface: Surface): SlashCommand[] {
  return SLASH_COMMANDS.filter((c) => c.surfaces.includes(surface));
}

export function shortcutsFor(surface: Surface): typeof KEY_SHORTCUTS {
  return KEY_SHORTCUTS.filter((k) => k.surfaces.includes(surface));
}

/**
 * Message for a command this surface does not implement.
 *
 * Returns a pointer to the surface that does implement it, rather than a bare
 * "unknown command" - that ambiguity is the actual usability bug.
 */
export function explainUnknown(cmd: string, surface: Surface): string {
  const entry = lookupSlash(cmd);
  if (!entry) {
    const guess = nearest(cmd, commandsFor(surface).map((c) => c.name));
    return guess
      ? `Unknown command: /${cmd}. Did you mean /${guess}? Type /help for the full list.`
      : `Unknown command: /${cmd}. Type /help for the full list.`;
  }
  if (entry.surfaces.includes(surface)) {
    // Declared for this surface but not handled - the drift check should catch
    // this before a user does.
    return `/${entry.name} is registered for this surface but has no handler. This is a bug.`;
  }
  const where = entry.surfaces.map((s) => SURFACE_LABEL[s]).join(" or ");
  return `/${entry.name} is not available here — it lives in ${where}.`;
}

/** Small edit-distance suggestion so a typo does not read as a missing feature. */
function nearest(input: string, candidates: string[]): string | undefined {
  let best: string | undefined;
  let bestScore = Infinity;
  for (const c of candidates) {
    const d = distance(input, c);
    if (d < bestScore) { bestScore = d; best = c; }
  }
  return bestScore <= 2 ? best : undefined;
}

function distance(a: string, b: string): number {
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let last = prev[0]!;
    prev[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const tmp = prev[j]!;
      prev[j] = Math.min(prev[j]! + 1, prev[j - 1]! + 1, last + (a[i - 1] === b[j - 1] ? 0 : 1));
      last = tmp;
    }
  }
  return prev[b.length]!;
}

/**
 * Registry entries claimed for `surface` that `handled` does not cover.
 * Used by the drift check so the table and the dispatchers cannot diverge.
 */
export function findUnimplemented(surface: Surface, handled: Set<string>): string[] {
  return commandsFor(surface)
    .filter((c) => !handled.has(c.name) && !(c.aliases ?? []).some((a) => handled.has(a)))
    .map((c) => c.name);
}
