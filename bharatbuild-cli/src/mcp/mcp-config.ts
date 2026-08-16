/**
 * BharatBuild CLI - MCP configuration
 *
 * Servers are declared in mcp.json at two scopes:
 *   workspace : <cwd>/.bharatbuild/mcp.json   (checked into the project)
 *   global    : ~/.bharatbuild/mcp.json       (per user)
 *
 * Workspace entries win on a name collision, so a project can pin a server
 * the user also has configured globally.
 */
import fs from "fs";
import os from "os";
import path from "path";

export interface MCPServerConfig {
  name: string;
  /** Full launch command, e.g. "npx -y @modelcontextprotocol/server-filesystem /tmp". */
  command: string;
  /** Parsed from `command` when absent. */
  args?: string[];
  env?: Record<string, string>;
  /** Connection timeout in ms. */
  timeout?: number;
  scope?: "workspace" | "global";
}

export interface MCPConfig { servers: MCPServerConfig[]; }

export type MCPScope = "workspace" | "global";

export function mcpConfigPath(scope: MCPScope, projectDir: string = process.cwd()): string {
  if (scope === "workspace") return path.join(projectDir, ".bharatbuild", "mcp.json");
  return path.join(
    process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"),
    "mcp.json",
  );
}

function readScope(scope: MCPScope, projectDir: string): MCPServerConfig[] {
  try {
    const f = mcpConfigPath(scope, projectDir);
    if (!fs.existsSync(f)) return [];
    const parsed = JSON.parse(fs.readFileSync(f, "utf8")) as MCPConfig;
    return (parsed.servers ?? []).map((s) => ({ ...s, scope }));
  } catch {
    return []; // a malformed mcp.json must not stop the CLI from starting
  }
}

/** Merged view of both scopes, workspace taking precedence. */
export function loadMCPConfig(projectDir: string = process.cwd()): MCPConfig {
  const workspace = readScope("workspace", projectDir);
  const global = readScope("global", projectDir);
  const names = new Set(workspace.map((s) => s.name));
  return { servers: [...workspace, ...global.filter((s) => !names.has(s.name))] };
}

export function saveMCPConfig(
  config: MCPConfig,
  scope: MCPScope = "global",
  projectDir: string = process.cwd(),
): void {
  const f = mcpConfigPath(scope, projectDir);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  // `scope` is derived from location; don't persist it into the file.
  const servers = config.servers.map(({ scope: _drop, ...rest }) => rest);
  fs.writeFileSync(f, JSON.stringify({ servers }, null, 2));
}

/**
 * Split a launch command into executable + args.
 *
 * Handles quoted segments so a path containing spaces survives - on Windows
 * that is the common case, not the exception.
 */
export function resolveCommand(server: MCPServerConfig): { command: string; args: string[] } {
  if (server.args) return { command: server.command, args: server.args };

  const parts = server.command.match(/"[^"]*"|'[^']*'|\S+/g) ?? [];
  const unquote = (s: string) =>
    (s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))
      ? s.slice(1, -1)
      : s;

  const [cmd = "", ...rest] = parts.map(unquote);
  return { command: cmd, args: rest };
}
