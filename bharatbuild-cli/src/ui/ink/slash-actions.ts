/**
 * Slash command dispatch for the ink TUI.
 *
 * The ink surface previously had no dispatcher at all, so every `/command` was
 * forwarded to the model as chat text. This module owns the whole `tui` surface
 * and returns a plain description of what the App should do, keeping the React
 * layer free of runtime plumbing.
 *
 * Handlers return text rather than printing: ink owns the screen, so anything
 * written straight to stdout is erased on the next frame. For the same reason
 * commands that would seize the terminal in the classic UI (external pager,
 * $EDITOR) render inline here instead of spawning a child process.
 */

import { commandsFor, explainUnknown, shortcutsFor, lookupSlash } from "../slash-registry.js";
import { applyAgent, agentNames } from "../../agents/apply-agent.js";
import { userTurns, keepBefore } from "./rewind.js";
import { loadCustomCommands, applyArgs, expandShell } from "../custom-commands.js";
import { runUserCommand } from "../../tools/shell/index.js";

export interface SlashContext {
  runtime: any;
  model: string;
  agent: string;
  compact: boolean;
  planMode: boolean;
  tangentMode: boolean;
  /** Transcript as the UI knows it, for /transcript, /copy, /reply, /logdump. */
  transcript: Array<{ role: string; content: string; timestamp: Date }>;
}

export interface SlashResult {
  /** Text to append to the transcript as a system message. */
  output?: string;
  /** Wipe the visible transcript. */
  clear?: boolean;
  /** Leave the session. */
  exit?: boolean;
  /** State the App should adopt. */
  patch?: Partial<Pick<SlashContext, "model" | "agent" | "compact" | "planMode" | "tangentMode">>;
  /** Pre-fill the input box (used by /paste and /reply). */
  inputValue?: string;
  /**
   * An image to send with the next message rather than on its own — a
   * screenshot is nearly always evidence for a question, not the question.
   */
  attachImage?: { imageBase64: string; mimeType: string };
  /** Long-running command — the App shows a spinner while it resolves. */
  busy?: boolean;
  /**
   * A prompt to send to the model, as though the user had typed it.
   *
   * Used by user-defined .toml commands, which are prompt templates rather
   * than things the CLI executes itself.
   */
  promptToSend?: string;
  /** Colours changed; force a re-render so the new palette takes effect. */
  repaint?: boolean;
}

const EFFORTS = ["low", "medium", "high", "xhigh", "max"];

/** Commands this surface implements. `inkUnhandled()` asserts it covers the registry. */
export const INK_HANDLED = new Set([
  "help", "h", "exit", "quit", "q", "clear", "model", "agent", "usage", "context",
  "tools", "mcp", "compact", "plan", "effort", "session-id", "copy", "paste",
  "theme", "transcript", "editor", "reply", "title", "chat", "rewind", "spawn",
  "hooks", "settings", "checkpoint", "goal", "knowledge", "guide", "todos",
  "code", "prompts", "upgrade-agent", "logdump", "changelog", "tangent", "spec",
  "glyphs", "thinking", "permissions",
]);

