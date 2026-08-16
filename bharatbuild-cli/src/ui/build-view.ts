import chalk from "chalk";
export function renderBuildStart(cmd: string) { console.log(chalk.bold(`\n🔨 Running: ${chalk.cyan(cmd)}\n`)); }
export function renderBuildResult(passed: boolean, errors: string[]) {
  if (passed) console.log(chalk.bold.green("\n✅ Build passed!\n"));
  else {
    console.log(chalk.bold.red(`\n❌ Build failed — ${errors.length} error(s)\n`));
    errors.slice(0, 5).forEach((e) => console.log(chalk.red(`  • ${e}`)));
    console.log();
  }
}
