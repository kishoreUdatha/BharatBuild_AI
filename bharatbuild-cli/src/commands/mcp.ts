import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { mcpConfigPath, type MCPScope, type MCPServerConfig } from "../mcp/mcp-config.js";

type MCPServerDef = MCPServerConfig & { scope: MCPScope };

// Scope-specific reads/writes. The merged view used at runtime lives in
// mcp/mcp-config.ts; these operate on one file so add/remove target a scope.
function loadMCP(scope: MCPScope): MCPServerDef[] {
  try {
    const f = mcpConfigPath(scope);
    if (fs.existsSync(f)) {
      const servers = (JSON.parse(fs.readFileSync(f, "utf8")) as { servers?: MCPServerConfig[] }).servers ?? [];
      return servers.map((s) => ({ ...s, scope }));
    }
  } catch { /* malformed config - treat as empty */ }
  return [];
}

function saveMCP(scope: MCPScope, servers: MCPServerDef[]): void {
  const f = mcpConfigPath(scope);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, JSON.stringify({ servers }, null, 2));
}

export function mcpCommand(): Command {
  const cmd = new Command("mcp").description("Manage MCP servers");

  cmd.command("add").description("Add an MCP server").requiredOption("--name <name>", "Server name").requiredOption("--command <cmd>", "Launch command").option("--scope <scope>", "workspace|global", "workspace").option("--env <kv>", "key=val,key2=val2").option("--timeout <ms>", "Timeout ms").option("--force", "Overwrite existing").action((opts) => {
    const servers = loadMCP(opts.scope);
    if (servers.find((s) => s.name === opts.name) && !opts.force) { console.log(chalk.yellow(`  ⚠  Server "${opts.name}" already exists. Use --force to overwrite.`)); return; }
    const env: Record<string,string> = {};
    if (opts.env) { for (const kv of opts.env.split(",")) { const [k,v] = kv.split("="); if (k) env[k] = v ?? ""; } }
    const server: MCPServerDef = { name: opts.name, command: opts.command, scope: opts.scope, ...(Object.keys(env).length ? { env } : {}), ...(opts.timeout ? { timeout: parseInt(opts.timeout) } : {}) };
    const updated = servers.filter((s) => s.name !== opts.name); updated.push(server); saveMCP(opts.scope, updated);
    console.log(chalk.green(`  ✅ MCP server "${opts.name}" added`));
  });

  cmd.command("remove").description("Remove an MCP server").requiredOption("--name <name>", "Server name").option("--scope <scope>", "workspace|global", "workspace").action((opts) => {
    const servers = loadMCP(opts.scope).filter((s) => s.name !== opts.name);
    saveMCP(opts.scope, servers); console.log(chalk.green(`  ✅ Removed "${opts.name}"`));
  });

  cmd.command("list [scope]").description("List MCP servers").action((scope = "workspace") => {
    const servers = loadMCP(scope as "workspace"|"global");
    if (servers.length === 0) { console.log(chalk.dim(`  No MCP servers in ${scope} scope.`)); return; }
    console.log(chalk.bold(`\n  🔌 MCP Servers [${scope}]\n`));
    for (const s of servers) console.log(`  ${chalk.cyan("●")} ${chalk.bold(s.name.padEnd(20))} ${chalk.dim(s.command)}`);
    console.log();
  });

  cmd.command("import").description("Import MCP config from file").requiredOption("--file <path>", "Config file").option("--force", "Overwrite").argument("[scope]", "workspace|global", "workspace").action((scope, opts) => {
    try {
      const data = JSON.parse(fs.readFileSync(opts.file, "utf8")) as { servers?: MCPServerDef[] };
      const existing = opts.force ? [] : loadMCP(scope as "workspace"|"global");
      const merged = [...existing, ...(data.servers ?? []).filter((s) => !existing.find((e) => e.name === s.name))];
      saveMCP(scope as "workspace"|"global", merged);
      console.log(chalk.green(`  ✅ Imported ${(data.servers ?? []).length} servers`));
    } catch (err) { console.log(chalk.red(`  ✗ ${err instanceof Error ? err.message : err}`)); }
  });

  cmd.command("status").description("Get MCP server status").requiredOption("--name <name>", "Server name").action((opts) => {
    const ws = loadMCP("workspace"); const gl = loadMCP("global");
    const server = [...ws, ...gl].find((s) => s.name === opts.name);
    if (!server) { console.log(chalk.yellow(`  ⚠  Server "${opts.name}" not found`)); return; }
    console.log(chalk.bold(`\n  MCP Server: ${opts.name}\n`));
    console.log(`  Command: ${chalk.cyan(server.command)}`);
    console.log(`  Scope:   ${server.scope}`);
    if (server.env) console.log(`  Env:     ${JSON.stringify(server.env)}`);
    console.log(chalk.dim(`\n  This is the stored config. Run 'bharatbuild mcp test --name ${opts.name}' to actually connect.\n`));
  });

  // Actually launch a server and list its tools. Configuration alone proves
  // nothing - this is the command that tells you the integration works.
  cmd
    .command("test")
    .description("Connect to an MCP server and list the tools it exposes")
    .option("--name <name>", "Server name (default: all configured servers)")
    .action(async (opts: { name?: string }) => {
      const { MCPClient } = await import("../mcp/mcp-client.js");
      const { loadMCPConfig } = await import("../mcp/mcp-config.js");

      const all = loadMCPConfig().servers;
      const targets = opts.name ? all.filter((s) => s.name === opts.name) : all;

      if (targets.length === 0) {
        console.log(opts.name
          ? chalk.yellow(`\n  ⚠  Server "${opts.name}" not found in workspace or global config.\n`)
          : chalk.dim("\n  No MCP servers configured. Add one with: bharatbuild mcp add --name <n> --command <cmd>\n"));
        return;
      }

      const mcp = new MCPClient();
      console.log(chalk.bold(`\n  🔌 Testing ${targets.length} MCP server(s)\n`));

      let failures = 0;
      for (const server of targets) {
        process.stdout.write(`  ${chalk.bold(server.name.padEnd(20))} `);
        try {
          const tools = await mcp.connect(server);
          console.log(chalk.green(`✓ connected — ${tools.length} tool(s)`));
          for (const t of tools) console.log(`      ${chalk.cyan(t.name)}  ${chalk.dim((t.definition.description ?? "").slice(0, 60))}`);
        } catch (err) {
          failures++;
          console.log(chalk.red(`✗ ${err instanceof Error ? err.message : String(err)}`));
        }
      }

      await mcp.close();
      console.log();
      if (failures > 0) process.exitCode = 1;
    });

  return cmd;
}