export async function runSlashCommand(raw: string, ctx: SlashContext): Promise<SlashResult> {
  const parts = raw.slice(1).trim().split(/\s+/);
  const cmd = (parts[0] ?? "").toLowerCase();
  const args = parts.slice(1);

  // A user-defined command is not handled here — it expands to a prompt and
  // is sent to the model like anything the user typed. Checked before the
  // switch so a project can define a command the built-ins have not claimed.
  if (!INK_HANDLED.has(cmd)) {
    const custom = loadCustomCommands().commands.find((c) => c.name === cmd);
    if (custom) {
      const withArgs = applyArgs(custom.prompt, args.join(" "));
      const expanded = await expandShell(withArgs, async (shellCmd) => {
        const r = await runUserCommand({ command: shellCmd });
        return r.content.replace(/^STDOUT:\s*/, "").trimEnd();
      });
      return { promptToSend: expanded };
    }
  }
  const rt = ctx.runtime;

  switch (cmd) {
    // ── Session basics ──────────────────────────────────────────────────────
    case "":
    case "help":
    case "h":
      return { output: renderHelp() };

    case "exit":
    case "quit":
    case "q":
      return { exit: true };

    case "clear":
      return { clear: true };

    case "session-id":
      return { output: rt?.sessionId ? `Session: ${rt.sessionId}` : "No active session." };

    case "title":
      return title(rt, args);

    case "chat":
      return chat(rt, args);

    case "rewind":
      return rewind(rt, args);

    // ── Model / agent knobs ─────────────────────────────────────────────────
    case "model": {
      if (!args[0]) return { output: `Model: ${ctx.model}\n\nUsage: /model <auto|haiku|sonnet|opus|full-id>` };
      rt?.cost?.setModel?.(args[0]);
      return { patch: { model: args[0] }, output: `Model set to ${args[0]}` };
    }

    case "agent": {
      if (!args[0]) {
        return { output: `Agent: ${ctx.agent}\n\nAvailable: ${agentNames().join(", ")}\nUsage: /agent <name>` };
      }
      // This only patched a label: no system prompt was applied and a
      // read-only agent stayed free to write. Switching now does what
      // --agent does, through the same code.
      try {
        const applied = applyAgent(rt, args[0], process.cwd());
        const note = applied.readOnly
          ? " — read-only: it will plan, not edit."
          : "";
        return { patch: { agent: applied.role }, output: `Agent switched to ${applied.role}${note}` };
      } catch (err) {
        return { output: err instanceof Error ? err.message : String(err) };
      }
    }

    case "effort": {
      if (!args[0]) return { output: `Usage: /effort <${EFFORTS.join("|")}>` };
      const level = args[0].toLowerCase();
      if (!EFFORTS.includes(level)) return { output: `Unknown effort "${level}". Use: ${EFFORTS.join(", ")}` };
      rt?.cost?.setEffort?.(level);
      return { output: `Reasoning effort set to ${level}` };
    }

    case "compact":
      return { patch: { compact: !ctx.compact }, output: `Compact display ${ctx.compact ? "off" : "on"}.` };

    case "plan":
      return {
        patch: { planMode: !ctx.planMode },
        output: ctx.planMode ? "Plan mode off — edits enabled." : "Plan mode on — read-only; the agent plans, it does not edit.",
      };

    case "tangent":
      return {
        patch: { tangentMode: !ctx.tangentMode },
        output: ctx.tangentMode ? "Tangent mode off." : "Tangent mode on — explore freely, no file changes.",
      };

    case "permissions": {
      // A denial the user cannot trace back to a line of their own config is a
      // bug report waiting to happen, so this shows the rules verbatim.
      const { loadConfig } = await import("../../config/config.js");
      const cfg = loadConfig();
      const rules = cfg.permissions;
      const lines = [`Mode: ${cfg.permissionMode}`];
      if (!rules || (!rules.allow?.length && !rules.ask?.length && !rules.deny?.length)) {
        lines.push(
          "",
          "No per-tool rules. Every tool follows the mode above.",
          "",
          "Add a permissions block to ~/.bharatbuild/config.json, e.g.:",
          '  "permissions": {',
          '    "deny":  ["WebFetch", "Bash(curl *)"],',
          '    "ask":   ["Bash"],',
          '    "allow": ["Edit", "Read"]',
          "  }",
          "",
          "deny beats ask beats allow. A rule can name a tool (Bash) or narrow it",
          "by argument (Bash(git *)). Rules override the mode, but not plan mode",
          "or protected paths.",
        );
      } else {
        for (const [name, list] of [["deny", rules.deny], ["ask", rules.ask], ["allow", rules.allow]] as const) {
          if (list?.length) lines.push("", `${name}:`, ...list.map((r) => `  ${r}`));
        }
      }
      return { output: lines.join("\n") };
    }

    case "thinking": {
      // Off by default: thinking tokens are billed as output, so leaving it on
      // for every "what does this file do" is a silent price rise.
      const { configuredLevel, supportsThinking, thinkingShape } = await import("../../models/thinking-config.js");
      const { resolveModel } = await import("../../config/constants.js");
      const levels = ["off", "low", "medium", "high"];
      const resolved = resolveModel(ctx.model);
      if (!args[0]) {
        return {
          output: [
            `Thinking: ${configuredLevel()}`,
            `Model ${resolved}: ${supportsThinking(resolved) ? thinkingShape(resolved) + " thinking" : "no thinking support"}`,
            "",
            "Usage: /thinking <off|low|medium|high>",
            "Reasoning is billed as output tokens, so this is off unless asked for.",
          ].join("\n"),
        };
      }
      const level = args[0].toLowerCase();
      if (!levels.includes(level)) {
        return { output: `Unknown level "${level}". Use: ${levels.join(", ")}` };
      }
      // The provider reads this per request, so it takes effect on the next turn.
      process.env["BHARATBUILD_THINKING"] = level;
      if (level !== "off" && !supportsThinking(resolved)) {
        return { output: `Thinking set to ${level}, but ${resolved} does not support it — it will be ignored until you switch model.` };
      }
      return { output: `Thinking set to ${level}.` };
    }

    case "glyphs": {
      // Switching live, not by restart, because the only way to know whether a
      // font has U+23FA is to look at it — and the way back has to be just as
      // quick when it turns out to be a tofu box.
      const { setGlyphs, getGlyphMode, glyphModes, getGlyphs } = await import("./glyphs.js");
      const modes = glyphModes();
      if (!args[0]) {
        const g = getGlyphs();
        return {
          output: [
            `Glyphs: ${getGlyphMode()}`,
            "",
            ...modes.map((m) => `  ${m}`),
            "",
            `Current markers:  ${g.assistant}  ${g.elbow.trim()}  ${g.cursor}`,
            "Usage: /glyphs <unicode|claude|ascii>",
            "  claude — the exact characters claude-code uses (⏺ ⎿). Some fonts",
            "           show these as empty boxes; if that happens, switch back.",
          ].join("\n"),
        };
      }
      const mode = args[0].toLowerCase();
      if (!modes.includes(mode as never)) {
        return { output: `Unknown glyph set "${mode}". Available: ${modes.join(", ")}` };
      }
      setGlyphs(mode as never);
      const g = getGlyphs();
      return {
        output: `Glyphs set to ${mode}.  ${g.assistant} marker   ${g.elbow.trim()} elbow` +
          (mode === "claude" ? "\nIf those show as boxes, your font lacks them — /glyphs unicode goes back." : ""),
        repaint: true,
      };
    }

    case "theme": {
      const { setInkTheme, getInkThemeName, inkThemeNames } = await import("./theme.js");
      const available = inkThemeNames();
      if (!args[0]) {
        return { output: `Theme: ${getInkThemeName()}\nAvailable: ${available.join("  ")}\nUsage: /theme <name>` };
      }
      const name = args[0].toLowerCase();
      if (!available.includes(name as never)) {
        return { output: `Unknown theme "${name}". Available: ${available.join(", ")}` };
      }
      setInkTheme(name as never);
      // Keep the classic UI's theme in step so the two surfaces agree.
      const { setTheme } = await import("../theme.js");
      setTheme(name as "dark" | "light" | "safe");
      return { output: `Theme set to ${name}.`, repaint: true };
    }

    // ── Inspection ──────────────────────────────────────────────────────────
    case "usage": {
      const cost = rt?.cost;
      if (!cost) return { output: "No usage recorded yet." };
      const lines = [cost.summary()];
      const detail = cost.breakdown?.();
      if (detail && detail.trim()) lines.push("", detail);
      if (typeof rt.serverCreditsRemaining === "number" && rt.serverCreditsRemaining >= 0) {
        lines.push("", `Credits remaining: ${rt.serverCreditsRemaining}`);
      }
      return { output: lines.join("\n") };
    }

    case "context": {
      const sub = (args[0] ?? "show").toLowerCase();
      if (sub === "clear") {
        rt?.reset?.();
        return { output: "Context cleared." };
      }
      const stats = rt?.context?.stats?.();
      if (!stats) return { output: "Context unavailable." };
      return {
        output: [
          `Messages:  ${stats.messageCount}`,
          `Tokens:    ~${stats.estimatedTokens.toLocaleString()} / ${stats.contextLimit.toLocaleString()}`,
          `Used:      ${stats.usagePercent.toFixed(1)}%${stats.compacted ? " (compacted)" : ""}`,
        ].join("\n"),
      };
    }

    case "tools": {
      if ((args[0] ?? "").toLowerCase() === "reset") {
        rt?.dispatcher?.resetBuiltInApprovals?.();
        return { output: "Tool permissions reset." };
      }
      return { output: rt?.dispatcher?.renderBuiltInToolsList?.() || "No tools registered." };
    }

    case "mcp": {
      const mcp = rt?.mcp;
      if (!mcp?.isInitialized?.()) return { output: "No MCP servers connected." };
      const defs = mcp.getToolDefinitions?.() ?? [];
      const names = defs.map((d: any) => `  ${d.name}`).join("\n");
      return { output: `MCP — ${defs.length} tool${defs.length === 1 ? "" : "s"}\n${names}` };
    }

    case "hooks":
      return hooks();

    case "settings":
      return settings();

    case "transcript":
      return { output: renderTranscript(ctx.transcript) };

    case "changelog":
      return changelog();

    case "logdump":
      return logdump(rt, ctx);

    case "upgrade-agent":
      return { busy: true, ...(await upgradeAgent()) };

    // ── Clipboard / composing ───────────────────────────────────────────────
    case "copy": {
      const last = [...ctx.transcript].reverse().find((m) => m.role === "assistant");
      if (!last) return { output: "No assistant response to copy yet." };
      try {
        const { default: clipboard } = await import("clipboardy");
        await clipboard.write(last.content);
        return { output: "Last response copied to clipboard." };
      } catch {
        return { output: "Clipboard unavailable on this system." };
      }
    }

    case "paste": {
      try {
        // readClipboard tries the image first and prints nothing, which
        // matters here: ink owns the screen, so the console.log-based
        // handlePasteCommand the classic UI uses would be erased on the next
        // frame. Reading text only, as this did, meant a screenshot on the
        // clipboard came through as an empty paste.
        const { readClipboard } = await import("../clipboard.js");
        const clip = await readClipboard();

        if (clip.type === "image" && clip.imageBase64) {
          const kb = Math.round((clip.imageBase64.length * 3) / 4 / 1024);
          return {
            attachImage: {
              imageBase64: clip.imageBase64,
              mimeType: clip.mimeType ?? "image/png",
            },
            output: `Image attached (${kb} KB). It goes with your next message.`,
          };
        }

        if (clip.type === "text" && clip.text?.trim()) {
          return { inputValue: clip.text, output: `Pasted ${clip.text.length} chars into the prompt.` };
        }
        return { output: "Clipboard is empty." };
      } catch {
        return { output: "Clipboard unavailable on this system." };
      }
    }

    case "editor":
      return {
        output:
          "The rich UI owns the terminal, so $EDITOR cannot be opened over it.\n" +
          "Paste multi-line text with /paste, or run BHARATBUILD_CLASSIC_UI=1 bharatbuild chat for the editor flow.",
      };

    case "reply": {
      const last = [...ctx.transcript].reverse().find((m) => m.role === "assistant");
      if (!last) return { output: "No assistant response to reply to yet." };
      const quoted = last.content.split("\n").map((l) => `> ${l}`).join("\n");
      return { inputValue: `${quoted}\n\n`, output: "Quoted the last response — continue typing your reply." };
    }

    // ── Agent tools (delegate to the real implementations) ──────────────────
    case "goal":
      return goal(args);

    case "knowledge":
      return knowledge(args);

    case "todos":
      return todos(args);

    case "guide":
      return { busy: true, ...(await guide(rt, args)) };

    case "checkpoint":
      return checkpoint(args);

    case "code":
      return code(args);

    case "prompts":
      return prompts(args);

    case "spec":
      return spec(args);

    case "spawn":
      return spawn(rt, args);

    default:
      return { output: explainUnknown(cmd, "tui") };
  }
}

