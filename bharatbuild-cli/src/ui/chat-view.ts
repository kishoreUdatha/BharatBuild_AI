import chalk from "chalk";
export function renderUserMessage(msg: string) { console.log(chalk.bold.cyan("\n  You: ") + msg); }
export function renderAssistantChunk(chunk: string) { process.stdout.write(chunk); }
export function renderAssistantDone() { console.log("\n"); }
export function renderToolCall(toolName: string, input: Record<string, unknown>) {
  const p = JSON.stringify(input).slice(0, 80);
  console.log(chalk.dim(`\n  🔧 ${chalk.yellow(toolName)}(${p}${p.length >= 80 ? "…" : ""})`));
}
export function renderToolResult(toolName: string, isError: boolean, durationMs: number) {
  if (isError) console.log(chalk.red(`  ✗ ${toolName} (${durationMs}ms)`));
  else console.log(chalk.dim(`  ✓ ${toolName} (${durationMs}ms)`));
}
