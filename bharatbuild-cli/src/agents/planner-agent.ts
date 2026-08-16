/** BharatBuild CLI - Planner Agent
 *
 * Read-only mode: explores the codebase and produces an implementation plan
 * WITHOUT making any changes. Mirrors Kiro CLI's Plan agent exactly.
 *
 * Blocked tools: write_file, execute_command, git_add, git_commit,
 *               subagent, delegate (write-capable)
 * Allowed tools: read_file, list_files, find_files, search_code,
 *               search_files, git_status, git_diff, git_log,
 *               thinking, knowledge, todo_list, web_fetch, web_search
 */
import { getAgent } from "./agent-registry.js";
import type { ModelClient, ModelChunk } from "../runtime/agent-loop.js";
import { ContextManager } from "../runtime/context-manager.js";
import { ToolDispatcher, type ToolResult } from "../runtime/tool-dispatcher.js";
import { EventStream } from "../runtime/event-stream.js";
import { CostMeter } from "../runtime/cost-meter.js";
import { AgentLoop } from "../runtime/agent-loop.js";
import { loadConfig } from "../config/config.js";
import { isBlockedInReadOnly } from "../permissions/read-only.js";



/** Wraps ToolDispatcher and blocks all write operations */
class ReadOnlyToolDispatcher extends ToolDispatcher {
  override getDefinitions(): object[] {
    return super.getDefinitions().filter((d) => {
      const def = d as { name: string };
      return !isBlockedInReadOnly(def.name);
    });
  }

  override async execute(
    toolUseId: string,
    toolName: string,
    input: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ToolResult> {
    if (isBlockedInReadOnly(toolName)) {
      return {
        toolUseId,
        content: `Tool '${toolName}' is not available in Plan (read-only) mode. Produce your plan as text output instead.`,
        isError: true,
      };
    }
    return super.execute(toolUseId, toolName, input, signal);
  }
}

export interface PlanStep {
  step: number;
  description: string;
  files?: string[];
  command?: string;
}

export class PlannerAgent {
  private _loop: AgentLoop;
  private _context: ContextManager;
  readonly events: EventStream;

  constructor(model: ModelClient, modelId?: string) {
    const config = loadConfig();
    const resolvedModelId = modelId ?? config.model ?? "auto";
    const agent = getAgent("planner");
    this.events = new EventStream();
    this._context = new ContextManager();
    this._context.setSystemPrompt(
      agent.systemPrompt +
      "\n\nIMPORTANT: You are in read-only Plan mode. " +
      "You MUST NOT write files, execute commands, or make any changes. " +
      "Explore the codebase using read_file, search_code, and list_files, " +
      "then produce a detailed implementation plan as structured text output. " +
      "When your plan is complete, present it clearly and stop."
    );
    const dispatcher = new ReadOnlyToolDispatcher(this.events, model);
    const cost = new CostMeter(resolvedModelId);
    this._loop = new AgentLoop(model, this._context, dispatcher, this.events, cost);
  }

  async plan(task: string, opts?: { model?: string; maxTurns?: number }): Promise<void> {
    const config = loadConfig();
    await this._loop.run(
      `Create a detailed implementation plan for: ${task}\n\n` +
      `Explore the codebase first (read relevant files, check existing patterns), ` +
      `then output a numbered plan with:\n` +
      `- Each step clearly described\n` +
      `- File paths to create or modify\n` +
      `- Any dependencies or prerequisites\n\n` +
      `Do NOT write any code or make any changes. Plan only.`,
      { model: opts?.model ?? config.model ?? "auto", maxTurns: opts?.maxTurns ?? 10 }
    );
  }
}