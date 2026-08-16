/**
 * BharatBuild CLI — Interactive Login/Register helpers
 */

import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { login, register, clearCredentials } from "../api/auth.js";
import { Spinner, promptPassword } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

function ask(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

export async function interactiveLogin(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  console.log(chalk.bold("\n🔐 Login to BharatBuild\n"));
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const email = await ask(rl, "  Email: ");
  rl.close();
  const password = await promptPassword("  Password: ");

  const spinner = new Spinner();
  spinner.start("Logging in…");
  try {
    const creds = await login(client, email, password);
    spinner.succeed(`Logged in as ${chalk.green(creds.name)} (${creds.tier})`);
    console.log();
  } catch (err) {
    spinner.fail("Login failed");
    if (err instanceof APIError) {
      console.error(chalk.red(`  ${err.detail}\n`));
    } else {
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
    }
  }
}

export async function interactiveRegister(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  console.log(chalk.bold("\n📝 Create BharatBuild Account\n"));
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const name = await ask(rl, "  Full name: ");
  const email = await ask(rl, "  Email: ");
  rl.close();
  const password = await promptPassword("  Password (min 8 chars): ");

  const spinner = new Spinner();
  spinner.start("Creating account…");
  try {
    const creds = await register(client, name, email, password);
    spinner.succeed(`Account created! Welcome, ${chalk.green(creds.name)}`);
    console.log();
  } catch (err) {
    spinner.fail("Registration failed");
    if (err instanceof APIError) {
      console.error(chalk.red(`  ${err.detail}\n`));
    } else {
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
    }
  }
}
