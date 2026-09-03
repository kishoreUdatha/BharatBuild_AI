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
  readProcessOutputDefinition, readProcessOutput,
  stopProcessDefinition, stopProcess,
} from "../tools/shell/process-tools.js";
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
import {
  runTestsDefinition, executeRunTests, type RunTestsInput,
} from "../tools/testing/run-tests-tool.js";
import type { MCPClient } from "../mcp/mcp-client.js";
import {
  readNotebookDefinition, readNotebook,
  editNotebookDefinition, editNotebook,
} from "../tools/notebook/index.js";
import { askUserDefinition, askUser } from "../tools/agent/ask-user.js";
import { takeDenyReason } from "../permissions/deny-reason.js";
import { isFileWriteTool, targetPath } from "../permissions/plan-mode.js";
import { captureBefore } from "./file-snapshots.js";
import {
  githubIssueDefinition, githubIssue, type GithubIssueInput,
  githubPrDefinition, githubPr, type GithubPrInput,
} from "../tools/github/index.js";
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

/**
 * Backend tool names → the CLI implementation that serves them.
 *
 * The server substitutes its own toolset instead of using the definitions the
 * CLI sends, so the model calls names this dispatcher never registered
 * (`edit_file`, `list_directory`) and they came back as "Unknown tool: …".
 * The schemas line up one-for-one, only the parameter names differ.
 *
 * This is a compatibility shim. The durable fix is for the backend to honour
 * the client's tool definitions, or for both to share one registry.
 */
const TOOL_ALIASES: Record<
  string,
  { name: string; mapInput?: (input: Record<string, unknown>) => Record<string, unknown> }
> = {
  // edit_file{path, old_string, new_string} → apply_patch{file_path, …}
  edit_file: {
    name: "apply_patch",
    mapInput: (i) => ({ ...i, file_path: i["file_path"] ?? i["path"] }),
  },
  // list_directory{path} → list_files{path}
  list_directory: { name: "list_files" },
};

function resolveAlias(
  toolName: string,
  input: Record<string, unknown>,
): { name: string; input: Record<string, unknown> } {
  const alias = TOOL_ALIASES[toolName];
  if (!alias) return { name: toolName, input };
  return { name: alias.name, input: alias.mapInput ? alias.mapInput(input) : input };
}

/**
 * Tools the model is no longer told about, because another tool does the same
 * job under a clearer name.
 *
 * Six pairs did identical work: read/read_file, write/write_file,
 * glob/find_files, grep/search_code, shell/execute_command, and
 * search_files (covered by glob plus grep). That cost ~940 tokens a turn, but
 * the real damage was to tool selection — the model had to choose between two
 * indistinguishable options on every decision, with nothing in the
 * descriptions to say which was right. It is also where the alias bugs came
 * from: the backend advertised one spelling, the CLI registered the other.
 *
 * Survivors were chosen on schema simplicity and output quality:
 *   read_file        `path` beats `read`'s batched operations array
 *   write_file       renders a unified diff; `write` returns a bare string
 *   glob             clearer name for the same job as find_files
 *   grep             output_mode/count support that search_code lacks
 *   execute_command  timeout_ms, and guidance naming builds and tests
 *
 * These are hidden, not removed. execute() still dispatches every one of them,
 * so a resumed session or a backend advertising the other spelling keeps
 * working — only the advertised set shrinks.
 *
 * Known trade-off: `read`'s Image mode is no longer advertised. Text and
 * directory reads are covered by read_file and list_files; image reading is
 * still reachable by name but the model will not discover it.
 */
const HIDDEN_FROM_MODEL = new Set([
  "read", "write", "find_files", "search_code", "shell", "search_files",
]);

