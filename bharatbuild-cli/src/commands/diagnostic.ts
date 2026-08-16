import { Command } from "commander";
import chalk from "chalk";
import os from "os";
import { execSync } from "child_process";
import { logger } from "../infra/logger.js";
import pkg from "../../package.json" with { type: "json" };

export function diagnosticCommand(): Command {
  return new Command("diagnostic")
    .description("Run diagnostic tests and generate system report")
    .option("-f, --format <fmt>", "Output format: plain|json", "plain")
    .option("--force", "Generate limited diagnostics without running app")
    .action((opts) => {
      const info = {
        version: pkg.version,
        platform: process.platform,
        arch: process.arch,
        nodeVersion: process.version,
        cwd: process.cwd(),
        logPath: logger.getLogPath(),
        memory: `${(os.totalmem() / 1024 / 1024 / 1024).toFixed(2)} GB`,
        freeMemory: `${(os.freemem() / 1024 / 1024 / 1024).toFixed(2)} GB`,
        cpus: os.cpus().length,
        shell: process.env["SHELL"] ?? process.env["COMSPEC"] ?? "unknown",
        term: process.env["TERM"] ?? "unknown",
        bharatbuildHome: process.env["BHARATBUILD_HOME"] ?? "~/.bharatbuild",
        proxyHttp: process.env["HTTP_PROXY"] ?? "not set",
        proxyHttps: process.env["HTTPS_PROXY"] ?? "not set",
      };
      if (opts.format === "json") { console.log(JSON.stringify(info, null, 2)); return; }
      console.log(chalk.bold("\n  🔍 BharatBuild Diagnostic Report\n"));
      for (const [k, v] of Object.entries(info)) {
        console.log(`  ${chalk.cyan(k.padEnd(22))} ${chalk.dim(String(v))}`);
      }
      console.log();
    });
}
