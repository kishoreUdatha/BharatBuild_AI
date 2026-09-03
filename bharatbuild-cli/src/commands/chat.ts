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
import { pickSession } from "../ui/session-picker.js";
import { applyAgent } from "../agents/apply-agent.js";
import { AGENTIC_CHAT_STREAM } from "../api/endpoints.js";
import { hooksRuntime } from "../hooks/hooks-runtime.js";
import { modelRoute, describeRoute } from "../api/model-route.js";
import { resolveProviderKey } from "../auth/provider-key.js";

export interface ChatOpts {
  model?:          string;
  resume?:         boolean;
  /** Alias for `resume`; commander fills whichever flag was used. */
  continue?:       boolean;
  resumeId?:       string;
  resumePicker?:   boolean;
  listSessions?:   boolean;
  deleteSession?:  string;
  agent?:          string;
  trustAllTools?:  boolean;
  effort?:         string;
  noInteractive?:  boolean;
}

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

  // A direct provider key works without logging in, from the environment or
  // from the stored file. The route banner below reports which, on every path.
  if (!creds && !resolveProviderKey()) {
    console.error(chalk.red("\n✗ Not logged in, and no API key.\n"));
    console.log(chalk.dim("  Run: bharatbuild login\n"));
    console.log(chalk.dim("  Or:  bharatbuild key set sk-ant-…    (stored once, every terminal)\n"));
    process.exit(1);
  }

  // ── Resolve model (effort overrides model tier) ────────────────────────────
  let activeModel = opts.model ?? config.model ?? "auto";
  if (opts.effort && EFFORT_MODEL[opts.effort]) {
    activeModel = EFFORT_MODEL[opts.effort]!;
    console.log(chalk.dim(`  effort: ${opts.effort} → model tier: ${activeModel}\n`));
  }
  const usingAuto = isAutoModel(activeModel);

  // ── Build model client ─────────────────────────────────────────────────────
  // Environment or stored file — see resolveProviderKey for why both.
  const directKey = resolveProviderKey();

  const modelClient = directKey
    ? createModelClientAuto(activeModel, directKey.key)
    : {
        async *complete(params: {
          model: string; system: string; messages: unknown[];
          tools: object[]; maxTokens: number; signal?: AbortSignal;
        }): AsyncIterable<import("../runtime/agent-loop.js").ModelChunk> {
          const stream = client.streamSSE(AGENTIC_CHAT_STREAM, {
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

  /*
   * ── Where the model calls are going ────────────────────────────────────────
   *
   * Printed on every start, both routes. Previously only the direct path
   * announced itself, and only when logged out — so being logged in and routed
   * through the server was silent, and the first sign of which path you were
   * on was a turn failing. When the server's model account ran out of credit,
   * the provider's "your credit balance is too low" read as though the user's
   * own key was dead.
   */
  console.log(chalk.dim(`  ${describeRoute(modelRoute(runtime.isProxied, process.env, config.apiBaseUrl), activeModel)}\n`));

  /*
   * ── Hooks ──────────────────────────────────────────────────────────────────
   *
   * This used to be started by the bare `bharatbuild` action only, so the file
   * watcher and git hooks ran or did not run depending on whether you typed
   * `bharatbuild` or `bharatbuild chat` — the same session either way, and
   * nothing on screen explained the difference. Starting it here covers every
   * route into a chat, interactive or not.
   */
  hooksRuntime.start(config.workingDir);

  // ── Apply --agent flag ─────────────────────────────────────────────────────
  // This used a local six-entry prompt map while the registry defines ten
  // agents, and fell back to the default prompt for anything missing — so
  // `--agent guide` and `--agent typo` both silently started a normal session.
  if (opts.agent) {
    let applied;
    try {
      applied = applyAgent(runtime, opts.agent, config.workingDir);
    } catch (err) {
      console.error(chalk.red(`\n  ${err instanceof Error ? err.message : err}\n`));
      process.exitCode = 1;
      return;
    }
    const badge = applied.readOnly ? chalk.yellow(" [read-only]") : "";
    console.log(chalk.dim(`  agent: ${applied.role}${badge}\n`));
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
  } else if (opts.resume || opts.continue) {
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

  /*
   * ── Interactive TUI ────────────────────────────────────────────────────────
   *
   * There used to be a second, complete chat interface here (TUISession) that
   * ran whenever this one could not. It was a fork in every sense: none of the
   * ink UI's behaviour existed in it, and features drifted between the two —
   * `!` and `@file` lived only in the fallback for months, while the approval
   * dialog, prompt history and rewind lived only here. Anyone piping output or
   * running without a TTY silently got the older interface.
   *
   * An interactive chat needs a terminal. Without one, say so and point at the
   * non-interactive path rather than starting a lesser interface.
   */
  if (!process.stdout.isTTY) {
    console.error(
      chalk.yellow("\n  Interactive chat needs a terminal.\n") +
      chalk.dim("  This looks like a pipe or a redirect. For non-interactive use:\n\n") +
      chalk.dim("    bharatbuild chat \"your question\"\n") +
      chalk.dim("    bharatbuild chat --no-interactive\n") +
      chalk.dim("    bharatbuild ask \"your question\"\n"),
    );
    process.exitCode = 1;
    return;
  }

  const { startInkTUI } = await import("../ui/ink/index.js");
  const instance = startInkTUI({
    runtime,
    model: activeModel,
    mode: "developer",
  });
  await instance.waitUntilExit();
  // An active fs.watch keeps the event loop alive, so the process would sit
  // there after the UI had gone.
  hooksRuntime.stop();
}
