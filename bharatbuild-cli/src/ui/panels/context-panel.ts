import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface ContextEntry {
  path: string;
  tokens: number;
  percentage: number;
}

export function renderContextPanel(entries: ContextEntry[], totalTokens: number): void {
  const t = getTheme();
  const w = process.stdout.columns ?? 80;
  const border = "─".repeat(w - 4);
  console.log(t.heading(`\n  ┌${border}┐`));
  console.log(t.heading(`  │ 📁 Context Breakdown${" ".repeat(w - 24)}│`));
  console.log(t.heading(`  ├${border}┤`));
  if (entries.length === 0) {
    console.log(t.dim(`  │  No files in context${" ".repeat(w - 23)}│`));
  } else {
    for (const e of entries) {
      const bar = "█".repeat(Math.round(e.percentage / 5));
      const line = `  ${e.path}  ${e.percentage.toFixed(1)}%  ${bar}`;
      console.log(t.info(line.padEnd(w - 2)));
    }
  }
  console.log(t.heading(`  ├${border}┤`));
  console.log(t.dim(`  │  Total: ${totalTokens.toLocaleString()} tokens${" ".repeat(w - 22 - totalTokens.toLocaleString().length)}│`));
  console.log(t.heading(`  └${border}┘\n`));
  console.log(t.dim("  Subcommands: /context add <file>  /context remove <file>  /context clear\n"));
}
