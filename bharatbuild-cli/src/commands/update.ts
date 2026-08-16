import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import readline from "readline";

export function updateCommand(): Command {
  return new Command("update")
    .description("Update BharatBuild CLI to the latest version")
    .option("-y, --non-interactive", "Skip confirmation")
    .action(async (opts) => {
      console.log(chalk.bold("\n  🔄 BharatBuild CLI Updater\n"));
      let confirm = opts.nonInteractive;
      if (!confirm) {
        const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
        confirm = await new Promise((r) => rl.question(chalk.cyan("  Update to latest version? [y/N]: "), (a) => { rl.close(); r(a.trim().toLowerCase() === "y"); }));
      }
      if (!confirm) { console.log(chalk.dim("  Update cancelled.\n")); return; }
      console.log(chalk.dim("  Updating..."));
      try {
        execSync("npm install -g @bharatbuild/cli@latest", { stdio: "inherit" });
        console.log(chalk.bold.green("\n  ✅ Updated successfully!\n"));
      } catch {
        console.log(chalk.yellow("\n  ⚠  Could not auto-update. Run manually: npm install -g @bharatbuild/cli@latest\n"));
      }
    });
}
