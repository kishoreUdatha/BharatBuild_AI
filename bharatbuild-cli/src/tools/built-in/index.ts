/**
 * BharatBuild CLI — Built-in Tools
 * Central entry point for all 14 Kiro-style built-in tools.
 *
 * Tools:
 *   read, write, glob, grep, shell, code,
 *   web_fetch, web_search, knowledge, subagent,
 *   todo_list, goal, introspect, use_aws
 *
 * Usage:
 *   import { createToolRegistry } from "./tools/built-in/index.js";
 *   const registry = createToolRegistry();
 *   const tool = registry.get("shell");
 *   const result = await tool.execute({ command: "ls" });
 */

// Re-exports
export { BuiltInToolRegistry } from "./registry.js";
export type {
  BuiltInTool,
  BuiltInToolDefinition,
  ToolResult,
  ToolSchema,
  ToolParameter,
  ApprovalStatus,
  ToolApprovalConfig,
} from "./types.js";
export { checkToolApproval, applyApprovalDecision } from "./approval.js";
export type { ApprovalDecision } from "./approval.js";

// Tool imports
import { BuiltInToolRegistry } from "./registry.js";
import { readTool } from "./read.js";
import { writeTool } from "./write.js";
import { globTool } from "./glob.js";
import { grepTool } from "./grep.js";
import { shellTool } from "./shell.js";
import { codeTool } from "./code.js";
import { webFetchTool } from "./web-fetch.js";
import { webSearchTool } from "./web-search.js";
import { knowledgeTool } from "./knowledge.js";
import { subagentTool } from "./subagent.js";
import { todoListTool } from "./todo-list.js";
import { goalTool } from "./goal.js";
import { introspectTool } from "./introspect.js";
import { useAwsTool } from "./use-aws.js";
import type { ToolApprovalConfig } from "./types.js";

/**
 * Create and return a fully-configured tool registry with all 14 built-in tools.
 */
export function createToolRegistry(config?: Partial<ToolApprovalConfig>): BuiltInToolRegistry {
  const registry = new BuiltInToolRegistry(config);

  // Register all 14 built-in tools
  registry.register(readTool);
  registry.register(writeTool);
  registry.register(globTool);
  registry.register(grepTool);
  registry.register(shellTool);
  registry.register(codeTool);
  registry.register(webFetchTool);
  registry.register(webSearchTool);
  registry.register(knowledgeTool);
  registry.register(subagentTool);
  registry.register(todoListTool);
  registry.register(goalTool);
  registry.register(introspectTool);
  registry.register(useAwsTool);

  return registry;
}

/**
 * Get all tool definitions in the format expected by the Anthropic API.
 */
export function getToolDefinitionsForModel(registry: BuiltInToolRegistry): object[] {
  return registry.getModelToolDefinitions();
}

/**
 * Convenience: create a registry and print the tools list.
 */
export function printToolsList(registry?: BuiltInToolRegistry): string {
  const r = registry ?? createToolRegistry();
  return r.renderToolsList();
}
