/**
 * BharatBuild CLI — Spinner & UI Utilities
 */

import chalk from "chalk";
import ora, { type Ora } from "ora";

// ── Spinner ───────────────────────────────────────────────────────────────────

export class Spinner {
  private _ora: Ora;

  constructor() {
    this._ora = ora({ spinner: "dots", color: "cyan" });
  }

  start(text: string): void {
    this._ora.start(chalk.cyan(text));
  }

  succeed(text?: string): void {
    this._ora.succeed(text ? chalk.green(text) : undefined);
  }

  fail(text?: string): void {
    this._ora.fail(text ? chalk.red(text) : undefined);
  }

  update(text: string): void {
    this._ora.text = chalk.cyan(text);
  }

  stop(): void {
    this._ora.stop();
  }

  get isSpinning(): boolean {
    return this._ora.isSpinning;
  }
}

// ── Progress Renderer ─────────────────────────────────────────────────────────

export class ProgressRenderer {
  private buffer = "";
  private spinner: Spinner;
  private started = false;

  constructor(private writeFn: (text: string) => void = process.stdout.write.bind(process.stdout)) {
    this.spinner = new Spinner();
  }

  onStage(stage: string, status: "start" | "done" | "error"): void {
    if (this.spinner.isSpinning) this.spinner.stop();

    if (status === "start") {
      this.spinner.start(`${stage}…`);
    } else if (status === "done") {
      this.spinner.succeed(chalk.green(`✓ ${stage}`));
    } else {
      this.spinner.fail(chalk.red(`✗ ${stage}`));
    }
  }

  onChunk(text: string): void {
    if (this.spinner.isSpinning) this.spinner.stop();
    if (!this.started) {
      this.writeFn("\n");
      this.started = true;
    }
    this.buffer += text;
    this.writeFn(text);
  }

  onComplete(): void {
    if (this.spinner.isSpinning) this.spinner.stop();
    if (this.buffer) this.writeFn("\n");
    this.buffer = "";
    this.started = false;
  }

  onError(msg: string): void {
    if (this.spinner.isSpinning) this.spinner.fail();
    console.error(chalk.red(`\n✗ Error: ${msg}`));
    this.started = false;
  }
}

// ── Banner ────────────────────────────────────────────────────────────────────
//
//  Tricolor scheme  →  saffron (#FF9933)  white  green (#138808)
//  Layout: ASCII wordmark (7-row block font) inside a rounded box
//  Width: 58 cols — fits a default 80-col terminal with room to breathe

const SAFFRON = chalk.hex("#FF9933");
const INDIA_GREEN = chalk.hex("#138808");
const NAVY = chalk.hex("#000080");   // Ashoka Chakra navy

export function printBanner(): void {
  const B = chalk.bold;
  const D = chalk.dim;
  const W = chalk.white;
  const C = chalk.cyan;

  // top border
  console.log(C("  ╭──────────────────────────────────────────────────────╮"));

  // blank row
  console.log(C("  │") + " ".repeat(56) + C("│"));

  // ASCII wordmark — saffron rows
  console.log(C("  │") + "  " + SAFFRON.bold(
    "██████╗ ██╗  ██╗ █████╗ ██████╗  █████╗ ████████╗"
  ) + "  " + C("│"));
  console.log(C("  │") + "  " + SAFFRON.bold(
    "██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝"
  ) + "  " + C("│"));
  // white rows
  console.log(C("  │") + "  " + B.white(
    "██████╔╝███████║███████║██████╔╝███████║   ██║   "
  ) + "  " + C("│"));
  console.log(C("  │") + "  " + B.white(
    "██╔══██╗██╔══██║██╔══██║██╔══██╗██╔══██║   ██║   "
  ) + "  " + C("│"));
  // green rows
  console.log(C("  │") + "  " + INDIA_GREEN.bold(
    "██████╔╝██║  ██║██║  ██║██║  ██║██║  ██║   ██║   "
  ) + "  " + C("│"));
  console.log(C("  │") + "  " + INDIA_GREEN.bold(
    "╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═╝   "
  ) + "  " + C("│"));

  // blank row
  console.log(C("  │") + " ".repeat(56) + C("│"));

  // version line only
  const ver = "  " + NAVY.bold("BharatBuild") + D("  ·  ") + W.bold("v1.0.0") + "                            ";
  console.log(C("  │") + ver + C("│"));

  // bottom border
  console.log(C("  ╰──────────────────────────────────────────────────────╯"));
  console.log();
}

// ── Mode Selector ─────────────────────────────────────────────────────────────

export function printModeSelector(): void {
  console.log(chalk.bold("\nAvailable modes:"));
  console.log(
    `  ${chalk.cyan("student")}      🎓 Academic projects, SRS, UML, code, docs, viva`
  );
  console.log(
    `  ${chalk.cyan("developer")}    💻 Code generation, Bolt-style project builder`
  );
  console.log(
    `  ${chalk.cyan("founder")}      🚀 PRD, business plan, GTM strategy`
  );
  console.log(
    `  ${chalk.cyan("college")}      🏫 Faculty management, batch tracking, analytics`
  );
  console.log(
    `  ${chalk.cyan("api-partner")}  🔌 API keys, token usage, billing`
  );
  console.log();
}

// ── Table ─────────────────────────────────────────────────────────────────────

export function printTable(headers: string[], rows: string[][]): void {
  if (rows.length === 0) {
    console.log(chalk.dim("  (no results)"));
    return;
  }

  const allRows = [headers, ...rows];
  const widths = headers.map((h, i) =>
    Math.max(h.length, ...rows.map((r) => (r[i] ?? "").length))
  );

  const line = "+" + widths.map((w) => "-".repeat(w + 2)).join("+") + "+";

  console.log(chalk.dim(line));
  console.log(
    chalk.bold(
      "|" +
        headers.map((h, i) => ` ${h.padEnd(widths[i])} `).join("|") +
        "|"
    )
  );
  console.log(chalk.dim(line));

  for (const row of rows) {
    console.log(
      "|" +
        headers.map((_, i) => ` ${(row[i] ?? "").padEnd(widths[i])} `).join("|") +
        "|"
    );
  }

  console.log(chalk.dim(line));
  console.log(chalk.dim(`  ${rows.length} row(s)`));
}

// ── Prompt helper ─────────────────────────────────────────────────────────────

import readline from "readline";

export async function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(chalk.cyan(question), (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

export async function promptPassword(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  // Disable echo for password
  (rl as any).stdoutMuted = true;
  (rl as any)._writeToOutput = function (str: string) {
    if ((rl as any).stdoutMuted) process.stdout.write("");
    else process.stdout.write(str);
  };
  return new Promise((resolve) => {
    rl.question(chalk.cyan(question), (answer) => {
      (rl as any).stdoutMuted = false;
      process.stdout.write("\n");
      rl.close();
      resolve(answer.trim());
    });
  });
}
