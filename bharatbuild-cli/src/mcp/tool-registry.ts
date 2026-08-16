/**
 * BharatBuild CLI - MCP tool registry
 *
 * Holds the tools discovered from connected MCP servers, namespaced so two
 * servers exposing a "search" tool cannot collide with each other or with a
 * built-in tool.
 */
import type { ToolDefinition } from "../tools/filesystem/index.js";

export interface MCPToolEntry {
  /** Namespaced name exposed to the model: mcp__<server>__<tool>. */
  name: string;
  /** Name the owning server knows it by. */
  originalName: string;
  serverName: string;
  definition: ToolDefinition;
}

export function namespacedToolName(serverName: string, toolName: string): string {
  return `mcp__${serverName}__${toolName}`;
}

export class MCPToolRegistry {
  private tools = new Map<string, MCPToolEntry>();

  register(entry: MCPToolEntry): void {
    this.tools.set(entry.name, entry);
  }

  /** Replace every tool belonging to one server (used on reconnect). */
  registerServer(serverName: string, entries: MCPToolEntry[]): void {
    this.unregisterServer(serverName);
    for (const e of entries) this.register(e);
  }

  unregister(name: string): void {
    this.tools.delete(name);
  }

  unregisterServer(serverName: string): void {
    for (const [name, e] of this.tools) {
      if (e.serverName === serverName) this.tools.delete(name);
    }
  }

  get(name: string): MCPToolEntry | undefined {
    return this.tools.get(name);
  }

  getAll(): MCPToolEntry[] {
    return [...this.tools.values()];
  }

  /** Tool definitions in the shape the model API expects. */
  getDefinitions(): ToolDefinition[] {
    return this.getAll().map((e) => e.definition);
  }

  get size(): number {
    return this.tools.size;
  }
}
