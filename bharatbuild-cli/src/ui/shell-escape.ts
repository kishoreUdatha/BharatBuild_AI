import { spawn } from "child_process";
import chalk from "chalk";

export async function runShellEscape(command: string): Promise<void> {
  console.log(chalk.dim(`\n  $ ${command}`));
  const shell = process.platform === "win32" ? "cmd" : "sh";
  const args = process.platform === "win32" ? ["/c", command] : ["-c", command];
  return new Promise((resolve) => {
    const child = spawn(shell, args, { stdio: "inherit" });
    child.on("close", (code) => {
      if (code !== 0) console.log(chalk.red(`\n  Process exited with code ${code}`));
      resolve();
    });
    child.on("error", (err) => {
      console.log(chalk.red(`\n  Error: ${err.message}`));
      resolve();
    });
  });
}
