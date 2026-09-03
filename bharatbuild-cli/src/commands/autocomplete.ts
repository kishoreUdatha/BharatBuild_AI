import { Command } from "commander";
import chalk from "chalk";
import {
  installCompletion, completionFor, resolveShell, SUPPORTED_SHELLS,
} from "../infra/autocomplete.js";

export function autocompleteCommand(): Command {
  return new Command("autocomplete")
    .description("Install shell autocompletion")
    .argument("[shell]", `Shell: ${SUPPORTED_SHELLS.join("|")} (auto-detected)`)
    .option("--print", "Print script instead of installing")
    .action((shell?: string, opts?: { print?: boolean }) => {
      // The shell now decides the script. This used to fall through to
      // PowerShell for anything non-zsh on Windows, so `autocomplete bash`
      // wrote a .ps1 and told the user to source it from ~/.bashrc.
      let target;
      try {
        target = resolveShell(shell);
      } catch (err) {
        console.error(chalk.red(`\n  ${err instanceof Error ? err.message : String(err)}\n`));
        process.exitCode = 1;
        return;
      }

      const { hint } = completionFor(target);

      if (opts?.print) {
        // Only the script goes to stdout — this output is meant to be piped
        // into a file or eval'd, so a banner would end up inside it.
        console.log(completionFor(target).script);
        return;
      }

      console.log(chalk.bold(`\n  🔧 Installing ${target} completion...\n`));
      const installPath = installCompletion(target);
      console.log(`  Installed: ${chalk.cyan(installPath)}`);
      console.log(chalk.dim(`  ${hint.replace("<path>", installPath)}`));
      console.log(chalk.green("\n  ✅ Autocomplete installed!\n"));
    });
}
