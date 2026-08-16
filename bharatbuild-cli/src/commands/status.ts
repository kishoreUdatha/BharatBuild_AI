/** BharatBuild CLI — status command */
import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { BharatBuildClient } from "../api/client.js";
import { Spinner } from "../ui/spinner.js";

export async function statusCommand(client: BharatBuildClient): Promise<void> {
  const creds = loadCredentials();
  const config = loadConfig();
  console.log(chalk.bold("\n?? BharatBuild Status\n"));
  console.log(`  Auth:      ${creds ? chalk.green(`? ${creds.name} (${creds.tier})`) : chalk.red("? Not logged in")}`);
  console.log(`  API:       ${chalk.dim(config.apiBaseUrl)}`);
  console.log(`  Model:     ${chalk.cyan(config.model)}`);
  console.log(`  Mode:      ${chalk.cyan(config.permissionMode)}`);
  const spinner = new Spinner();
  spinner.start("Checking API…");
  try {
    await client.get("/api/v1/health");
    spinner.succeed("API reachable");
  } catch {
    spinner.fail("API unreachable");
  }
  console.log();
}
