import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";

export function issueCommand(): Command {
  return new Command("issue")
    .description("Create a GitHub issue or feedback report")
    .argument("[description...]", "Issue description")
    .option("-f, --force", "Force issue creation")
    .action((description: string[]) => {
      const desc = description.join(" ");
      const title = encodeURIComponent(desc || "Bug report / Feature request");
      const url = `https://github.com/bharatbuild-ai/bharatbuild-cli/issues/new?title=${title}&template=bug_report.yml`;
      console.log(chalk.bold("\n  🐛 Opening GitHub issue...\n"));
      console.log(chalk.dim(`  URL: ${url}\n`));
      try {
        const open = process.platform === "win32" ? "start" : process.platform === "darwin" ? "open" : "xdg-open";
        execSync(`${open} "${url}"`, { stdio: "ignore" });
      } catch {
        console.log(chalk.yellow(`  Could not open browser. Visit: ${url}\n`));
      }
    });
}
