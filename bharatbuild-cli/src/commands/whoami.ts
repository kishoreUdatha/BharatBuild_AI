import { Command } from "commander";
import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";

export function whoamiCommand(): Command {
  return new Command("whoami")
    .description("Show current user and auth status")
    .option("-f, --format <fmt>", "Output format: plain|json", "plain")
    .action((opts) => {
      const creds = loadCredentials();
      if (!creds) {
        console.log(chalk.yellow("\n  Not logged in. Run: bharatbuild login\n"));
        if (opts.format === "json") console.log(JSON.stringify({ loggedIn: false }));
        return;
      }
      if (opts.format === "json") { console.log(JSON.stringify({ loggedIn: true, name: creds.name, email: creds.email, tier: creds.tier })); return; }
      console.log(chalk.bold("\n  👤 Current User\n"));
      console.log(`  ${chalk.bold("Name:")}    ${creds.name}`);
      console.log(`  ${chalk.bold("Email:")}   ${creds.email ?? "N/A"}`);
      console.log(`  ${chalk.bold("Plan:")}    ${chalk.cyan(creds.tier ?? "free")}`);
      console.log(`  ${chalk.bold("Token:")}   ${creds.token ? chalk.green(creds.token.slice(0, 8) + "…") : "N/A"}`);
      console.log();
    });
}