// ── Individual handlers ───────────────────────────────────────────────────────

async function title(rt: any, args: string[]): Promise<SlashResult> {
  const sm = rt?.sessions;
  if (!sm) return { output: "Session store unavailable." };
  const current = sm.list().find((s: any) => s.id === rt.sessionId);
  if (args.length === 0) {
    return { output: `Title: "${current?.title ?? "Untitled Session"}"\n\nUsage: /title <new title>` };
  }
  const newTitle = args.join(" ");
  sm.save(
    rt.sessionId,
    {
      title: newTitle,
      model: current?.model ?? "auto",
      createdAt: current?.createdAt ?? Date.now(),
      updatedAt: Date.now(),
      messageCount: rt.context?.messages?.length ?? 0,
      workingDir: process.cwd(),
    },
    rt.context,
  );
  return { output: `Session title set to "${newTitle}".` };
}

async function chat(rt: any, args: string[]): Promise<SlashResult> {
  const sm = rt?.sessions;
  if (!sm) return { output: "Session store unavailable." };
  const sub = (args[0] ?? "list").toLowerCase();

  if (sub === "new") {
    rt.reset?.();
    return { clear: true, output: "Started a new session." };
  }

  const sessions = sm.list().sort((a: any, b: any) => b.updatedAt - a.updatedAt);
  if (sessions.length === 0) return { output: "No saved sessions." };

  if (sub === "list") {
    const lines = sessions.slice(0, 15).map((s: any, i: number) => {
      const when = new Date(s.updatedAt).toLocaleString("en-IN", { hour12: false });
      const mark = s.id === rt.sessionId ? "▸" : " ";
      return `  ${mark} ${String(i + 1).padStart(2)}. ${(s.title ?? "Untitled").slice(0, 40).padEnd(40)} ${s.messageCount} msgs  ${when}`;
    });
    return { output: [`Sessions (${sessions.length})`, "", ...lines, "", "Switch with: /chat <number>"].join("\n") };
  }

  const n = parseInt(sub, 10);
  if (Number.isNaN(n) || n < 1 || n > sessions.length) {
    return { output: `Usage: /chat <list|new|number>  (1–${sessions.length})` };
  }
  const target = sessions[n - 1];
  const ok = rt.resume?.(target.id);
  return ok
    ? { clear: true, output: `Resumed "${target.title ?? "Untitled"}".` }
    : { output: `Could not resume session ${target.id}.` };
}

