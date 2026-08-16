/**
 * BharatBuild CLI - Tool Dispatcher
 * Routes tool calls from the agent loop to the correct implementation.
 *
 * Registered tools:
 *   Built-in (14 Kiro-style):
 *     read, write, glob, grep, shell, code, web_fetch, web_search,
 *     knowledge, subagent, todo_list, goal, introspect, use_aws
 *
 *   Legacy (backward compat):
 *     Filesystem : read_file, write_file, list_files, find_files, apply_patch, delete_file
 *     Shell      : execute_command
 *     Git        : git_status, git_diff, git_log, git_add, git_commit
 *     Search     : search_code, search_files
 *     Agent      : delegate, thinking, guide
 */

import { EventStream } from "./event-stream.js";
import {
  readFileDefinition, writeFileDefinition, listFilesDefinition, findFilesDefinition,
  readFile, writeFile, listFiles, findFiles,
} from "../tools/filesystem/index.js";
import { applyPatchDefinition, applyPatch } from "../tools/filesystem/apply-patch.js";
import { deleteFileDefinition, deleteFile } from "../tools/filesystem/delete-file.js";
import { executeCommandDefinition, executeCommand } from "../tools/shell/index.js";
import {
  gitStatusDefinition, gitDiffDefinition, gitLogDefinition,
  gitAddDefinition, gitCommitDefinition,
  gitStatus, gitDiff, gitLog, gitAdd, gitCommit,
} from "../tools/git/index.js";
import {
  searchCodeDefinition, searchFilesDefinition,
  searchCode, searchFiles,
} from "../tools/search/index.js";
import {
  subagentDefinition, executeSubagent, type SubagentInput,
} from "../tools/agent/subagent.js";
import {
  delegateDefinition, executeDelegate, type DelegateInput,
} from "../tools/agent/delegate.js";
import {
  goalDefinition, executeGoal, type GoalInput,
} from "../tools/agent/goal.js";
import {
  thinkingDefinition, executeThinking, type ThinkingInput,
} from "../tools/agent/thinking.js";
import {
  knowledgeDefinition, executeKnowledge, type KnowledgeInput,
} from "../tools/agent/knowledge.js";
import {
  todoDefinition, executeTodo, type TodoInput,
} from "../tools/agent/todo.js";
import {
  guideDefinition, executeGuide, type GuideInput,
} from "../tools/agent/guide.js";
import {
  webFetchDefinition, webSearchDefinition,
  executeWebFetch, executeWebSearch,
  type WebFetchInput, type WebSearchInput,
} from "../tools/web/index.js";
import type { MCPClient } from "../mcp/mcp-client.js";
import {
  createToolRegistry,
  BuiltInToolRegistry,
  checkToolApproval,
  applyApprovalDecision,
} from "../tools/built-in/index.js";

export interface ToolResult {
  toolUseId: string;
  content: string;
  isError: boolean;
}

export class ToolDispatcher {
  private _events: EventStream;
  private _modelClient?: import("../runtime/agent-loop.js").ModelClient;
  private _mcp?: MCPClient;
  private _builtInRegistry: BuiltInToolRegistry;

  constructor(events: EventStream, modelClient?: import("../runtime/agent-loop.js").ModelClient) {
    this._events = events;
    this._modelClient = modelClient;
    this._builtInRegistry = createToolRegistry();
  }

  /** Get the built-in tool registry (for /tools display and approval management) */
  getBuiltInRegistry(): BuiltInToolRegistry {
    return this._builtInRegistry;
  }

  /** Render built-in tools list (Kiro-style output) */
  renderBuiltInToolsList(): string {
    return this._builtInRegistry.renderToolsList();
  }

  /** Allow a built-in tool for the session (skip approval) */
  trustBuiltInTool(toolName: string): void {
    this._builtInRegistry.allowTool(toolName);
  }

  /** Deny a built-in tool for the session */
  denyBuiltInTool(toolName: string): void {
    this._builtInRegistry.denyTool(toolName);
  }

  /** Reset all built-in tool approvals */
  resetBuiltInApprovals(): void {
    this._builtInRegistry.resetSessionApprovals();
  }

  /** Trust all built-in tools (skip all confirmations) */
  trustAllBuiltInTools(): void {
    for (const tool of this._builtInRegistry.getAll()) {
      this._builtInRegistry.allowTool(tool.definition.name);
    }
  }

  /** Inject model client (needed for guide tool) */
  setModelClient(client: import("../runtime/agent-loop.js").ModelClient): void {
    this._modelClient = client;
  }

  /**
   * Attach connected MCP servers. Their tools are appended to the definitions
   * sent to the model and routed back here by namespaced name.
   */
  setMCPClient(mcp: MCPClient): void {
    this._mcp = mcp;
  }

  /** Returns all tool definitions for sending to the model */
  getDefinitions(): object[] {
    return [
      // ── 14 Kiro-style built-in tools ──────────────────────────────────
      ...this._builtInRegistry.getModelToolDefinitions(),
      // ── Legacy tools (backward compat) ────────────────────────────────
      // Filesystem
      readFileDefinition,
      writeFileDefinition,
      listFilesDefinition,
      findFilesDefinition,
      applyPatchDefinition,
      deleteFileDefinition,
      // Shell
      executeCommandDefinition,
      // Git
      gitStatusDefinition,
      gitDiffDefinition,
      gitLogDefinition,
      gitAddDefinition,
      gitCommitDefinition,
      // Search
      searchCodeDefinition,
      searchFilesDefinition,
      // Agent orchestration
      subagentDefinition,
      delegateDefinition,
      goalDefinition,
      // Reasoning + productivity
      thinkingDefinition,
      knowledgeDefinition,
      todoDefinition,
      guideDefinition,
      // Web
      webFetchDefinition,
      webSearchDefinition,
      // MCP (namespaced mcp__<server>__<tool>; empty when none configured)
      ...(this._mcp?.getToolDefinitions() ?? []),
    ];
  }

