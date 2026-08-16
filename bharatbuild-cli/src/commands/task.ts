/**
 * BharatBuild CLI — task command
 * Run a task from .bharatbuild/tasks/ or describe one inline
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { chatCommand } from "./chat.js";
import { loadConfig } from "../config/config.js";
import type { CLIConfig } from "../config/config.js";

export async function taskCommand(
  description: string | undefined,
  opts: { model?: string; file?: string },
  config: CLIConfig,
  client: BharatBuildClient
): Promise<void> {
  if (!description && !opts.file) {
    console.error(chalk.red('\n  Usage: bharatbuild task "implement user auth"\n'));
    process.exit(1);
  }
  const prompt = opts.file
    ? `Complete the task described in ${opts.file}`
    : `Complete this task: ${description}`;
  console.log(chalk.bold.cyan(`\n📋 Task: ${description ?? opts.file}\n`));
  await chatCommand(prompt, opts, config, client);
}
