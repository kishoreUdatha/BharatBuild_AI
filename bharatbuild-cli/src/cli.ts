/**
 * BharatBuild CLI — Bootstrap
 * Wires all commands into the Commander program.
 */
import { Command } from "commander";
import chalk from "chalk";
import { loadConfig } from "./config/config.js";
import { loadCredentials } from "./auth/credentials.js";
import { BharatBuildClient } from "./api/client.js";

export function createCLI(): Command {
  const program = new Command();
  program
    .name("bharatbuild")
    .description("BharatBuild AI — AI-powered platform for Indian developers, students & founders")
    .version("1.0.0")
    .option("--api-url <url>", "Override API base URL")
    .option("--mode <mode>", "Platform mode (student|developer|founder|college|api-partner)")
    .option("--model <model>", "AI model to use")
    .option("-v, --verbose", "Verbose output");
  return program;
}

export function makeClient(apiUrl?: string): BharatBuildClient {
  const config = loadConfig();
  const creds = loadCredentials();
  return new BharatBuildClient({ apiBaseUrl: apiUrl ?? config.apiBaseUrl, authToken: creds?.token });
}

export function requireAuth(): void {
  if (!loadCredentials()) {
    console.error(chalk.red("\n✗ Not logged in. Run: bharatbuild login\n"));
    process.exit(1);
  }
}