  /** Execute a tool by name */
  async execute(
    toolUseId: string,
    toolName: string,
    input: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ToolResult> {
    const startMs = Date.now();

    await this._events.emit(EventStream.toolCall(toolUseId, toolName, input));

    let result: { content: string; isError: boolean };

    try {
      // ── Try built-in tools first (14 Kiro-style tools) ──────────────────
      if (this._builtInRegistry.has(toolName)) {
        // Check approval status
        const decision = await checkToolApproval(
          this._builtInRegistry,
          toolName,
          input,
          { nonInteractive: !!process.env["BHARATBUILD_TRUST_ALL_TOOLS"] }
        );

        if (decision === "deny") {
          result = { content: `Tool '${toolName}' was denied.`, isError: true };
        } else if (decision === "cancel") {
          result = { content: "Tool execution cancelled by user.", isError: false };
        } else {
          // Apply "allow_always" to registry
          applyApprovalDecision(this._builtInRegistry, toolName, decision);
          // Execute
          const tool = this._builtInRegistry.get(toolName)!;
          result = await tool.execute(input, signal);
        }
      }
      // ── MCP tools (namespaced, never shadow built-in) ───────────────────
      else if (this._mcp?.handles(toolName)) {
        result = await this._mcp.callTool(toolName, input);
      }
      // ── Legacy tools (backward compat) ──────────────────────────────────
      else {
        switch (toolName) {
        // ── Filesystem ────────────────────────────────────────────────────
        case "read_file":
          result = await readFile(input as Parameters<typeof readFile>[0]);
          break;
        case "write_file":
          result = await writeFile(input as Parameters<typeof writeFile>[0]);
          break;
        case "list_files":
          result = await listFiles(input as Parameters<typeof listFiles>[0]);
          break;
        case "find_files":
          result = await findFiles(input as Parameters<typeof findFiles>[0]);
          break;
        case "apply_patch":
          result = await applyPatch(input as Parameters<typeof applyPatch>[0]);
          break;
        case "delete_file":
          result = await deleteFile(input as Parameters<typeof deleteFile>[0]);
          break;

        // ── Shell ─────────────────────────────────────────────────────────
        case "execute_command":
          result = await executeCommand(input as Parameters<typeof executeCommand>[0], signal);
          break;

        // ── Git ───────────────────────────────────────────────────────────
        case "git_status":
          result = await gitStatus(input as Parameters<typeof gitStatus>[0]);
          break;
        case "git_diff":
          result = await gitDiff(input as Parameters<typeof gitDiff>[0]);
          break;
        case "git_log":
          result = await gitLog(input as Parameters<typeof gitLog>[0]);
          break;
        case "git_add":
          result = await gitAdd(input as Parameters<typeof gitAdd>[0]);
          break;
        case "git_commit":
          result = await gitCommit(input as Parameters<typeof gitCommit>[0]);
          break;

        // ── Search ────────────────────────────────────────────────────────
        case "search_code":
          result = await searchCode(input as Parameters<typeof searchCode>[0]);
          break;
        case "search_files":
          result = await searchFiles(input as Parameters<typeof searchFiles>[0]);
          break;

        // ── Agent orchestration ───────────────────────────────────────────
        case "subagent":
          await this._events.emit(EventStream.status(
            `spawning subagent [${(input["agent"] as string) ?? "default"}]: ${String(input["task"] ?? "").slice(0, 60)}…`,
            "thinking"
          ));
          result = await executeSubagent(input as unknown as SubagentInput, signal);
          break;

        case "delegate":
          await this._events.emit(EventStream.status(
            `delegating to [${(input["specialist"] as string) ?? "coder"}]: ${String(input["task"] ?? "").slice(0, 60)}…`,
            "thinking"
          ));
          result = await executeDelegate(input as unknown as DelegateInput, signal);
          break;

        case "goal":
          result = executeGoal(input as unknown as GoalInput);
          break;

        // ── Reasoning + productivity ──────────────────────────────────────
        case "thinking":
          result = executeThinking(input as unknown as ThinkingInput);
          break;

        case "knowledge":
          result = executeKnowledge(input as unknown as KnowledgeInput);
          break;

        case "todo_list":
          result = executeTodo(input as unknown as TodoInput);
          break;

        case "guide":
          if (!this._modelClient) {
            result = { content: "Guide tool requires a model client (not yet initialized).", isError: true };
          } else {
            result = await executeGuide(input as unknown as GuideInput, this._modelClient);
          }
          break;

        // ── Web ──────────────────────────────────────────────────────────────
        case "web_fetch":
          result = await executeWebFetch(input as unknown as WebFetchInput);
          break;

        case "web_search":
          result = await executeWebSearch(input as unknown as WebSearchInput);
          break;

        // ── Unknown ───────────────────────────────────────────────────────
        default:
          result = { content: `Unknown tool: ${toolName}`, isError: true };
        }
      }
    } catch (err) {
      result = { content: err instanceof Error ? err.message : String(err), isError: true };
    }

    const durationMs = Date.now() - startMs;
    await this._events.emit(EventStream.toolResult(toolUseId, toolName, result.content, result.isError, durationMs));
    return { toolUseId, ...result };
  }
}