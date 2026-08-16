import { Command } from "commander";
import chalk from "chalk";
import { HooksRuntime } from "../hooks/hooks-runtime.js";
import type { HookEvent } from "../hooks/hook-config.js";

export function hookRunCommand(): Command {
  return new Command("hook:run")
    .description("Internal: run hooks for a specific event (called by git hooks)")
    .argument("<event>", "Hook event: git-commit|git-push|build-complete|test-complete")
    .option("--file <path>", "File path (for file-based events)")
    .action(async (event: string, opts) => {
      const runtime = new HooksRuntime();
      const validEvents: HookEvent[] = ["file-saved","file-created","file-deleted","git-commit","git-push","build-complete","test-complete"];
      if (!validEvents.includes(event as HookEvent)) {
        console.log(chalk.yellow(`  Unknown hook event: ${event}`));
        process.exit(1);
      }
      await runtime.runEvent(event as HookEvent, opts.file ? { filePath: opts.file } : undefined);
    });
}
