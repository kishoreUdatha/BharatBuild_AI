/**
 * BharatBuild CLI — Built-in Tool Dispatcher
 *
 * This is the new Kiro-style dispatcher that routes tool calls through the
 * built-in tool registry. It replaces the per-tool switch statement with a
 * unified registry-based dispatch.
 *
 * Integrates:
 *   - 14 built-in tools (read, write, glob, grep, shell, code, etc.)
 *   - Approval system (prompts user before execution)
 *   - MCP tools (namespaced, from external servers)
 *   - Event emission for UI display
 */

import { EventStream } from "../../runtime/event-stream.js";
import {
  createToolRegistry,
  BuiltInToolRegistry,
  checkToolApproval,
  applyApprovalDecision,
} from "./index.js";
import type { ToolApprovalConfig, ToolResult as BuiltInToolResult } from "./types.js";
import type { MCPClient } from "../../mcp/mcp-client.js";

export interface DispatcherToolResult {
  toolUseId: string;
  content: string;
  isError: boolean;
}

export interface BuiltInDispatcherOptions {
  approvalConfig?: Partial<ToolApprovalConfig>;
  nonInteractive?: boolean;
}

export class BuiltInToolDispatcher {
  private registry: BuiltInToolRegistry;
  private events: EventStream;
  private mcp?: MCPClient;
  private nonInteractive: boolean;

  constructor(events: EventStream, options?: BuiltInDispatcherOptions) {
    this.events = events;
    this.registry = createToolRegistry(options?.approvalConfig);
    this.nonInteractive = options?.nonInteractive ?? false;
  }

  /** Get the tool registry (for inspection or modification) */
  getRegistry(): BuiltInToolRegistry {
    return this.registry;
  }

  /** Attach MCP servers for external tool support */
  setMCPClient(mcp: MCPClient): void {
    this.mcp = mcp;
  }

  /** Get all tool definitions for sending to the model */
  getDefinitions(): object[] {
    const builtIn = this.registry.getModelToolDefinitions();
    const mcp = this.mcp?.getToolDefinitions() ?? [];
    return [...builtIn, ...mcp];
  }

  /** Execute a tool call */
  async execute(
    toolUseId: string,
    toolName: string,
    input: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<DispatcherToolResult> {
    const startMs = Date.now();

    await this.events.emit(EventStream.toolCall(toolUseId, toolName, input));

    let result: BuiltInToolResult;

    try {
      // Check MCP tools first (namespaced, never shadows built-in)
      if (this.mcp?.handles(toolName)) {
        result = await this.mcp.callTool(toolName, input);
      } else if (this.registry.has(toolName)) {
        // Check approval
        const decision = await checkToolApproval(
          this.registry,
          toolName,
          input,
          { nonInteractive: this.nonInteractive }
        );

        if (decision === "deny") {
          result = { content: `Tool '${toolName}' was denied.`, isError: true };
        } else if (decision === "cancel") {
          result = { content: "Tool execution cancelled by user.", isError: false };
        } else {
          // Apply "allow_always" to registry
          applyApprovalDecision(this.registry, toolName, decision);

          // Execute the tool
          const tool = this.registry.get(toolName)!;
          result = await tool.execute(input, signal);
        }
      } else {
        result = { content: `Unknown tool: ${toolName}`, isError: true };
      }
    } catch (err) {
      result = { content: err instanceof Error ? err.message : String(err), isError: true };
    }

    const durationMs = Date.now() - startMs;
    await this.events.emit(
      EventStream.toolResult(toolUseId, toolName, result.content, result.isError, durationMs)
    );

    return { toolUseId, ...result };
  }

  /** Render the tools panel (for /tools slash command) */
  renderToolsList(): string {
    return this.registry.renderToolsList();
  }

  /** Allow a tool for the rest of the session */
  allowTool(toolName: string): void {
    this.registry.allowTool(toolName);
  }

  /** Deny a tool for the rest of the session */
  denyTool(toolName: string): void {
    this.registry.denyTool(toolName);
  }

  /** Reset all session permissions */
  resetPermissions(): void {
    this.registry.resetSessionApprovals();
  }
}
