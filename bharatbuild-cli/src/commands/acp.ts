import { Command } from "commander";
import chalk from "chalk";
import { ACPServer } from "../acp/acp-server.js";
import { ACPClient } from "../acp/acp-client.js";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto as createModelClient } from "../models/model-router.js";
import { resolveModel } from "../config/constants.js";

export function acpCommand(): Command {
  const cmd = new Command("acp").description("Agent Communication Protocol — server and client");

  cmd.command("serve").description("Start ACP server").option("--port <port>", "Port", "3141").option("--host <host>", "Host", "127.0.0.1").action(async (opts) => {
    const creds = loadCredentials();
    const config = loadConfig();
    const model = createModelClient(resolveModel(config.model), creds?.token);
    console.log(chalk.bold(`\n  🔌 ACP Server starting on http://${opts.host}:${opts.port}\n`));
    const server = new ACPServer({
      port: parseInt(opts.port as string),
      host: opts.host as string,
      onTask: async (task) => {
        let result = "";
        for await (const chunk of model.complete({ model: resolveModel(config.model), system: "You are BharatBuild CLI agent.", messages: [{ role: "user", content: task.description }], tools: [], maxTokens: 2000 })) {
          if (chunk.type === "text_delta" && chunk.text) result += chunk.text;
        }
        return result;
      },
    });
    await server.listen(parseInt(opts.port as string), opts.host as string);
    console.log(chalk.dim("  Press Ctrl+C to stop.\n"));
    await new Promise<void>((resolve) => process.on("SIGINT", async () => { await server.close(); resolve(); }));
  });

  cmd.command("connect <url>").description("Connect to ACP server and show capabilities").action(async (url: string) => {
    const client = new ACPClient(url);
    try {
      const session = await client.initialize();
      console.log(chalk.green(`\n  ✅ Connected — session: ${session.id}\n`));
      const caps = await client.getCapabilities() as Record<string, unknown>;
      for (const [k, v] of Object.entries(caps)) console.log(`  ${chalk.cyan(k)}: ${JSON.stringify(v)}`);
      console.log();
    } catch (err) { console.log(chalk.red(`  ✗ ${err instanceof Error ? err.message : err}\n`)); }
  });

  cmd.command("task <url> <description>").description("Send a task to ACP server").action(async (url: string, description: string) => {
    const client = new ACPClient(url);
    await client.initialize();
    console.log(chalk.dim("\n  Sending task..."));
    const task = await client.createTask("CLI Task", description);
    console.log(chalk.green(`\n  ✅ Task ${task.status}`));
    if (task.result) console.log("\n" + task.result + "\n");
  });

  return cmd;
}