async function rewind(rt: any, args: string[]): Promise<SlashResult> {
  // Shares userTurns/keepBefore with the esc-esc picker: two definitions of
  // "a turn" would eventually disagree about where the cut falls.
  const all = rt?.context?.messages ?? [];
  const turns = userTurns(all);

  if (turns.length === 0) return { output: "No conversation to rewind." };

  if (!args[0]) {
    const lines = turns.map((t, i) => `  ${String(i + 1).padStart(2)}. ${t.preview}`);
    return {
      output: [
        "Rewind — fork from a turn:", "",
        ...lines, "",
        "Usage: /rewind <number>   (or press esc twice)",
      ].join("\n"),
    };
  }

  const n = parseInt(args[0], 10);
  if (Number.isNaN(n) || n < 1 || n > turns.length) {
    return { output: `Pick a turn between 1 and ${turns.length}.` };
  }
  const kept = keepBefore(all, turns[n - 1]!);
  rt.context.clear();
  rt.context.pushAll(kept);
  return { output: `Forked from turn ${n}. ${kept.length} message(s) kept — continue to branch from here.` };
}

async function spawn(rt: any, args: string[]): Promise<SlashResult> {
  const task = args.join(" ").trim();
  if (!task) {
    return { output: "Usage: /spawn <task>\n\nRuns planner → coder → tester in a dependency graph." };
  }
  const { executeDag } = await import("../../crew/dag-executor.js");
  const { loadConfig } = await import("../../config/config.js");
  const model = loadConfig().model ?? "auto";
  const stages = [
    { name: "plan", task: `Plan the implementation for: ${task}`, agent: "planner", model, depends_on: [] },
    { name: "code", task: `Implement: ${task}`, agent: "coder", model, depends_on: ["plan"] },
    { name: "test", task: `Write tests for: ${task}`, agent: "tester", model, depends_on: ["code"] },
  ];
  const result = await executeDag({ stages });
  const lines = result.stages.map(
    (s: any) => `  ${s.error ? "✗" : "✓"} ${s.name}${s.durationMs ? `  ${s.durationMs}ms` : ""}`,
  );
  const combined = result.stages.map((s: any) => `[${s.name}]\n${String(s.output ?? "").slice(0, 1000)}`).join("\n\n---\n\n");
  rt?.context?.push?.({ role: "assistant", content: `Parallel agents completed:\n\n${combined}` });
  return {
    output: [
      result.success ? `Agents finished (${result.totalDurationMs}ms)` : "Some agents failed",
      "",
      ...lines,
      "",
      "Results added to context.",
    ].join("\n"),
  };
}

