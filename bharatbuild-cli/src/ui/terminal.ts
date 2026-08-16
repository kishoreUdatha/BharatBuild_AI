import chalk from "chalk";
import readline from "readline";
export function printSuccess(msg: string) { console.log(chalk.green(`\n✅ ${msg}\n`)); }
export function printError(msg: string) { console.log(chalk.red(`\n❌ ${msg}\n`)); }
export function printWarning(msg: string) { console.log(chalk.yellow(`\n⚠  ${msg}\n`)); }
export function printInfo(msg: string) { console.log(chalk.cyan(`\n💡 ${msg}\n`)); }
export function printDivider(label?: string) {
  const w = process.stdout.columns ?? 80;
  if (label) { const p = Math.max(0, (w - label.length - 2) / 2); console.log(chalk.dim("─".repeat(p) + " " + label + " " + "─".repeat(p))); }
  else console.log(chalk.dim("─".repeat(w)));
}
export async function confirm(q: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((r) => rl.question(chalk.cyan(`${q} [y/N]: `), (a) => { rl.close(); r(a.trim().toLowerCase() === "y"); }));
}
