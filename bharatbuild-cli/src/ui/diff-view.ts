import chalk from "chalk";
export function renderDiff(diff: string) {
  for (const l of diff.split("\n")) {
    if (l.startsWith("+++") || l.startsWith("---")) console.log(chalk.bold(l));
    else if (l.startsWith("@@")) console.log(chalk.cyan(l));
    else if (l.startsWith("+")) console.log(chalk.green(l));
    else if (l.startsWith("-")) console.log(chalk.red(l));
    else console.log(chalk.dim(l));
  }
}
