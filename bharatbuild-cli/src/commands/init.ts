/**
 * BharatBuild CLI — init command
 * Initialises a BharatBuild project in the current directory
 */
import fs from "fs";
import path from "path";
import chalk from "chalk";
import { prompt } from "../ui/spinner.js";
import { saveConfig } from "../config/config.js";
import { DEFAULT_MODEL } from "../config/constants.js";

export interface ProjectConfig {
  name: string;
  description: string;
  mode: string;
  model: string;
  apiUrl: string;
  createdAt: string;
}

const CONFIG_FILE = ".bharatbuild.json";
const RULES_FILE = ".bharatbuild/rules.md";

export async function initCommand(opts: { yes?: boolean; mode?: string }): Promise<void> {
  console.log(chalk.bold.cyan("\n🚀 Initialising BharatBuild project\n"));

  if (!opts.yes && fs.existsSync(CONFIG_FILE)) {
    const ans = await prompt("  .bharatbuild.json already exists. Overwrite? [y/N]: ");
    if (ans.toLowerCase() !== "y") {
      console.log(chalk.dim("  Cancelled.\n"));
      return;
    }
  }

  const dirName = path.basename(process.cwd());
  const name = opts.yes ? dirName : (await prompt(`  Project name [${dirName}]: `)) || dirName;
  const description = opts.yes ? "" : await prompt("  Description (optional): ");
  const mode = opts.mode ?? (opts.yes ? "developer" : (await prompt("  Mode (student/developer/founder/college) [developer]: ")) || "developer");

  const config: ProjectConfig = {
    name,
    description,
    mode,
    model: DEFAULT_MODEL,
    apiUrl: "http://localhost:8000",
    createdAt: new Date().toISOString(),
  };

  // Write .bharatbuild.json
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
  console.log(chalk.green(`  ✓ Created ${CONFIG_FILE}`));

  // Write rules file
  fs.mkdirSync(".bharatbuild", { recursive: true });
  if (!fs.existsSync(RULES_FILE)) {
    fs.writeFileSync(RULES_FILE, `# BharatBuild Project Rules\n\n## Project: ${name}\n\n## Guidelines\n- Write clean, well-documented code\n- Follow existing project conventions\n- Add tests for new features\n`);
    console.log(chalk.green(`  ✓ Created ${RULES_FILE}`));
  }

  // Add to .gitignore
  const gitignore = ".gitignore";
  const entry = ".bharatbuild/sessions/\n.bharatbuild/checkpoints/\n";
  if (fs.existsSync(gitignore)) {
    const existing = fs.readFileSync(gitignore, "utf8");
    if (!existing.includes(".bharatbuild/sessions")) {
      fs.appendFileSync(gitignore, `\n# BharatBuild\n${entry}`);
      console.log(chalk.green(`  ✓ Updated .gitignore`));
    }
  }

  console.log(chalk.bold.green(`\n✅ Project "${name}" initialised!\n`));
  console.log(chalk.dim(`  Run ${chalk.cyan("bharatbuild chat")} to start building.\n`));
}
