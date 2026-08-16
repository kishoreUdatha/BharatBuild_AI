/** BharatBuild CLI — review command */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { chatCommand } from "./chat.js";
import type { CLIConfig } from "../config/config.js";

export async function reviewCommand(target: string | undefined, opts: { model?: string; staged?: boolean }, config: CLIConfig, client: BharatBuildClient): Promise<void> {
  let prompt: string;
  if (opts.staged) prompt = "Review the staged git changes. Check for bugs, security issues, code style, and suggest improvements.";
  else if (target) prompt = `Review this file/code for bugs, security issues, and improvements: ${target}`;
  else prompt = "Review the recent git changes (git diff HEAD~1) for bugs, security issues, and improvements.";
  console.log(chalk.bold.cyan("\n?? Code Review\n"));
  await chatCommand(prompt, opts, config, client);
}
