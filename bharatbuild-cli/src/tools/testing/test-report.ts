import chalk from "chalk";
export interface TestSummary { passed:number; failed:number; total:number; duration?:number; failedTests?:string[]; }
export function printTestReport(summary: TestSummary): void {
  const icon = summary.failed === 0 ? chalk.green("?") : chalk.red("?");
  console.log(`\n${icon} Tests: ${chalk.green(summary.passed+" passed")}, ${summary.failed > 0 ? chalk.red(summary.failed+" failed") : chalk.dim("0 failed")}, ${summary.total} total`);
  if (summary.duration) console.log(chalk.dim(`   Time: ${summary.duration.toFixed(2)}s`));
  if (summary.failedTests?.length) {
    console.log(chalk.red("\nFailed tests:"));
    summary.failedTests.forEach((t) => console.log(chalk.red(`  ? ${t}`)));
  }
  console.log();
}
