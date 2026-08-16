/** BharatBuild CLI — logout command */
import chalk from "chalk";
import { clearCredentials } from "../auth/credentials.js";

export function logoutCommand(): void {
  clearCredentials();
  console.log(chalk.green("\n✓ Logged out successfully.\n"));
}