function goal(args: string[]): SlashResult | Promise<SlashResult> {
  return (async () => {
    const { executeGoal } = await import("../../tools/agent/goal.js");
    const sub = (args[0] ?? "status").toLowerCase();
    if (sub === "status" || sub === "list") {
      const { listGoals } = await import("../../tools/agent/goal.js");
      const goals = listGoals();
      if (goals.length === 0) return { output: "No goals yet.\n\nUsage: /goal <description>" };
      return {
        output: goals
          .map((g: any) => `  ${g.status === "complete" ? "✓" : "○"} ${g.description}  (${g.status})`)
          .join("\n"),
      };
    }
    if (sub === "complete" || sub === "cancel") {
      const { listGoals, updateGoal } = await import("../../tools/agent/goal.js");
      const active = listGoals().find((g: any) => g.status !== "complete");
      if (!active) return { output: "No active goal." };
      updateGoal(active.id, { status: sub === "complete" ? "complete" : "cancelled" } as any);
      return { output: `Goal ${sub === "complete" ? "completed" : "cancelled"}: ${active.description}` };
    }
    const res = executeGoal({ command: "create", description: args.join(" "), criteria: [] });
    return { output: res.content };
  })();
}

async function knowledge(args: string[]): Promise<SlashResult> {
  const { executeKnowledge } = await import("../../tools/agent/knowledge.js");
  const sub = (args[0] ?? "show").toLowerCase();
  const rest = args.slice(1).join(" ");
  if (sub === "show" || sub === "list") return { output: executeKnowledge({ command: "list" }).content };
  if (sub === "search") return { output: executeKnowledge({ command: "search", query: rest }).content };
  if (sub === "remove") return { output: executeKnowledge({ command: "remove", id: rest }).content };
  if (sub === "add") {
    if (!rest) return { output: "Usage: /knowledge add <text>" };
    return { output: executeKnowledge({ command: "add", name: rest.slice(0, 40), content: rest }).content };
  }
  return { output: "Usage: /knowledge <show|add|search|remove>" };
}

