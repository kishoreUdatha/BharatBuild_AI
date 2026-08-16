import { Command } from "commander";
import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto as createModelClient } from "../models/model-router.js";
import { resolveModel } from "../config/constants.js";

export function translateCommand(): Command {
  return new Command("translate")
    .description("Translate natural language to shell commands")
    .argument("[input...]", "Natural language description")
    .option("-n, --count <n>", "Number of suggestions (max 5)", "1")
    .action(async (input: string[], opts) => {
      const query = input.join(" ");
      if (!query) { console.log(chalk.yellow("Usage: bharatbuild translate <description>")); return; }
      const creds = loadCredentials();
      const config = loadConfig();
      const count = Math.min(parseInt(opts.count ?? "1"), 5);
      const model = createModelClient(resolveModel(config.model), creds?.token);
      console.log(chalk.dim(`\n  Translating: "${query}"...\n`));
      const prompt = `Translate this natural language description to ${count} shell command(s).
Description: "${query}"
Rules: Output ONLY the shell command(s), one per line. No explanation. No markdown. Just the command.`;
      let result = "";
      for await (const chunk of model.complete({ model: resolveModel(config.model), system: "You are a shell command expert.", messages: [{ role: "user", content: prompt }], tools: [], maxTokens: 200 })) {
        if (chunk.type === "text_delta" && chunk.text) result += chunk.text;
      }
      const cmds = result.trim().split("\n").filter(Boolean).slice(0, count);
      cmds.forEach((cmd, i) => { if (count > 1) console.log(chalk.dim(`  ${i+1}.`) + " " + chalk.cyan(cmd)); else console.log("  " + chalk.cyan(cmd)); });
      console.log();
    });
}

