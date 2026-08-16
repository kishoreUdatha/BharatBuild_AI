/**
 * BharatBuild CLI - Interactive REPL with Mode Switching
 * Auto model selection is active by default — best model chosen per request.
 */

import readline from "readline";
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { loadCredentials, clearCredentials, whoami } from "../api/auth.js";
import { printBanner, printModeSelector, Spinner } from "./spinner.js";
import type { CLIConfig } from "../config/config.js";
import { isAutoModel } from "../models/auto-select.js";
import { MODEL_TIERS } from "../config/constants.js";
import { explainUnknown, commandsFor } from "./slash-registry.js";
import { renderHelpPanel } from "./panels/help-panel.js";

export type PlatformMode =
  | "student"
  | "developer"
  | "founder"
  | "college"
  | "api-partner";

export type ModeHandler = (
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
) => Promise<void>;

export type ModeHandlers = Map<PlatformMode, ModeHandler>;

const MODE_EMOJI: Record<PlatformMode, string> = {
  student: "🎓",
  developer: "💻",
  founder: "🚀",
  college: "🏫",
  "api-partner": "🔌",
};

const HELP_TIPS = `
${chalk.bold("Tips:")}
  • Type naturally - describe what you want to build
  • Switch modes with /mode developer, /mode student, etc.
  • Each mode has a guided menu: type /menu for prompts
  • Model auto-selects the best AI per request — or pin with /model <id>
  • Sessions are auto-saved — use /session list to see them
`;

const AVAILABLE_MODELS = [
  "auto",
  // Claude — primary tiers
  MODEL_TIERS.haiku,
  MODEL_TIERS.sonnet,
  MODEL_TIERS.opus,
  // Claude — previous versions
  MODEL_TIERS.sonnet46,
  MODEL_TIERS.sonnet45,
  MODEL_TIERS.sonnet40,
  MODEL_TIERS.opus48,
  MODEL_TIERS.opus47,
  MODEL_TIERS.opus46,
  MODEL_TIERS.opus45,
  // GPT-5.6
  MODEL_TIERS.gpt56sol,
  MODEL_TIERS.gpt56terra,
  MODEL_TIERS.gpt56luna,
  // Budget open-weight
  MODEL_TIERS.deepseek,
  MODEL_TIERS.minimax25,
  MODEL_TIERS.minimax21,
  MODEL_TIERS.glm5,
  MODEL_TIERS.qwen3,
];

export class BharatBuildREPL {
  private mode: PlatformMode = "developer";
  private rl: readline.Interface | null = null;
  private running = false;
  /** Active AgentRuntime — set when the REPL runs in agent/chat mode. */
  _runtime: import("../runtime/agent-runtime.js").AgentRuntime | null = null;
  /** Last user input line — used as default session title on /session save. */
  _lastInput: string | null = null;

  constructor(
    private config: CLIConfig,
    private client: BharatBuildClient,
    private handlers: ModeHandlers
  ) {}

  setMode(mode: PlatformMode): void {
    this.mode = mode;
    console.log(
      chalk.green(
        `\n  ${MODE_EMOJI[mode]} Switched to ${chalk.bold(mode)} mode\n`
      )
    );
  }

  /** Returns the current active model label for display */
  private getActiveModel(): string {
    return this.config.model ?? "auto";
  }

  private getPrompt(): string {
    const emoji = MODE_EMOJI[this.mode] ?? ">";
    const model = this.getActiveModel();
    const modelLabel = isAutoModel(model) ? chalk.cyan("auto") : chalk.dim(model.split("-")[0]);
    return `${chalk.bold.green("bharatbuild")} ${chalk.dim(`[${this.mode}|${modelLabel}]`)}> `;
  }

  private async handleSlashCommand(input: string): Promise<void> {
    const parts = input.slice(1).trim().split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);

    // If user just typed "/" with nothing else, show all commands
    if (!cmd) {
      renderHelpPanel("repl");
      return;
    }

