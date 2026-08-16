/**
 * BharatBuild CLI — Built-in Tool Registry
 * Central registry for all 14 Kiro-style built-in tools.
 * Handles registration, lookup, approval status, and listing.
 */

import type { BuiltInTool, BuiltInToolDefinition, ApprovalStatus, ToolApprovalConfig } from "./types.js";
import { DEFAULT_APPROVAL_CONFIG } from "./types.js";

export class BuiltInToolRegistry {
  private tools = new Map<string, BuiltInTool>();
  private approvalConfig: ToolApprovalConfig;
  private sessionApprovals = new Map<string, ApprovalStatus>();

  constructor(config?: Partial<ToolApprovalConfig>) {
    this.approvalConfig = { ...DEFAULT_APPROVAL_CONFIG, ...config };
  }

  /** Register a built-in tool */
  register(tool: BuiltInTool): void {
    this.tools.set(tool.definition.name, tool);
  }

  /** Get a tool by name */
  get(name: string): BuiltInTool | undefined {
    return this.tools.get(name);
  }

  /** Check if a tool is registered */
  has(name: string): boolean {
    return this.tools.has(name);
  }

  /** Get all registered tools */
  getAll(): BuiltInTool[] {
    return Array.from(this.tools.values());
  }

  /** Get all tool definitions (for sending to the model) */
  getDefinitions(): BuiltInToolDefinition[] {
    return this.getAll().map((t) => ({
      ...t.definition,
      status: this.getApprovalStatus(t.definition.name),
    }));
  }

  /** Get the tool definitions in Anthropic API format */
  getModelToolDefinitions(): object[] {
    return this.getAll().map((t) => ({
      name: t.definition.name,
      description: t.definition.description,
      input_schema: t.definition.parameters,
    }));
  }

  /** Get the approval status for a tool */
  getApprovalStatus(toolName: string): ApprovalStatus {
    // Session-level override takes priority
    const sessionStatus = this.sessionApprovals.get(toolName);
    if (sessionStatus) return sessionStatus;

    if (this.approvalConfig.alwaysAllow.includes(toolName)) return "allowed";
    if (this.approvalConfig.alwaysDeny.includes(toolName)) return "denied";
    return "approval_required";
  }

  /** Set approval status for a tool in the current session */
  setSessionApproval(toolName: string, status: ApprovalStatus): void {
    this.sessionApprovals.set(toolName, status);
  }

  /** Allow a tool for the session */
  allowTool(toolName: string): void {
    this.sessionApprovals.set(toolName, "allowed");
  }

  /** Deny a tool for the session */
  denyTool(toolName: string): void {
    this.sessionApprovals.set(toolName, "denied");
  }

  /** Reset all session approvals */
  resetSessionApprovals(): void {
    this.sessionApprovals.clear();
  }

  /** Update the approval config (persisted) */
  updateConfig(config: Partial<ToolApprovalConfig>): void {
    Object.assign(this.approvalConfig, config);
  }

  /** Get the current config */
  getConfig(): ToolApprovalConfig {
    return { ...this.approvalConfig };
  }

  /** Render the tools list (like Kiro's /tools output) */
  renderToolsList(): string {
    const lines: string[] = [];
    lines.push(" Name          Source      Status                Description");
    const tools = this.getAll().sort((a, b) => a.definition.name.localeCompare(b.definition.name));
    for (const tool of tools) {
      const name = tool.definition.name.padEnd(14);
      const source = "built-in".padEnd(12);
      const status = this.getApprovalStatus(tool.definition.name);
      const statusStr = status === "allowed"
        ? "✓ allowed"
        : status === "denied"
          ? "✗ denied"
          : "◌ approval required";
      const statusPadded = statusStr.padEnd(22);
      const desc = tool.definition.description.slice(0, 60) + (tool.definition.description.length > 60 ? "..." : "");
      lines.push(` ${name}${source}${statusPadded}${desc}`);
    }
    return lines.join("\n");
  }

  /** Get count of registered tools */
  get size(): number {
    return this.tools.size;
  }
}
