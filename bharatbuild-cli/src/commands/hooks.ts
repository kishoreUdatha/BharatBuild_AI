import { Command } from "commander";
import chalk from "chalk";
import { loadHooksConfig, addHook, removeHook, type HookEvent } from "../hooks/hook-config.js";
import { installGitHooks, uninstallGitHooks } from "../hooks/git-hooks.js";

export function hooksCommand(): Command {
  const cmd = new Command("hooks").description("Manage automation hooks");

  cmd.command("list").description("List all hooks").action(() => {
    const config = loadHooksConfig();
    console.log(chalk.bold("\n  🪝 Hooks\n"));
    if (config.hooks.length === 0) {
      console.log(chalk.dim("  No hooks configured.\n"));
      console.log(chalk.dim("  Add a hook:"));
      console.log(chalk.cyan("    bharatbuild hooks add <name> <event>"));
      console.log(chalk.dim("\n  Available events: file-saved, file-created, file-deleted, git-commit, git-push, build-complete, test-complete"));
      console.log(chalk.dim("\n  Example:"));
      console.log(chalk.cyan("    bharatbuild hooks add \"auto-fix\" file-saved --pattern \"**/*.ts\" --agent coder"));
      console.log(chalk.dim("\n  Install git hooks:"));
      console.log(chalk.cyan("    bharatbuild hooks install-git\n"));
      return;
    }
    for (const h of config.hooks) {
      const status = h.enabled ? chalk.green("●") : chalk.dim("○");
      const id = chalk.dim(`[${h.id.slice(0, 12)}]`);
      console.log(`  ${status} ${chalk.bold(h.name.padEnd(20))} ${chalk.cyan(h.event.padEnd(20))} ${h.pattern ? chalk.dim(h.pattern) : ""} ${id}`);
    }
    console.log(chalk.dim(`\n  ${config.hooks.length} hook(s) configured.\n`));
  });

  cmd.command("add <name> <event>").description("Add a hook").option("-p, --pattern <glob>", "File glob pattern").option("-a, --agent <agent>", "Agent to trigger").option("--prompt <text>", "Prompt template").action((name: string, event: string, opts) => {
    addHook({ id: `hook-${Date.now()}`, name, event: event as HookEvent, pattern: opts.pattern, agent: opts.agent, prompt: opts.prompt, enabled: true });
    console.log(chalk.green(`✅ Hook "${name}" added for event "${event}"`));
  });

  cmd.command("remove <id>").description("Remove a hook by ID").action((id: string) => {
    removeHook(id);
    console.log(chalk.green(`✅ Hook "${id}" removed`));
  });

  cmd.command("install-git").description("Install BharatBuild git hooks").action(() => {
    installGitHooks();
    console.log(chalk.green("✅ Git hooks installed"));
  });

  cmd.command("uninstall-git").description("Uninstall BharatBuild git hooks").action(() => {
    uninstallGitHooks();
    console.log(chalk.green("✅ Git hooks uninstalled"));
  });

  return cmd;
}
