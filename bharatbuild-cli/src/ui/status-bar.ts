import chalk from "chalk";

export interface StatusBarState {
  model: string;
  mode?: string;
  tokens?: number;
  cost?: number;
  session?: string;
  thinking?: boolean;
}

export function renderStatusBar(state: StatusBarState): string {
  const parts: string[] = [];
  parts.push(chalk.bold.cyan(` ${state.model}`));
  if (state.mode) parts.push(chalk.dim(`|`) + chalk.yellow(` ${state.mode}`));
  if (state.tokens) parts.push(chalk.dim(`|`) + chalk.dim(` ${state.tokens.toLocaleString()} tokens`));
  if (state.cost) parts.push(chalk.dim(`|`) + chalk.dim(` $${state.cost.toFixed(4)}`));
  if (state.thinking) parts.push(chalk.dim(`|`) + chalk.cyan(` ⠋ thinking...`));
  const bar = parts.join(" ");
  const width = process.stdout.columns ?? 80;
  const padded = bar.padEnd(width);
  return `${chalk.bgBlack(padded)}`;
}

export function printStatusBar(state: StatusBarState) {
  process.stdout.write(`\r${renderStatusBar(state)}\n`);
}
