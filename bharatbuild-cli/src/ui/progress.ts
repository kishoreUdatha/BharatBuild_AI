import chalk from "chalk";
export class ProgressBar {
  private cur = 0;
  constructor(private total: number, private label = "") {}
  update(n: number, label?: string) {
    this.cur = n; if (label) this.label = label;
    const pct = Math.round((n / this.total) * 100);
    const f = Math.round((n / this.total) * 30);
    process.stdout.write(`\r  ${chalk.green("█".repeat(f))}${chalk.dim("░".repeat(30 - f))} ${pct}% ${chalk.dim(this.label)}   `);
    if (n >= this.total) process.stdout.write("\n");
  }
  done(msg?: string) { this.update(this.total, msg ?? "done"); }
}