async function todos(args: string[]): Promise<SlashResult> {
  const { executeTodo, getAllLists } = await import("../../tools/agent/todo.js");
  const sub = (args[0] ?? "list").toLowerCase();
  const rest = args.slice(1).join(" ");

  if (sub === "list") {
    const lists = getAllLists();
    if (lists.length === 0) return { output: "No todo lists.\n\nUsage: /todos add <task>" };
    const lines: string[] = [];
    for (const l of lists as any[]) {
      lines.push(`${l.title}`);
      for (const item of l.items) lines.push(`  ${item.completed ? "✓" : "○"} ${item.description}`);
    }
    return { output: lines.join("\n") };
  }

  if (sub === "add") {
    if (!rest) return { output: "Usage: /todos add <task>" };
    const lists = getAllLists() as any[];
    const listId = lists[0]?.id ?? (executeTodo({ command: "create", title: "Session tasks" }), (getAllLists() as any[])[0]?.id);
    return { output: executeTodo({ command: "add", list_id: listId, description: rest }).content };
  }

  if (sub === "complete" || sub === "remove") {
    if (!rest) return { output: `Usage: /todos ${sub} <item-id>` };
    const lists = getAllLists() as any[];
    return { output: executeTodo({ command: "complete", list_id: lists[0]?.id, item_id: rest }).content };
  }

  return { output: "Usage: /todos <list|add|complete|remove>" };
}

async function guide(rt: any, args: string[]): Promise<SlashResult> {
  const question = args.join(" ").trim();
  if (!question) return { output: "Usage: /guide <question>" };
  const model = rt?.modelClient;
  if (!model) return { output: "No model client available for the guide agent." };
  const { executeGuide } = await import("../../tools/agent/guide.js");
  const res = await executeGuide({ question } as any, model);
  return { output: res.content };
}

async function checkpoint(args: string[]): Promise<SlashResult> {
  const { CheckpointManager } = await import("../../tools/checkpoint/checkpoint-manager.js");
  const m = new CheckpointManager();
  const sub = (args[0] ?? "list").toLowerCase();
  const rest = args.slice(1).join(" ");

  try {
    if (sub === "init") {
      const cp = await m.init(rest || undefined);
      return { output: `Checkpoint created: ${cp.name}\n  ID: ${cp.id}  Files: ${cp.files.length}` };
    }
    if (sub === "list") {
      const all = m.list();
      if (all.length === 0) return { output: "No checkpoints. Create one with /checkpoint init [name]" };
      return {
        output: all
          .slice(0, 15)
          .map((c: any) => `  ${c.id.slice(0, 8)}  ${String(c.name).padEnd(24)} ${c.files.length} files  ${new Date(c.createdAt).toLocaleString("en-IN", { hour12: false })}`)
          .join("\n"),
      };
    }
    if (sub === "restore") {
      if (!rest) return { output: "Usage: /checkpoint restore <id>" };
      const r = await m.restore(rest);
      return { output: `Restored ${r.restored.length} file(s); skipped ${r.skipped.length}.` };
    }
    if (sub === "diff") {
      if (!rest) return { output: "Usage: /checkpoint diff <id>" };
      const d: any = await m.diff(rest);
      const fmt = (label: string, arr: string[]) => (arr?.length ? `${label}:\n${arr.map((f) => `  ${f}`).join("\n")}` : "");
      return {
        output: [fmt("Modified", d.modified), fmt("Added", d.added), fmt("Deleted", d.deleted)]
          .filter(Boolean)
          .join("\n\n") || "No changes since that checkpoint.",
      };
    }
  } catch (err) {
    return { output: `Checkpoint failed: ${(err as Error).message}` };
  }
  return { output: "Usage: /checkpoint <init|list|restore|diff>" };
}

