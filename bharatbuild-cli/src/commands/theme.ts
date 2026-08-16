import { Command } from "commander";
import chalk from "chalk";
import { setTheme, type ThemeName } from "../ui/theme.js";
import { loadConfig, saveConfig } from "../config/config.js";

const THEMES: ThemeName[] = ["dark", "light", "safe"];

export function themeCommand(): Command {
  const cmd = new Command("theme")
    .description("Get or set the visual theme (dark|light|safe)")
    .argument("[theme]", "Theme name")
    .option("--list", "List all available themes")
    .action((theme?: string, opts?: { list?: boolean }) => {
      if (opts?.list || !theme) {
        const config = loadConfig();
        const current = (config as any).theme ?? "dark";
        console.log(chalk.bold("\n  🎨 Available Themes\n"));
        for (const t of THEMES) {
          const active = t === current ? chalk.green(" ✓ active") : "";
          console.log(`  ${chalk.cyan(t.padEnd(10))}${active}`);
        }
        console.log(chalk.dim("\n  Usage: bharatbuild theme <dark|light|safe>\n"));
        return;
      }
      if (!THEMES.includes(theme as ThemeName)) {
        console.log(chalk.red(`  ✗ Unknown theme: ${theme}. Choose: ${THEMES.join(", ")}\n`));
        process.exit(1);
      }
      setTheme(theme as ThemeName);
      saveConfig({ ...(loadConfig() as any), theme });
      console.log(chalk.green(`\n  ✓ Theme set to: ${chalk.bold(theme)}\n`));
    });
  return cmd;
}
