/**
 * BharatBuild CLI — fix command
 * Fix errors: build errors, test failures, or a described issue
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { chatCommand } from "./chat.js";
import type { CLIConfig } from "../config/config.js";

export async function fixCommand(description: string | undefined, opts: { model?: string; build?: boolean; test?: boolean }, config: CLIConfig, client: BharatBuildClient): Promise<void> {
  let prompt: string;
  if (opts.build) {
    prompt = "Run the build. Identify all errors and fix them until the build passes with 0 errors.";
  } else if (opts.test) {
    prompt = "Run the tests. Identify all failing tests and fix them until all tests pass.";
  } else if (description) {
    prompt = `Fix the following issue: ${description}`;
  } else {
    prompt = "Identify any build errors or test failures and fix them.";
  }
  console.log(chalk.bold.cyan("\n🔧 Fix mode\n"));
  await chatCommand(prompt, opts, config, client);
}