    switch (cmd) {
      case "help":
      case "h":
        // Command list comes from the slash registry so it cannot drift from
        // what this dispatcher actually handles; HELP_TEXT keeps the tips.
        renderHelpPanel("repl");
        console.log(HELP_TIPS);
        break;

      case "mode": {
        const target = args[0] as PlatformMode;
        const validModes: PlatformMode[] = [
          "student",
          "developer",
          "founder",
          "college",
          "api-partner",
        ];
        if (!target || !validModes.includes(target)) {
          console.log(chalk.yellow("Usage: /mode <student|developer|founder|college|api-partner>"));
          printModeSelector();
        } else {
          this.setMode(target);
        }
        break;
      }

      case "model": {
        const targetModel = args[0];
        if (!targetModel) {
          // Show current + available models
          const current = this.getActiveModel();
          console.log(chalk.bold("\n🤖 AI Model Selection:\n"));
          for (const m of AVAILABLE_MODELS) {
            const active = m === current ? chalk.green(" ✓ active") : "";
            const desc =
              m === "auto"
                ? chalk.dim(" — best model selected per request (default)")
                : chalk.dim(` — ${m}`);
            console.log(`  ${chalk.cyan(m.padEnd(36))}${desc}${active}`);
          }
          console.log(chalk.dim("\n  Usage: /model <model-id>  e.g. /model auto\n"));
        } else {
          if (!AVAILABLE_MODELS.includes(targetModel)) {
            console.log(chalk.yellow(`\n  ⚠ Unknown model: ${targetModel}`));
            console.log(chalk.dim("  Run /model to see available models.\n"));
          } else {
            this.config = { ...this.config, model: targetModel };
            if (isAutoModel(targetModel)) {
              console.log(chalk.green(`\n  ✓ Model set to auto — best model selected per request\n`));
            } else {
              console.log(chalk.green(`\n  ✓ Model set to: ${chalk.bold(targetModel)}\n`));
            }
            // Persist to config
            const { saveConfig } = await import("../config/config.js");
            saveConfig({ model: targetModel });
          }
        }
        break;
      }

      case "modes":
        printModeSelector();
        break;

      case "reset":
        if (this._runtime) {
          this._runtime.reset();
          console.log(chalk.dim("\n  Context cleared. Starting fresh.\n"));
        } else {
          console.log(chalk.dim("\n  No active session to reset.\n"));
        }
        break;

      case "session": {
        const subCmd = (args[0] ?? "list").toLowerCase();
        const { SessionManager } = await import("../runtime/session-manager.js");
        const sm = new SessionManager();

        if (subCmd === "list") {
          const sessions = sm.list().sort((a, b) => b.updatedAt - a.updatedAt);
          if (sessions.length === 0) {
            console.log(chalk.dim("\n  No saved sessions.\n"));
          } else {
            console.log(chalk.bold(`\n  💾 Saved Sessions (${sessions.length})\n`));
            for (const s of sessions.slice(0, 20)) {
              const age  = Math.round((Date.now() - s.updatedAt) / 60000);
              const when = age < 60 ? `${age}m ago` : age < 1440 ? `${Math.round(age / 60)}h ago` : `${Math.round(age / 1440)}d ago`;
              console.log(
                `  ${chalk.cyan(s.id.slice(-8))}  ${chalk.bold(s.title.slice(0, 45).padEnd(45))}  ` +
                `${chalk.dim(when)}  ${chalk.dim(s.model)}`
              );
            }
            console.log(chalk.dim("\n  Load with: /session load <id-suffix>\n"));
          }
        } else if (subCmd === "save") {
          if (!this._runtime) {
            console.log(chalk.yellow("\n  No active runtime to save.\n"));
            break;
          }
          const title = args.slice(1).join(" ") || this._lastInput?.slice(0, 60) || "manual save";
          const id = this._runtime.sessionId;
          this._runtime["_session"].save(id, {
            title,
            model:        this.config.model ?? "auto",
            createdAt:    Date.now(),
            updatedAt:    Date.now(),
            messageCount: this._runtime.context.messages.length,
            workingDir:   this.config.workingDir ?? process.cwd(),
          }, this._runtime.context);
          console.log(chalk.green(`\n  ✓ Session saved: ${chalk.bold(id.slice(-8))} — "${title}"\n`));
        } else if (subCmd === "load") {
          const idSuffix = args[1] ?? "";
          if (!idSuffix) {
            console.log(chalk.yellow("\n  Usage: /session load <id-suffix>\n  Run /session list to see IDs.\n"));
            break;
          }
          // Match by full ID or trailing suffix
          const sessions = sm.list();
          const match = sessions.find((s) => s.id === idSuffix || s.id.endsWith(idSuffix));
          if (!match) {
            console.log(chalk.red(`\n  ✗ Session not found: ${idSuffix}\n`));
            break;
          }
          if (this._runtime) {
            const ok = this._runtime.resume(match.id);
            if (ok) {
              console.log(chalk.green(`\n  ✓ Resumed session: "${match.title}" (${match.messageCount} messages)\n`));
            } else {
              console.log(chalk.red(`\n  ✗ Failed to load session data.\n`));
            }
          } else {
            console.log(chalk.yellow("\n  No active runtime — start chatting first, then /session load.\n"));
          }
        } else {
          console.log(chalk.yellow(`\n  Unknown session subcommand: ${subCmd}\n  Use: /session list | /session save [name] | /session load <id>\n`));
        }
        break;
      }

      case "login": {
        const { interactiveLogin } = await import("../commands/login.js");
        await interactiveLogin(this.client, this.config);
        break;
      }

      case "logout":
        clearCredentials();
        this.client.clearToken();
        console.log(chalk.dim("\n  Logged out.\n"));
        break;

      case "whoami": {
        const spinner = new Spinner();
        spinner.start("Fetching account info…");
        try {
          const info = await whoami(this.client);
          spinner.succeed();
          console.log();
          console.log(`  ${chalk.bold("Name:")}    ${info.name}`);
          console.log(`  ${chalk.bold("Email:")}   ${info.email}`);
          console.log(`  ${chalk.bold("Plan:")}    ${chalk.cyan(info.tier)}`);
          console.log(`  ${chalk.bold("Tokens:")}  ${chalk.green(info.tokenBalance.toLocaleString())}`);
          console.log();
        } catch (err) {
          spinner.fail();
          console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : err}\n`));
        }
        break;
      }

      case "projects": {
        const spinner = new Spinner();
        spinner.start("Loading projects…");
        try {
          const data = await this.client.get<{ projects?: unknown[]; items?: unknown[] }>(
            "/api/v1/projects?limit=20"
          );
          spinner.succeed();
          const list = data.projects ?? data.items ?? (Array.isArray(data) ? data : []);
          if (list.length === 0) {
            console.log(chalk.dim("\n  No projects yet.\n"));
          } else {
            console.log(chalk.bold(`\n  Your Projects (${list.length}):\n`));
            for (const p of list as Array<Record<string, unknown>>) {
              const name = String(p.name ?? p.project_name ?? p.id ?? "Unnamed");
              const id = String(p.id ?? "").slice(0, 8);
              const status = String(p.status ?? "").toLowerCase();
              const statusColor =
                status === "completed" || status === "done"
                  ? chalk.green(status)
                  : status === "failed"
                  ? chalk.red(status)
                  : chalk.yellow(status || "unknown");
              console.log(
                `  ${chalk.cyan("•")} ${chalk.bold(name)} ${chalk.dim(`[${id}]`)} ${statusColor}`
              );
            }
            console.log();
          }
        } catch (err) {
          spinner.fail();
          console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : err}\n`));
        }
        break;
      }

      case "tokens": {
        const spinner = new Spinner();
        spinner.start("Fetching token balance…");
        try {
          const data = await this.client.get<{
            balance?: number;
            tokens_remaining?: number;
            used?: number;
          }>("/api/v1/tokens/balance");
          spinner.succeed();
          const balance = data.balance ?? data.tokens_remaining ?? 0;
          const used = data.used ?? 0;
          console.log();
          console.log(`  ${chalk.bold("Token Balance:")} ${chalk.green(balance.toLocaleString())}`);
          if (used) console.log(`  ${chalk.bold("Used:")}          ${used.toLocaleString()}`);
          console.log();
        } catch (err) {
          spinner.fail();
          console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : err}\n`));
        }
        break;
      }

      case "menu": {
        const handler = this.handlers.get(this.mode);
        if (handler) {
          await handler("__menu__", this.client, this.config);
        } else {
          console.log(chalk.yellow(`\n  No menu available for ${this.mode} mode.\n`));
        }
        break;
      }

      case "exit":
      case "quit":
      case "q":
        console.log(chalk.dim("\nGoodbye! 👋\n"));
        this.running = false;
        break;

      default:
        // Consult the registry so a command that lives on the other surface
        // says so, instead of reading as a missing feature.
        console.log(chalk.yellow(`\n  ${explainUnknown(cmd, "repl")}\n`));
    }
  }

  async start(): Promise<void> {
    this.running = true;

    printBanner();

    // Show login status
    const creds = loadCredentials();
    if (creds) {
      console.log(
        `  ${chalk.dim("✓")} Logged in as ${chalk.green(creds.name)} ${chalk.dim(`(${creds.tier})`)}`
      );
      this.client.setToken(creds.token);
    } else {
      console.log(
        `  ${chalk.yellow("⚠")}  Not logged in — run ${chalk.cyan("bharatbuild login")} or type ${chalk.cyan("/login")}`
      );
    }

    // Show active model
    const activeModel = this.getActiveModel();
    const modelDisplay = isAutoModel(activeModel)
      ? chalk.cyan("auto") + chalk.dim(" (best model selected per request)")
      : chalk.cyan(activeModel);
    console.log(
      `  ${chalk.dim("🤖")} Model: ${modelDisplay}  ${chalk.dim("(change with /model <id>)")}`
    );

    console.log(
      `  ${chalk.dim("🎯")} Mode: ${chalk.cyan(this.mode)}  ${chalk.dim("(change with /mode <name>)")}`
    );
    console.log(
      `  ${chalk.dim("💡")} Type ${chalk.cyan("/help")} for commands or ${chalk.cyan("/menu")} for guided options`
    );
    console.log();

    // Build slash command completion list for this surface
    const slashCommands = commandsFor("repl").map((c) => `/${c.name}`);

    const completer = (line: string): [string[], string] => {
      if (line.startsWith("/")) {
        const hits = slashCommands.filter((c) => c.startsWith(line));
        // Show all commands if user just typed "/"
        return [hits.length ? hits : slashCommands, line];
      }
      return [[], line];
    };

    // Create readline interface with slash-command autocomplete
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: this.getPrompt(),
      completer,
    });

    this.rl.prompt();

    this.rl.on("line", async (line) => {
      const input = line.trim();

      if (!input) {
        this.rl!.setPrompt(this.getPrompt());
        this.rl!.prompt();
        return;
      }

      // Slash command
      if (input.startsWith("/")) {
        await this.handleSlashCommand(input);
        if (!this.running) {
          this.rl!.close();
          return;
        }
        this.rl!.setPrompt(this.getPrompt());
        this.rl!.prompt();
        return;
      }

      // Bare words convenience
      if (input.toLowerCase() === "exit" || input.toLowerCase() === "quit") {
        await this.handleSlashCommand("/exit");
        this.rl!.close();
        return;
      }
      if (input.toLowerCase() === "help") {
        await this.handleSlashCommand("/help");
        this.rl!.setPrompt(this.getPrompt());
        this.rl!.prompt();
        return;
      }

      // Dispatch to current mode handler — pass config with active model
      this._lastInput = input;
      const handler = this.handlers.get(this.mode);
      if (handler) {
        try {
          await handler(input, this.client, this.config);
        } catch (err) {
          console.error(
            chalk.red(`\n✗ Error: ${err instanceof Error ? err.message : String(err)}\n`)
          );
        }
      } else {
        console.log(chalk.yellow(`\n  No handler for mode: ${this.mode}\n`));
      }

      this.rl!.setPrompt(this.getPrompt());
      this.rl!.prompt();
    });

    this.rl.on("close", () => {
      if (this.running) {
        console.log(chalk.dim("\nGoodbye! 👋\n"));
      }
      process.exit(0);
    });

    // Handle Ctrl+C gracefully
    process.on("SIGINT", () => {
      console.log(chalk.dim("\n\nGoodbye! 👋\n"));
      process.exit(0);
    });

    // Keep process alive while REPL is running
    await new Promise<void>((resolve) => {
      this.rl!.on("close", resolve);
    });
  }
}