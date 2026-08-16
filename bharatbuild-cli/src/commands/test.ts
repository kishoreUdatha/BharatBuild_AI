/**
 * BharatBuild CLI — test command
 * Run tests and optionally fix failures
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { chatCommand } from "./chat.js";
import { detectBuildSystem } from "../tools/build/detect-build-system.js";
import type { CLIConfig } from "../config/config.js";

export async function testCommand(opts: { fix?: boolean; model?: string; filter?: string }, config: CLIConfig, client: BharatBuildClient): Promise<void> {
  const bs = detectBuildSystem(process.cwd());
  const cmd = bs.testCommand ?? `${bs.name === "npm" ? "npm test" : bs.name === "python" ? "pytest" : "mvn test"}`;
  const fullCmd = opts.filter ? `${cmd} ${opts.filter}` : cmd;

  console.log(chalk.bold.cyan(`\n🧪 Tests — running: ${fullCmd}\n`));

  if (opts.fix) {
    await chatCommand(
      `Run the tests (${fullCmd}) and fix any failing tests. Keep running until all tests pass.`,
      opts, config, client
    );
  } else {
    const { executeCommand } = await import("../tools/shell/index.js");
    const result = await executeCommand({ command: fullCmd });
    if (result.isError) {
      console.log(chalk.red("\n✗ Tests failed:\n"));
      console.log(result.content);
      console.log(chalk.dim(`\nTip: run ${chalk.cyan("bharatbuild test --fix")} to auto-fix failures\n`));
    } else {
      console.log(chalk.green("\n✅ All tests passed!\n"));
      console.log(result.content);
    }
  }
}