async function code(args: string[]): Promise<SlashResult> {
  const sub = (args[0] ?? "overview").toLowerCase();
  const fs = await import("fs");
  const path = await import("path");

  if (sub === "overview" || sub === "init") {
    const { scanRepository } = await import("../../context/repository-scanner.js");
    // RepoSummary is { totalFiles, languages, topFiles, stack } and the call is
    // synchronous. Reading `.files` gave a permanent "Files: 0".
    const scan = scanRepository(process.cwd());

    // `languages` holds every extension seen — hundreds of entries on a large
    // tree, which printed as a wall of text that buried the conversation.
    const TOP = 10;
    const ranked = Object.entries(scan.languages)
      .filter(([ext]) => /^[a-z0-9+#]{1,10}$/i.test(ext))
      .sort((a, b) => b[1] - a[1]);
    const typeLines = ranked.slice(0, TOP).map(([ext, n]) => `  ${ext.padEnd(10)} ${n}`);
    if (ranked.length > TOP) typeLines.push(`  … ${ranked.length - TOP} more file types`);

    const s = scan.stack as unknown as Record<string, string | undefined>;
    const stackLines = Object.entries(s)
      .filter(([, v]) => v && v !== "unknown")
      .map(([k, v]) => `  ${k.padEnd(16)} ${v}`);

    return {
      output: [
        `Directory:  ${process.cwd()}`,
        `Files:      ${scan.totalFiles.toLocaleString()}`,
        ...(stackLines.length ? ["", "Stack", ...stackLines] : []),
        ...(typeLines.length ? ["", "Top file types", ...typeLines] : []),
      ].join("\n"),
    };
  }

  if (sub === "status" || sub === "logs") {
    const { execSync } = await import("child_process");
    try {
      const out = execSync(sub === "status" ? "git status --short" : "git log --oneline -15", {
        encoding: "utf8",
        timeout: 5000,
        cwd: process.cwd(),
      });
      return { output: out.trim() || (sub === "status" ? "Working tree clean." : "No commits.") };
    } catch {
      return { output: "Not a git repository (or git is unavailable)." };
    }
  }

  void fs; void path;
  return { output: "Usage: /code <init|overview|status|logs>" };
}

async function prompts(args: string[]): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  const os = await import("os");
  const dir = path.join(os.homedir(), ".bharatbuild", "prompts");
  fs.mkdirSync(dir, { recursive: true });

  const sub = (args[0] ?? "list").toLowerCase();
  const name = args[1];

  if (sub === "list") {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md"));
    if (files.length === 0) return { output: `No prompt templates in ${dir}\n\nCreate one: /prompts create <name>` };
    return { output: [`Prompts (${files.length})`, "", ...files.map((f) => `  ${f.replace(/\.md$/, "")}`)].join("\n") };
  }

  if (!name) return { output: `Usage: /prompts ${sub} <name>` };
  const file = path.join(dir, `${name}.md`);

  if (sub === "get") {
    if (!fs.existsSync(file)) return { output: `No prompt named "${name}".` };
    return { output: fs.readFileSync(file, "utf8") };
  }
  if (sub === "create") {
    if (fs.existsSync(file)) return { output: `"${name}" already exists — use /prompts edit ${name}.` };
    fs.writeFileSync(file, `# ${name}\n\n`, "utf8");
    return { output: `Created ${file}` };
  }
  if (sub === "edit") {
    return { output: fs.existsSync(file) ? `Edit this file directly:\n  ${file}` : `No prompt named "${name}".` };
  }
  return { output: "Usage: /prompts <list|get|create|edit> [name]" };
}

async function spec(args: string[]): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  const sub = (args[0] ?? "view").toLowerCase();
  const specDir = path.join(process.cwd(), ".bharatbuild", "spec");

  if (sub === "new") {
    fs.mkdirSync(specDir, { recursive: true });
    const file = path.join(specDir, "requirements.md");
    if (fs.existsSync(file)) return { output: `Spec already exists:\n  ${file}` };
    fs.writeFileSync(file, "# Requirements\n\n## Goals\n\n## Acceptance criteria\n\n", "utf8");
    return { output: `Created ${file}` };
  }

  if (sub === "view") {
    const file = path.join(specDir, "requirements.md");
    if (!fs.existsSync(file)) return { output: "No spec found. Create one with /spec new" };
    return { output: fs.readFileSync(file, "utf8").slice(0, 4000) };
  }

  if (sub === "run" || sub === "analyze") {
    return {
      output:
        `/spec ${sub} runs the full spec workflow, which is only wired up in the standalone command.\n` +
        `Run it outside the session:  bharatbuild spec ${sub}`,
    };
  }

  return { output: "Usage: /spec <new|view|run|analyze>" };
}

async function hooks(): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  const os = await import("os");
  const file = path.join(os.homedir(), ".bharatbuild", "hooks.json");
  if (!fs.existsSync(file)) return { output: `No hooks configured.\n  ${file}\n\nManage with: bharatbuild hooks list` };
  try {
    const cfg = JSON.parse(fs.readFileSync(file, "utf8")) as Record<string, unknown[]>;
    const lines = Object.entries(cfg).map(([evt, list]) => `  ${evt.padEnd(20)} ${Array.isArray(list) ? list.length : 0} hook(s)`);
    return { output: ["Hooks", "", ...lines].join("\n") };
  } catch {
    return { output: `Could not parse ${file}` };
  }
}

async function settings(): Promise<SlashResult> {
  const { loadConfig } = await import("../../config/config.js");
  const cfg = loadConfig() as unknown as Record<string, unknown>;
  const lines = Object.entries(cfg)
    .filter(([k]) => !/token|secret|key/i.test(k))
    .map(([k, v]) => `  ${k.padEnd(18)} ${String(v)}`);
  return { output: ["Settings", "", ...lines, "", "Change with: bharatbuild settings <key> <value>"].join("\n") };
}

