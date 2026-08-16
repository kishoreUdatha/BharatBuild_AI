/**
 * BharatBuild CLI - MCP server manager
 *
 * Spawns MCP servers over stdio and holds the connected clients.
 *
 * This previously logged "requires @modelcontextprotocol/sdk", recorded the
 * server as not running, and returned success - so `mcp add` appeared to work
 * while no server ever started. The SDK is now a real dependency.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { CLI_NAME, CLI_VERSION } from "../config/constants.js";
import { resolveCommand, type MCPServerConfig } from "./mcp-config.js";

const DEFAULT_TIMEOUT_MS = 30_000;

export interface ConnectedServer {
  name: string;
  client: Client;
  transport: StdioClientTransport;
}

export class MCPServerManager {
  private servers = new Map<string, ConnectedServer>();
  private failures = new Map<string, string>();

  /**
   * Start a server and complete the MCP handshake.
   *
   * Throws on failure - callers that want best-effort startup across several
   * servers should use `startAll`, which records errors instead.
   */
  async start(server: MCPServerConfig): Promise<ConnectedServer> {
    if (this.servers.has(server.name)) return this.servers.get(server.name)!;

    const { command, args } = resolveCommand(server);
    if (!command) throw new Error(`MCP server "${server.name}" has an empty command`);

    const transport = new StdioClientTransport({
      command,
      args,
      // Inherit the parent env so servers find node/npx, then layer overrides.
      env: { ...(process.env as Record<string, string>), ...(server.env ?? {}) },
      stderr: "pipe",
    });

    const client = new Client(
      { name: CLI_NAME, version: CLI_VERSION },
      { capabilities: {} },
    );

    // A server that dies during startup closes the pipe, and the SDK surfaces
    // only "Connection closed". The real reason is almost always on stderr, so
    // keep a tail of it to attach to the error.
    let stderrTail = "";
    transport.stderr?.on("data", (chunk: Buffer) => {
      stderrTail = (stderrTail + chunk.toString()).slice(-2000);
    });

    const timeoutMs = server.timeout ?? DEFAULT_TIMEOUT_MS;
    let timer: NodeJS.Timeout | undefined;
    try {
      await Promise.race([
        client.connect(transport),
        new Promise<never>((_, reject) => {
          timer = setTimeout(
            () => reject(new Error(`timed out after ${timeoutMs}ms`)),
            timeoutMs,
          );
        }),
      ]);
    } catch (err) {
      // Leaving the child process alive on a failed handshake leaks it for the
      // lifetime of the CLI.
      await transport.close().catch(() => {});
      const reason = err instanceof Error ? err.message : String(err);
      const detail = stderrTail.trim()
        ? `${reason}\n      server stderr: ${stderrTail.trim().split("\n").slice(-4).join("\n      ")}`
        : reason;
      this.failures.set(server.name, detail);
      throw new Error(`MCP server "${server.name}" failed to start: ${detail}`);
    } finally {
      if (timer) clearTimeout(timer);
    }

    const connected: ConnectedServer = { name: server.name, client, transport };
    this.servers.set(server.name, connected);
    this.failures.delete(server.name);
    return connected;
  }

  /** Start every server, collecting rather than throwing on failure. */
  async startAll(servers: MCPServerConfig[]): Promise<{ started: string[]; failed: Array<{ name: string; error: string }> }> {
    const started: string[] = [];
    const failed: Array<{ name: string; error: string }> = [];

    const results = await Promise.allSettled(servers.map((s) => this.start(s)));
    for (const [i, r] of results.entries()) {
      const name = servers[i]!.name;
      if (r.status === "fulfilled") started.push(name);
      else failed.push({ name, error: r.reason instanceof Error ? r.reason.message : String(r.reason) });
    }
    return { started, failed };
  }

  get(name: string): ConnectedServer | undefined {
    return this.servers.get(name);
  }

  async stop(name: string): Promise<void> {
    const s = this.servers.get(name);
    if (!s) return;
    this.servers.delete(name);
    await s.client.close().catch(() => {});
    await s.transport.close().catch(() => {});
  }

  async stopAll(): Promise<void> {
    await Promise.all([...this.servers.keys()].map((n) => this.stop(n)));
  }

  isRunning(name: string): boolean {
    return this.servers.has(name);
  }

  listRunning(): string[] {
    return [...this.servers.keys()];
  }

  lastError(name: string): string | undefined {
    return this.failures.get(name);
  }
}
