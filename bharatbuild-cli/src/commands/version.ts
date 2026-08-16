import { Command } from "commander";
import chalk from "chalk";
import pkg from "../../package.json" with { type: "json" };

const CHANGELOG: Record<string, string> = {
  "1.0.0": `## v1.0.0
- Initial release
- Multi-model support: Anthropic, OpenAI, Gemini, Ollama, Bedrock
- Full TUI with themes, panels, markdown rendering
- Spec-driven workflow: requirements, design docs, steering files
- Hooks system: file watcher, git hooks
- MCP support, permissions, quality gates
- 5 user modes: Student, Developer, Founder, College, API Partner`,
};

export function versionCommand(): Command {
  return new Command("version")
    .description("Show version and changelog")
    .option("--changelog [version]", "Show changelog")
    .action((opts) => {
      console.log(chalk.bold(`\n  BharatBuild CLI v${pkg.version}\n`));
      if (opts.changelog) {
        const ver = typeof opts.changelog === "string" ? opts.changelog : pkg.version;
        if (ver === "all") {
          for (const [v, notes] of Object.entries(CHANGELOG)) console.log(notes + "\n");
        } else {
          console.log(CHANGELOG[ver] ?? `No changelog for v${ver}`);
        }
        console.log();
      }
    });
}
