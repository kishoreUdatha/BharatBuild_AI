/**
 * BharatBuild CLI - MCP client
 *
 * Starts the configured MCP servers, discovers their tools, and dispatches
 * calls to the owning server.
 *
 * `callTool` previously returned the string `MCP tool "x" called` without
 * contacting anything, so a failed integration was indistinguishable from a
 * working one. It now performs a real call and surfaces errors.
 */
import { loadMCPConfig, type MCPServerConfig } from "./mcp-config.js";
import { MCPServerManager } from "./server-manager.js";
import { MCPToolRegistry, namespacedToolName, type MCPToolEntry } from "./tool-registry.js";
import type { ToolDefinition } from "../tools/filesystem/index.js";

export interface MCPToolResult { content: string; isError: boolean; }

export interface MCPInitResult {
  started: string[];
  failed: Array<{ name: string; error: string }>;
  toolCount: number;
}

/** Shape of a tool as returned by the MCP tools/list response. */
interface RemoteTool {
  name: string;
  description?: string;
  inputSchema?: { type?: string; properties?: Record<string, unknown>; required?: string[] };
}

/** Flatten an MCP content array into text the model can read. */
function renderContent(content: unknown): string {
  if (!Array.isArray(content)) return typeof content === "string" ? content : JSON.stringify(content ?? "");
  return content
    .map((part) => {
      const p = part as Record<string, unknown>;
      if (p["type"] === "text") return String(p["text"] ?? "");
      if (p["type"] === "resource") {
        const r = p["resource"] as Record<string, unknown> | undefined;
        return String(r?.["text"] ?? r?.["uri"] ?? "[resource]");
      }
      return `[${String(p["type"] ?? "content")}]`;
    })
    .filter(Boolean)
    .join("\n");
}

export class MCPClient {
  readonly serverManager = new MCPServerManager();
  readonly toolRegistry = new MCPToolRegistry();
  private initialized = false;

  /** Start configured servers and register their tools. Never throws. */
  async initialize(projectDir: string = process.cwd()): Promise<MCPInitResult> {
    const config = loadMCPConfig(projectDir);
    if (config.servers.length === 0) {
      this.initialized = true;
      return { started: [], failed: [], toolCount: 0 };
    }

    const { started, failed } = await this.serverManager.startAll(config.servers);
    for (const name of started) await this.loadServerTools(name);

    this.initialized = true;
    return { started, failed, toolCount: this.toolRegistry.size };
  }

  /** Connect one server without touching the others. */
  async connect(server: MCPServerConfig): Promise<MCPToolEntry[]> {
    await this.serverManager.start(server);
    return this.loadServerTools(server.name);
  }

  private async loadServerTools(serverName: string): Promise<MCPToolEntry[]> {
    const connected = this.serverManager.get(serverName);
    if (!connected) return [];

    let remote: RemoteTool[] = [];
    try {
      const res = await connected.client.listTools();
      remote = (res.tools ?? []) as RemoteTool[];
    } catch {
      // A server that connects but cannot list tools contributes nothing;
      // leaving the others working is better than failing the whole session.
      return [];
    }

    const entries: MCPToolEntry[] = remote.map((t) => {
      const definition: ToolDefinition = {
        name: namespacedToolName(serverName, t.name),
        description: t.description ?? `MCP tool "${t.name}" from server "${serverName}"`,
        input_schema: {
          type: "object",
          properties: t.inputSchema?.properties ?? {},
          required: t.inputSchema?.required ?? [],
        },
      };
      return { name: definition.name, originalName: t.name, serverName, definition };
    });

    this.toolRegistry.registerServer(serverName, entries);
    return entries;
  }

  /** Definitions to merge into the agent's tool list. */
  getToolDefinitions(): ToolDefinition[] {
    return this.toolRegistry.getDefinitions();
  }

  isInitialized(): boolean { return this.initialized; }

  /** True when `name` is an MCP tool this client can dispatch. */
  handles(name: string): boolean {
    return this.toolRegistry.get(name) !== undefined;
  }

  async callTool(name: string, input: Record<string, unknown>): Promise<MCPToolResult> {
    const entry = this.toolRegistry.get(name);
    if (!entry) {
      return { content: `MCP tool "${name}" not found. Known: ${this.toolRegistry.getAll().map((e) => e.name).join(", ") || "none"}`, isError: true };
    }

    const connected = this.serverManager.get(entry.serverName);
    if (!connected) {
      const why = this.serverManager.lastError(entry.serverName) ?? "not running";
      return { content: `MCP server "${entry.serverName}" is unavailable: ${why}`, isError: true };
    }

    try {
      const res = await connected.client.callTool({ name: entry.originalName, arguments: input });
      const text = renderContent((res as Record<string, unknown>)["content"]);
      // MCP reports tool-level failure in the payload, not by throwing.
      const isError = Boolean((res as Record<string, unknown>)["isError"]);
      return { content: text || (isError ? "MCP tool reported an error with no detail" : ""), isError };
    } catch (err) {
      return { content: `MCP call to "${name}" failed: ${err instanceof Error ? err.message : String(err)}`, isError: true };
    }
  }

  async close(): Promise<void> {
    await this.serverManager.stopAll();
    this.initialized = false;
  }
}
