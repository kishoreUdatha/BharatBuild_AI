/**
 * Hooks Runtime — wires FileWatcher + HookRunner into actual agent execution.
 *
 * Gap 5 fix: hooks now run via AgentRuntime (full tool access) instead of
 * a bare model.complete() call with tools:[]. A hook agent can read/write
 * files, run commands, search code, etc. — matching Kiro CLI behaviour.
 */
import chalk from "chalk";
import { FileWatcher, type FileChangeEvent } from "./file-watcher.js";
import { HookRunner } from "./hook-runner.js";
import { loadHooksConfig, type HookDefinition } from "./hook-config.js";
import { loadConfig } from "../config/config.js";
import { loadCredentials } from "../auth/credentials.js";
import { createModelClientAuto } from "../models/model-router.js";
import { AgentRuntime } from "../runtime/agent-runtime.js";
import type { HookEvent } from "./hook-config.js";
import { resolveModel } from "../config/constants.js";
import { rolePrompt } from "../agents/apply-agent.js";

/**
 * What a hook adds on top of the role.
 *
 * This used to be a fourth full copy of the role prompts, which meant the
 * "coder" description drifted from the registry's. Only the second half was
 * ever hook-specific, so that is all that lives here now — the role itself
 * comes from the registry like everywhere else.
 */
const HOOK_CONTEXT: Record<string, string> = {
  default:  "A file hook event has fired. Take appropriate action based on the event and file.",
  coder:    "A code file has changed. Review the change and take any needed action (e.g. fix lint errors, update imports, run tests).",
  tester:   "A source file changed. Check if tests need updating and run the relevant test suite.",
  reviewer: "A file was saved. Review it for obvious issues and report findings concisely.",
  fixer:    "A file event occurred. Identify and fix any issues introduced.",
};

function hookPrompt(role: string): string {
  const key = (role ?? "").trim().toLowerCase();
  return `${rolePrompt(key)} ${HOOK_CONTEXT[key] ?? HOOK_CONTEXT["default"]!}`;
}

export class HooksRuntime {
  private watcher: FileWatcher;
  private runner: HookRunner;
  private active = false;

  constructor(private dir?: string) {
    this.watcher = new FileWatcher(300);
    this.runner = new HookRunner(
      (hook, ctx) => this._executeHook(hook, ctx),
      dir
    );
  }

  private async _executeHook(
    hook: HookDefinition,
    ctx: { event: HookEvent; filePath?: string; payload?: Record<string, unknown> }
  ): Promise<void> {
    const config = loadConfig();
    const creds = loadCredentials();

    const hasKey =
      creds?.token ||
      process.env["ANTHROPIC_API_KEY"] ||
      process.env["OPENAI_API_KEY"] ||
      process.env["GEMINI_API_KEY"];

    if (!hasKey) {
      console.log(chalk.dim(`  [hook] ${hook.name} skipped — no API key`));
      return;
    }

    const prompt = hook.prompt
      ? hook.prompt
          .replace("{{file}}", ctx.filePath ?? "")
          .replace("{{event}}", ctx.event)
      : `A file event occurred: ${ctx.event}${ctx.filePath ? ` on ${ctx.filePath}` : ""}. Take appropriate action.`;

    console.log(chalk.dim(`\n  🪝 Hook triggered: ${chalk.yellow(hook.name)} [${ctx.event}]`));
    if (ctx.filePath) console.log(chalk.dim(`     File: ${ctx.filePath}`));

    try {
      const modelId = resolveModel(config.model);
      const modelClient = createModelClientAuto(modelId, creds?.token);

      // Use full AgentRuntime so the hook agent has complete tool access
      // (read_file, write_file, execute_command, search_code, git_*, etc.)
      const runtime = new AgentRuntime({
        config: { ...config, model: modelId, maxTurns: 10 },
        model: modelClient,
      });

      // Override system prompt with hook-specific agent role
      const agentRole = hook.agent ?? "default";
      runtime.context.setSystemPrompt(
        `${hookPrompt(agentRole)}\n\nWorking directory: ${config.workingDir}\n` +
        `You have full tool access. Keep responses concise — this is a background hook, not an interactive session.`
      );

      // Stream output to terminal
      process.stdout.write(chalk.dim("  🤖 "));
      runtime.events.on("text", (event) => {
        if (event.type === "text" && event.content) {
          process.stdout.write(event.content);
        }
      });
      runtime.events.on("tool_call", (event) => {
        if (event.type === "tool_call") {
          process.stdout.write(chalk.dim(`\n     🔧 ${event.toolName}…`));
        }
      });

      await runtime.run(prompt);
      process.stdout.write("\n\n");
    } catch (err) {
      console.log(chalk.red(`  [hook] Error: ${err instanceof Error ? err.message : err}`));
    }
  }

  start(watchDir?: string): void {
    // Starting twice would register a second "change" listener on the same
    // watcher, so every hook would fire twice per save. This is a module-level
    // singleton reached from more than one entry point, so that is a question
    // of which command you typed, not of anything the user did.
    if (this.active) return;

    const dir = watchDir ?? this.dir ?? process.cwd();
    const config = loadHooksConfig(dir);

    if (config.hooks.length === 0) return; // nothing to watch

    const hasFileHooks = config.hooks.some((h) =>
      ["file-saved", "file-created", "file-deleted"].includes(h.event)
    );

    if (hasFileHooks) {
      this.watcher.watch(dir);
      this.watcher.on("change", (change: FileChangeEvent) => {
        void this.runner.runForFileChange(change);
      });
      console.log(chalk.dim(`  🪝 File watcher active (${config.hooks.length} hook(s))\n`));
    }

    this.active = true;
  }

  async runEvent(event: HookEvent, payload?: Record<string, unknown>): Promise<void> {
    await this.runner.runForEvent(event, payload);
  }

  stop(): void {
    this.watcher.stop();
    this.active = false;
  }

  isActive(): boolean { return this.active; }
}

export const hooksRuntime = new HooksRuntime();
