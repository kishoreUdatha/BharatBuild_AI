import chalk from "chalk";

export type RenderMode = "chat" | "task" | "build" | "test";

export interface RenderContext {
  mode: RenderMode;
  model: string;
  sessionId?: string;
}

export function renderHeader(ctx: RenderContext) {
  const modeColors: Record<RenderMode, typeof chalk> = {
    chat: chalk.cyan,
    task: chalk.yellow,
    build: chalk.blue,
    test: chalk.green,
  };
  const color = modeColors[ctx.mode] ?? chalk.white;
  console.log(color.bold(`\n  [${ctx.mode.toUpperCase()}] `) + chalk.dim(`model: ${ctx.model}${ctx.sessionId ? ` | session: ${ctx.sessionId.slice(0, 8)}` : ""}`));
  console.log(chalk.dim("  " + "─".repeat((process.stdout.columns ?? 80) - 4)));
}

export function renderThinking(dots = 1) {
  const spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  const frame = spinner[dots % spinner.length] ?? "⠋";
  process.stdout.write(`\r  ${chalk.magenta(frame)} ${chalk.dim("thinking...")}`);
}

export function clearThinking() {
  process.stdout.write("\r" + " ".repeat(30) + "\r");
}

export function renderError(msg: string) {
  console.log(chalk.red(`\n  ❌ ${msg}\n`));
}

export function renderSuccess(msg: string) {
  console.log(chalk.green(`\n  ✅ ${msg}\n`));
}

export function renderCodeBlock(code: string, lang = "") {
  const border = chalk.dim("  " + "─".repeat(60));
  console.log(border);
  if (lang) console.log(chalk.dim(`  ${lang}`));
  for (const line of code.split("\n")) {
    console.log(chalk.dim("  │ ") + line);
  }
  console.log(border);
}
