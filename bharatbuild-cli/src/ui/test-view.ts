import chalk from "chalk";
export function renderTestResult(passed: number, failed: number, total: number, duration: number) {
  console.log(`\n  ${failed === 0 ? chalk.bold.green("✅ All tests passed") : chalk.bold.red(`❌ ${failed} test(s) failed`)}`);
  console.log(`  ${chalk.green(passed + " passed")}, ${failed > 0 ? chalk.red(failed + " failed") : chalk.dim("0 failed")}, ${total} total, ${duration.toFixed(2)}s\n`);
}
