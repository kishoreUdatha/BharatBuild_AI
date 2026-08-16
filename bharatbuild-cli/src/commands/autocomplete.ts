import { Command } from "commander";
import chalk from "chalk";
import { installCompletion, generateBashCompletion, generateZshCompletion, generatePowerShellCompletion } from "../infra/autocomplete.js";

export function autocompleteCommand(): Command {
  return new Command("autocomplete")
    .description("Install shell autocompletion")
    .argument("[shell]", "Shell: bash|zsh|powershell (auto-detected)")
    .option("--print", "Print script instead of installing")
    .action((shell?: string, opts?) => {
      const detected = shell ?? (process.env["SHELL"] ?? "bash").split("/").pop() ?? "bash";
      if (opts?.print) {
        if (detected.includes("zsh")) console.log(generateZshCompletion());
        else if (detected.includes("powershell") || process.platform === "win32") console.log(generatePowerShellCompletion());
        else console.log(generateBashCompletion());
        return;
      }
      console.log(chalk.bold(`\n  🔧 Installing ${detected} completion...\n`));
      const installPath = installCompletion(detected);
      console.log(`  Installed: ${chalk.cyan(installPath)}`);
      if (detected.includes("bash")) console.log(chalk.dim(`  Add to ~/.bashrc: source ${installPath}`));
      else if (detected.includes("zsh")) console.log(chalk.dim("  Add to ~/.zshrc: fpath=(~/.zsh/completions $fpath) && autoload -U compinit && compinit"));
      else console.log(chalk.dim(`  Add to PowerShell profile: . ${installPath}`));
      console.log(chalk.green("\n  ✅ Autocomplete installed!\n"));
    });
}
