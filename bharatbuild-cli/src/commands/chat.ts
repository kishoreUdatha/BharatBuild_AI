/**
 * BharatBuild CLI - chat command
 *
 * Matches all Kiro CLI chat flags:
 *   --resume            Resume most recent session
 *   --resume-id <id>    Resume specific session by ID
 *   --resume-picker     Interactive session picker
 *   --list-sessions     List saved sessions and exit
 *   --delete-session    Delete a session by ID
 *   --agent <name>      Start with a specific agent
 *   --trust-all-tools   Skip tool confirmation prompts
 *   --effort <level>    Set reasoning effort (low/medium/high/xhigh/max)
 *   --no-interactive    Print first response to stdout without TUI
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { AgentRuntime } from "../runtime/agent-runtime.js";
import { SessionManager } from "../runtime/session-manager.js";
import { loadConfig } from "../config/config.js";
import { loadCredentials } from "../auth/credentials.js";
import type { CLIConfig } from "../config/config.js";
import { createModelClientAuto, isAutoModel } from "../models/model-router.js";
import { TUISession } from "../ui/tui-session.js";
import { pickSession } from "../ui/session-picker.js";

export interface ChatOpts {
  model?:          string;
  resume?:         boolean;
  resumeId?:       string;
  resumePicker?:   boolean;
  listSessions?:   boolean;
  deleteSession?:  string;
  agent?:          string;
  trustAllTools?:  boolean;
  effort?:         string;
  noInteractive?:  boolean;
}

// Agent role system prompts (matches /agent slash command)
const AGENT_PROMPTS: Record<string, string> = {
  default:  "You are BharatBuild AI, an expert software engineer assistant.",
  planner:  "You are a senior software architect. Break tasks into clear implementation plans.",
  coder:    "You are an expert software engineer. Write clean, production-quality code.",
  tester:   "You are a QA engineer. Write comprehensive tests and ensure they pass.",
  fixer:    "You are a debugging expert. Identify root causes and apply minimal fixes.",
  reviewer: "You are a code reviewer. Check for bugs, security issues, and quality problems.",
};

// Effort → model tier mapping
const EFFORT_MODEL: Record<string, string> = {
  low:   "haiku",
  medium: "haiku",
  high:  "sonnet",
  xhigh: "sonnet",
  max:   "opus",
};

export async function chatCommand(
  initialPrompt: string | undefined,
  opts: ChatOpts,
  _config: CLIConfig,
  client: BharatBuildClient
): Promise<void> {
  const config = loadConfig();
  const creds  = loadCredentials();
  const sm     = new SessionManager();

  // ── --list-sessions ────────────────────────────────────────────────────────
  if (opts.listSessions) {
    const sessions = sm.list().sort((a, b) => b.updatedAt - a.updatedAt);
    if (sessions.length === 0) {
      console.log(chalk.dim("\n  No saved sessions.\n"));
      return;
    }
    console.log(chalk.bold(`\n  💬 Saved Sessions (${sessions.length})\n`));
    for (const s of sessions.slice(0, 30)) {
      const age  = Math.round((Date.now() - s.updatedAt) / 60000);
      const when = age < 60 ? `${age}m ago` : age < 1440 ? `${Math.round(age / 60)}h ago` : `${Math.round(age / 1440)}d ago`;
      console.log(
        `  ${chalk.cyan(s.id.slice(-8))}  ${chalk.bold(s.title.slice(0, 44).padEnd(44))}  ` +
        `${chalk.dim(when.padEnd(10))}  ${chalk.dim(s.model)}`
      );
    }
    console.log(chalk.dim("\n  Resume: bharatbuild chat --resume-id <id-suffix>\n"));
    return;
  }

  // ── --delete-session ───────────────────────────────────────────────────────
  if (opts.deleteSession) {
    const sessions = sm.list();
    const match = sessions.find((s) => s.id === opts.deleteSession || s.id.endsWith(opts.deleteSession!));
    if (!match) {
      console.log(chalk.red(`\n  ✗ Session not found: ${opts.deleteSession}\n`));
      process.exit(1);
    }
    sm.delete(match.id);
    console.log(chalk.green(`\n  ✓ Deleted session: "${match.title}"\n`));
    return;
  }

  if (!creds) {
    // Allow direct API key usage without login (like setting ANTHROPIC_API_KEY)
    const hasDirectKey =
      process.env["ANTHROPIC_API_KEY"] ||
      process.env["OPENAI_API_KEY"]    ||
      process.env["GEMINI_API_KEY"]    ||
      process.env["GOOGLE_API_KEY"];

    if (!hasDirectKey) {
      console.error(chalk.red("\n✗ Not logged in. Run: bharatbuild login\n"));
      console.log(chalk.dim("  Or set ANTHROPIC_API_KEY environment variable to use directly.\n"));
      process.exit(1);
    }
    console.log(chalk.dim("  Using direct API key (no login required)\n"));
  }

  // ── Resolve model (effort overrides model tier) ────────────────────────────
  let activeModel = opts.model ?? config.model ?? "auto";
  if (opts.effort && EFFORT_MODEL[opts.effort]) {
    activeModel = EFFORT_MODEL[opts.effort]!;
    console.log(chalk.dim(`  effort: ${opts.effort} → model tier: ${activeModel}\n`));
  }
  const usingAuto = isAutoModel(activeModel);

  // ── Build model client ─────────────────────────────────────────────────────
  const hasDirectKey =
    process.env["ANTHROPIC_API_KEY"] ||
    process.env["OPENAI_API_KEY"]    ||
    process.env["GEMINI_API_KEY"]    ||
    process.env["GOOGLE_API_KEY"];

  const modelClient = hasDirectKey
    ? createModelClientAuto(activeModel)
    : {
        async *complete(params: {
          model: string; system: string; messages: unknown[];
          tools: object[]; maxTokens: number; signal?: AbortSignal;
        }): AsyncIterable<import("../runtime/agent-loop.js").ModelChunk> {
          const stream = client.streamSSE("/api/v1/chat/stream", {
            model: usingAuto ? "auto" : activeModel,
            system: params.system, messages: params.messages,
            tools: params.tools, max_tokens: params.maxTokens,
          });
          for await (const event of stream) {
            const d = event.data as Record<string, unknown>;
            if (event.type === "text_delta")   yield { type: "text_delta", text: String(d["text"] ?? "") };
            else if (event.type === "tool_use") yield { type: "tool_use", toolUseId: String(d["id"] ?? ""), toolName: String(d["name"] ?? ""), toolInput: d["input"] as Record<string, unknown> };
            else if (event.type === "usage")    yield { type: "usage", inputTokens: Number(d["input_tokens"] ?? 0), outputTokens: Number(d["output_tokens"] ?? 0) };
            else if (event.type === "stop")     yield { type: "stop", stopReason: (d["stop_reason"] as "end_turn") ?? "end_turn" };
          }
        },
      };

  // ── Build AgentRuntime ─────────────────────────────────────────────────────
  const runtime = new AgentRuntime({
    config: { ...config, model: activeModel },
    model:  modelClient,
  });

  // ── Apply --agent flag (set system prompt) ─────────────────────────────────
  if (opts.agent) {
    const prompt = AGENT_PROMPTS[opts.agent] ?? AGENT_PROMPTS["default"]!;
    runtime.context.setSystemPrompt(
      `${prompt}\n\nWorking directory: ${config.workingDir}\n` +
      `You have access to tools for reading/writing files, running commands, searching code, and git.`
    );
    console.log(chalk.dim(`  agent: ${opts.agent}\n`));
  }

  // ── Apply --trust-all-tools ────────────────────────────────────────────────
  if (opts.trustAllTools) {
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    console.log(chalk.dim("  trust-all-tools: enabled\n"));
  }

  // ── Session resume logic ───────────────────────────────────────────────────
  if (opts.resumeId) {
    const sessions = sm.list();
    const match = sessions.find((s) => s.id === opts.resumeId || s.id.endsWith(opts.resumeId!));
    if (match) {
      runtime.resume(match.id);
      console.log(chalk.dim(`  Resumed: "${match.title}" (${match.messageCount} messages)\n`));
    } else {
      console.log(chalk.red(`  ✗ Session not found: ${opts.resumeId}\n`));
    }
  } else if (opts.resumePicker) {
    const sessions = sm.list().sort((a, b) => b.updatedAt - a.updatedAt);
    const uiSessions = sessions.map((s) => ({
      id: s.id, title: s.title,
      timestamp: new Date(s.updatedAt).toISOString(),
      messageCount: s.messageCount,
    }));
    const picked = await pickSession(uiSessions);
    if (picked) {
      runtime.resume(picked.id);
      console.log(chalk.dim(`  Resumed: "${picked.title}"\n`));
    }
  } else if (opts.resume) {
    // Resume most recent session for this working dir
    const sessions = sm.list()
      .filter((s) => s.workingDir === config.workingDir)
      .sort((a, b) => b.updatedAt - a.updatedAt);
    if (sessions[0]) {
      runtime.resume(sessions[0].id);
      console.log(chalk.dim(`  Resumed: "${sessions[0].title}"\n`));
    } else {
      console.log(chalk.dim("  No previous session for this directory. Starting fresh.\n"));
    }
  }

  // ── Non-interactive mode ───────────────────────────────────────────────────
  if (opts.noInteractive || initialPrompt) {
    runtime.events.on("text", (e) => { if (e.type === "text" && e.content) process.stdout.write(e.content); });
    runtime.events.on("tool_call", (e) => { if (e.type === "tool_call") console.log(chalk.dim(`\n  ● ${e.toolName}(${JSON.stringify(e.input).slice(0, 60)}…)`)); });
    runtime.events.on("error", (e) => { if (e.type === "error") console.error(chalk.red(`\n✗ ${e.message}\n`)); });
    runtime.events.on("complete", (e) => { if (e.type === "complete") console.log(chalk.dim(`\n\n  tokens: ${e.totalTokens} | turns: ${e.turns} | ${e.durationMs}ms\n`)); });
    if (initialPrompt) await runtime.run(initialPrompt);
    return;
  }

  // ── Interactive TUI mode ───────────────────────────────────────────────────
  // Use ink-based rich TUI (Kiro-style) by default; fall back to classic on error
  const useRichTUI = process.env["BHARATBUILD_CLASSIC_UI"] !== "1" && process.stdout.isTTY;

  if (useRichTUI) {
    try {
      const { startInkTUI } = await import("../ui/ink/index.js");
      const instance = startInkTUI({
        runtime,
        model: activeModel,
        mode: "developer",
      });
      await instance.waitUntilExit();
      return;
    } catch {
      // Fall back to classic TUI if ink fails (e.g. no TTY, missing deps)
    }
  }

  // Classic TUI fallback
  const tui = new TUISession({
    runtime,
    model: activeModel,
    mode:  "developer",
  });

  await tui.start();
}
