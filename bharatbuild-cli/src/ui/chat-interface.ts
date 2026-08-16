import readline from "readline";
import chalk from "chalk";
import { EventEmitter } from "events";
import { printStatusBar, type StatusBarState } from "./status-bar.js";
import { printKeyBindings } from "./key-bindings.js";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export class ChatInterface extends EventEmitter {
  private rl: readline.Interface;
  private history: string[] = [];
  private historyIndex = -1;
  private status: StatusBarState;

  constructor(status: StatusBarState) {
    super();
    this.status = status;
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });
    this._setupKeyHandlers();
  }

  private _setupKeyHandlers() {
    process.stdin.setRawMode?.(false); // safe fallback
    this.rl.on("SIGINT", () => this.emit("cancel"));
  }

  printWelcome(version: string) {
    console.clear();
    console.log(chalk.bold.cyan(`
  ╭──────────────────────────────────────╮
  │   BharatBuild CLI  v${version.padEnd(20)}│
  │   AI-powered development assistant  │
  ╰──────────────────────────────────────╯`));
    console.log(chalk.dim("  Type your message and press Enter. Ctrl+C to cancel, Ctrl+D to exit."));
    console.log(chalk.dim("  Type /help for commands, /keys for key bindings.\n"));
    printStatusBar(this.status);
    console.log();
  }

  updateStatus(updates: Partial<StatusBarState>) {
    this.status = { ...this.status, ...updates };
  }

  async prompt(): Promise<string> {
    return new Promise((resolve) => {
      this.rl.question(chalk.bold.green("  ❯ "), (input) => {
        const trimmed = input.trim();
        if (trimmed) this.history.unshift(trimmed);
        this.historyIndex = -1;
        resolve(trimmed);
      });
    });
  }

  startStreaming() {
    this.updateStatus({ thinking: true });
    process.stdout.write(chalk.bold.cyan("\n  BharatBuild: "));
  }

  streamChunk(text: string) {
    process.stdout.write(text);
  }

  endStreaming() {
    this.updateStatus({ thinking: false });
    process.stdout.write("\n\n");
    printStatusBar(this.status);
    console.log();
  }

  showToolCall(name: string, input: Record<string, unknown>) {
    const preview = JSON.stringify(input).slice(0, 60);
    console.log(chalk.dim(`\n  🔧 ${chalk.yellow(name)}(${preview}${preview.length >= 60 ? "…" : ""})`));
  }

  showToolResult(name: string, isError: boolean, ms: number) {
    const icon = isError ? chalk.red("✗") : chalk.green("✓");
    console.log(chalk.dim(`  ${icon} ${name} (${ms}ms)`));
  }

  handleSlashCommand(input: string): boolean {
    const [cmd, ...args] = input.slice(1).split(" ");
    switch (cmd) {
      case "help":
        console.log(chalk.bold("\n  Commands:"));
        console.log("    /help         Show this help");
        console.log("    /keys         Show key bindings");
        console.log("    /clear        Clear screen");
        console.log("    /model <id>   Switch model");
        console.log("    /exit         Exit");
        console.log();
        return true;
      case "keys":
        printKeyBindings();
        return true;
      case "clear":
        console.clear();
        printStatusBar(this.status);
        console.log();
        return true;
      case "exit":
      case "quit":
        this.close();
        process.exit(0);
      case "model":
        if (args[0]) { this.emit("model-change", args[0]); return true; }
        console.log(chalk.dim("  Usage: /model <model-id>"));
        return true;
      default:
        return false;
    }
  }

  close() {
    this.rl.close();
  }
}
