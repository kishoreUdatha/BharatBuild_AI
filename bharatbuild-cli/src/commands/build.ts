/**
 * BharatBuild CLI — build command
 * Detect build system and run the build, then report errors
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { chatCommand } from "./chat.js";
import { detectBuildSystem } from "../tools/build/detect-build-system.js";
import { loadConfig } from "../config/config.js";
import type { CLIConfig } from "../config/config.js";

export async function buildCommand(opts: { fix?: boolean; model?: string }, config: CLIConfig, client: BharatBuildClient): Promise<void> {
  const bs = detectBuildSystem(process.cwd());
  console.log(chalk.bold.cyan(`\n🔨 Build — detected: ${bs.name}\n`));
  console.log(chalk.dim(`  Command: ${bs.buildCommand}\n`));

  if (opts.fix) {
    await chatCommand(
      `Run the build command (${bs.buildCommand}) and fix any errors that appear. Keep fixing until the build passes.`,
      opts, config, client
    );
  } else {
    const { executeCommand } = await import("../tools/shell/index.js");
    const result = await executeCommand({ command: bs.buildCommand });
    if (result.isError) {
      console.log(chalk.red("\n✗ Build failed:\n"));
      console.log(result.content);
      console.log(chalk.dim(`\nTip: run ${chalk.cyan("bharatbuild build --fix")} to auto-fix errors\n`));
    } else {
      console.log(chalk.green("\n✅ Build passed!\n"));
      console.log(result.content);
    }
  }
}
