/**
 * BharatBuild CLI — Built-in Tool System Types
 * Mirrors the Kiro CLI tool architecture exactly.
 *
 * Each built-in tool has:
 *   - A name (e.g. "read", "write", "shell")
 *   - A source ("built-in")
 *   - An approval status ("approval required" | "allowed" | "denied")
 *   - A description
 *   - A JSON Schema for parameters
 *   - An execute function
 */

export interface ToolParameter {
  type: string;
  description?: string;
  enum?: string[];
  items?: ToolParameter;
  properties?: Record<string, ToolParameter>;
  required?: string[];
  default?: unknown;
  minItems?: number;
}

export interface ToolSchema {
  type: "object";
  properties: Record<string, ToolParameter>;
  required: string[];
}

export type ApprovalStatus = "approval_required" | "allowed" | "denied";

export interface BuiltInToolDefinition {
  name: string;
  source: "built-in";
  status: ApprovalStatus;
  description: string;
  parameters: ToolSchema;
}

export interface ToolResult {
  content: string;
  isError: boolean;
}

export interface BuiltInTool {
  definition: BuiltInToolDefinition;
  execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult>;
}

/**
 * Tool approval configuration — persisted per-session or per-project.
 */
export interface ToolApprovalConfig {
  /** Tools that are always allowed without prompting */
  alwaysAllow: string[];
  /** Tools that are always denied */
  alwaysDeny: string[];
  /** Default behavior for unlisted tools */
  defaultPolicy: "ask" | "allow" | "deny";
}

export const DEFAULT_APPROVAL_CONFIG: ToolApprovalConfig = {
  alwaysAllow: [],
  alwaysDeny: [],
  defaultPolicy: "ask",
};