async function changelog(): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  let version = "unknown";
  try {
    version = (JSON.parse(fs.readFileSync(path.join(process.cwd(), "package.json"), "utf8")) as any).version ?? "unknown";
  } catch { /* no package.json here */ }

  for (const dir of [process.cwd(), path.join(process.cwd(), "..")]) {
    const file = path.join(dir, "CHANGELOG.md");
    if (fs.existsSync(file)) {
      const body = fs.readFileSync(file, "utf8").split("\n").slice(0, 40).join("\n");
      return { output: `v${version}\n\n${body}` };
    }
  }
  return { output: `v${version}\n\nNo CHANGELOG.md found in this project.` };
}

async function upgradeAgent(): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  const { execSync } = await import("child_process");
  let local = "unknown";
  try {
    local = (JSON.parse(fs.readFileSync(path.join(process.cwd(), "package.json"), "utf8")) as any).version ?? "unknown";
  } catch { /* ignore */ }

  try {
    const latest = execSync("npm show @bharatbuild/cli version", {
      encoding: "utf8", timeout: 8000, stdio: ["pipe", "pipe", "pipe"],
    }).trim();
    if (!latest) throw new Error("empty");
    return {
      output:
        latest === local
          ? `Installed v${local} — up to date.`
          : `Installed v${local}\nLatest    v${latest}\n\nUpdate: npm install -g @bharatbuild/cli`,
    };
  } catch {
    return { output: `Installed v${local}\n\nCould not reach the npm registry to check for updates.` };
  }
}

async function logdump(rt: any, ctx: SlashContext): Promise<SlashResult> {
  const fs = await import("fs");
  const path = await import("path");
  const os = await import("os");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = path.join(os.homedir(), ".bharatbuild", "logs");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `bharatbuild-${stamp}.log`);

  const lines = [
    "BharatBuild CLI — Session Log",
    `Generated:   ${new Date().toISOString()}`,
    `Working dir: ${process.cwd()}`,
    `Session:     ${rt?.sessionId ?? "n/a"}`,
    `Model:       ${ctx.model}`,
    `Agent:       ${ctx.agent}`,
    `Usage:       ${rt?.cost?.summary?.() ?? "n/a"}`,
    `Node:        ${process.version}  (${process.platform})`,
    "─".repeat(60),
    "",
  ];
  for (const m of ctx.transcript) {
    lines.push(`[${m.timestamp.toISOString()}] ${m.role.toUpperCase()}`, m.content, "");
  }
  fs.writeFileSync(file, lines.join("\n"), "utf8");
  return { output: `Log written to:\n  ${file}\n\n${ctx.transcript.length} messages. Attach this when reporting an issue.` };
}

function renderTranscript(transcript: SlashContext["transcript"]): string {
  if (transcript.length === 0) return "Transcript is empty.";
  return transcript
    .map((m) => {
      const t = m.timestamp.toLocaleTimeString("en-IN", { hour12: false });
      return `[${t}] ${m.role}\n${m.content}`;
    })
    .join("\n\n");
}

/**
 * Compact help. One line per command overflowed a normal terminal (37 commands
 * plus 11 shortcuts ≈ 50 rows), and the excess rendered as garbled overlap.
 * Names go in a grid — the palette already shows descriptions as you type.
 */
function renderHelp(): string {
  const cmds = commandsFor("tui");
  const names = cmds.map((c) => `/${c.name}`);
  const colWidth = Math.max(...names.map((n) => n.length)) + 2;
  const cols = Math.max(1, Math.floor(76 / colWidth));
  const rows = Math.ceil(names.length / cols);

  const lines = [`Commands (${names.length}) — type / to search, Tab to complete`, ""];
  for (let r = 0; r < rows; r++) {
    let line = "  ";
    for (let c = 0; c < cols; c++) {
      const n = names[c * rows + r];
      if (n) line += n.padEnd(colWidth);
    }
    lines.push(line.replace(/\s+$/, ""));
  }

  lines.push("", "Shortcuts");
  const shortcuts = shortcutsFor("tui");
  const keyWidth = Math.max(...shortcuts.map((s) => s.key.length)) + 2;
  for (const s of shortcuts) {
    lines.push(`  ${s.key.padEnd(keyWidth)}${s.description}`);
  }
  return lines.join("\n");
}

/** Registry entries this surface does not implement — asserted by the drift test. */
export function inkUnhandled(): string[] {
  return commandsFor("tui")
    .filter((c) => !INK_HANDLED.has(c.name) && !(c.aliases ?? []).some((a) => INK_HANDLED.has(a)))
    .map((c) => c.name);
}

export { lookupSlash };
