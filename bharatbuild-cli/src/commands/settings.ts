import { Command } from "commander";
import chalk from "chalk";
import { loadConfig, saveConfig } from "../config/config.js";
import { openEditor } from "../ui/editor.js";

export function settingsCommand(): Command {
  const cmd = new Command("settings").description("Manage BharatBuild CLI settings");

  cmd.command("list").option("--all", "Show all available settings").option("-f, --format <fmt>", "Output format", "plain").action((opts) => {
    const config = loadConfig();
    if (opts.format === "json") { console.log(JSON.stringify(config, null, 2)); return; }
    console.log(chalk.bold("\n  ⚙  Settings\n"));
    for (const [k, v] of Object.entries(config)) {
      console.log(`  ${chalk.cyan(k.padEnd(25))} ${chalk.dim(JSON.stringify(v))}`);
    }
    console.log();
  });

  cmd.command("open").description("Open settings in editor").action(async () => {
    const { default: p } = await import("path");
    const { default: os } = await import("os");
    const f = p.join(process.env["BHARATBUILD_HOME"] ?? p.join(os.homedir(), ".bharatbuild"), "settings.json");
    await openEditor(JSON.stringify(loadConfig(), null, 2));
    console.log(chalk.green("\n  ✅ Settings saved\n"));
  });

  // Get or set a key
  cmd.argument("[key]", "Setting key").argument("[value]", "Setting value")
    .option("-d, --delete", "Delete a setting")
    .option("-f, --format <fmt>", "Output format", "plain")
    .action((key?: string, value?: string, opts?) => {
      if (!key) { cmd.help(); return; }
      const config = loadConfig();
      const cfg = config as unknown as Record<string,unknown>;
      if (opts?.delete) { delete cfg[key]; saveConfig(config); console.log(chalk.green(`  ✓ Deleted: ${key}`)); return; }
      if (value === undefined) {
        const v = cfg[key];
        if (opts?.format === "json") console.log(JSON.stringify({ [key]: v }));
        else console.log(`  ${key}: ${chalk.cyan(JSON.stringify(v))}`);
        return;
      }
      let parsed: unknown = value;
      try { parsed = JSON.parse(value); } catch {}
      cfg[key] = parsed;
      saveConfig(config);
      console.log(chalk.green(`  ✓ Set ${key} = ${JSON.stringify(parsed)}`));
    });

  return cmd;
}