/** Keep the first definition for each tool name. */
function dedupeByName(defs: object[]): object[] {
  const seen = new Set<string>();
  const out: object[] = [];
  for (const def of defs) {
    const name = (def as { name?: unknown }).name;
    if (typeof name !== "string") continue;
    if (seen.has(name)) continue;
    seen.add(name);
    if (HIDDEN_FROM_MODEL.has(name)) continue;
    out.push(def);
  }
  return out;
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
    // Six tools (web_fetch, web_search, knowledge, subagent, todo_list, goal)
    // are supplied by BOTH the built-in registry and the legacy list below, so
    // the array shipped to the model contained duplicate names. Providers
    // reject a tools array with repeated names, which would break the
    // direct-API-key path; the proxy path only escaped it because the backend
    // substitutes its own toolset.
    //
    // First occurrence wins, matching execute()'s dispatch order — it checks
    // the built-in registry before falling through to the legacy switch — so
    // the definition advertised is the implementation that actually runs.
    return dedupeByName([
      // ── 14 Kiro-style built-in tools ──────────────────────────────────
      ...this._builtInRegistry.getModelToolDefinitions(),
      // ── Legacy tools (backward compat) ────────────────────────────────
      // Filesystem
      readFileDefinition,
      writeFileDefinition,
      listFilesDefinition,
      findFilesDefinition,
      applyPatchDefinition,
      askUserDefinition,
      readNotebookDefinition,
      editNotebookDefinition,
      deleteFileDefinition,
      // Shell
      executeCommandDefinition,
      // Starting a server is only half of it: without these the agent cannot
      // see what it printed afterwards or shut it down.
      readProcessOutputDefinition,
      stopProcessDefinition,
      // Git
      gitStatusDefinition,
      gitDiffDefinition,
      gitLogDefinition,
      gitAddDefinition,
      gitCommitDefinition,
      githubIssueDefinition,
      githubPrDefinition,
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
      // Testing
      runTestsDefinition,
      // Web
      webFetchDefinition,
      webSearchDefinition,
      // MCP (namespaced mcp__<server>__<tool>; empty when none configured)
      ...(this._mcp?.getToolDefinitions() ?? []),
    ]);
  }

  /** Execute a tool by name */
  async execute(
    toolUseId: string,
    requestedName: string,
    requestedInput: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ToolResult> {
    const startMs = Date.now();

    // Map server-side tool names onto the local implementation before anything
    // else, so approval, dispatch and the transcript all agree on what ran.
    const { name: toolName, input } = resolveAlias(requestedName, requestedInput);

    // Snapshot the target before a tool that writes runs, so `esc esc` can put
    // the file back. Cheap by design: one read of the file about to change,
    // not a copy of the tree.
    if (isFileWriteTool(toolName)) {
      const target = targetPath(input);
      if (target) captureBefore(target);
    }

    await this._events.emit(EventStream.toolCall(toolUseId, toolName, input));

    let result: { content: string; isError: boolean };

    try {
      // ── Try built-in tools first (14 Kiro-style tools) ──────────────────
      if (this._builtInRegistry.has(toolName)) {
        // Check approval status
        // This passed `nonInteractive: !!TRUST_ALL`, and checkToolApproval
        // denies when nonInteractive is set — so --trust-all-tools *blocked*
        // every built-in tool, the exact opposite of what the flag means.
        // The trust check now lives inside checkToolApproval.
        const decision = await checkToolApproval(
          this._builtInRegistry,
          toolName,
          input,
          { nonInteractive: !process.stdin.isTTY }
        );

        if (decision === "deny") {
          // A mode-driven refusal explains itself; otherwise the model reads a
          // bare denial as a transient failure and retries the same call.
          const reason = takeDenyReason();
          result = { content: reason ?? `Tool '${toolName}' was denied.`, isError: true };
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
        case "run_tests":
          result = await executeRunTests(input as RunTestsInput);
          break;

        case "ask_user":
          result = await askUser(input as unknown as Parameters<typeof askUser>[0]);
          break;

        case "read_notebook":
          result = await readNotebook(input as unknown as Parameters<typeof readNotebook>[0]);
          break;

        case "edit_notebook":
          result = await editNotebook(input as unknown as Parameters<typeof editNotebook>[0]);
          break;

        case "execute_command":
          result = await executeCommand(input as unknown as Parameters<typeof executeCommand>[0], signal);
          break;

        case "github_issue":
          result = await githubIssue(input as unknown as GithubIssueInput);
          break;

        case "github_pr":
          result = await githubPr(input as unknown as GithubPrInput);
          break;

        case "read_process_output":
          result = await readProcessOutput(input as { pid?: number });
          break;

        case "stop_process":
          result = await stopProcess(input as { pid: number });
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