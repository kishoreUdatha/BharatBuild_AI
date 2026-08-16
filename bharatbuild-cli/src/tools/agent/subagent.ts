﻿/**
 * BharatBuild CLI - Subagent Tool
 *
 * Provides the `subagent` tool that the main agent can call to spawn
 * a nested AgentRuntime for a subtask. Each subagent gets its own
 * context, model client, and tool dispatcher — fully isolated.
 *
 * Tool definition follows the Anthropic tool schema so the model
 * can call it directly during the agent loop.
 */

import { EventEmitter } from "events";
import { AgentRuntime } from "../../runtime/agent-runtime.js";
import type { AgentEvent } from "../../runtime/event-stream.js";
import { createModelClientAuto } from "../../models/model-router.js";
import { loadConfig } from "../../config/config.js";

// ── Tool Definition ────────────────────────────────────────────────────────

export const subagentDefinition = {
  name: "subagent",
  description:
    "Spawn a nested AI subagent to handle a focused subtask. " +
    "The subagent runs its own full agent loop with tool access and returns a result. " +
    "Use this to delegate complex or parallelisable subtasks (e.g. write tests, " +
    "implement a module, run analysis). The subagent has access to all the same tools " +
    "(read_file, write_file, execute_command, search_code, git_*, etc.).",
  input_schema: {
    type: "object",
    properties: {
      task: {
        type: "string",
        description: "The specific task for the subagent to complete. Be detailed — the subagent starts with no prior context.",
      },
      agent: {
        type: "string",
        enum: ["default", "planner", "coder", "tester", "fixer", "reviewer"],
        description: "Which specialist agent to use. Defaults to 'default'.",
      },
      model: {
        type: "string",
        description: "Override the model for this subagent. Defaults to 'auto'.",
      },
      max_turns: {
        type: "number",
        description: "Maximum turns the subagent can take. Defaults to 20.",
      },
      parallel: {
        type: "boolean",
        description:
          "When true and called alongside other subagent invocations, this subagent " +
          "runs concurrently with the others. The main agent collects all results " +
          "before continuing. Default: true.",
      },
    },
    required: ["task"],
  },
} as const;

// ── Agent role system prompts ──────────────────────────────────────────────

const AGENT_PROMPTS: Record<string, string> = {
  default:  "You are BharatBuild AI, an expert software engineer assistant. Complete the given task thoroughly using available tools.",
  planner:  "You are a senior software architect. Break the task into a clear implementation plan, then execute it step by step.",
  coder:    "You are an expert software engineer. Write clean, well-tested, production-quality code. Follow existing patterns in the codebase.",
  tester:   "You are a QA engineer. Write comprehensive unit and integration tests. Cover edge cases. Verify all tests pass.",
  fixer:    "You are a debugging expert. Identify root causes of errors (not symptoms). Fix issues without breaking existing functionality.",
  reviewer: "You are a code reviewer. Check for bugs, security vulnerabilities, performance issues, and code quality. Provide specific, actionable feedback.",
};

// ── SubagentManager (state tracker) ───────────────────────────────────────

export interface SubagentConfig {
  id: string;
  task: string;
  agent: string;
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
  error?: string;
  startMs?: number;
  durationMs?: number;
}

export class SubagentManager extends EventEmitter {
  private agents = new Map<string, SubagentConfig>();

  spawn(task: string, agentName?: string, handler?: (task: string) => Promise<string>): SubagentConfig {
    const cfg: SubagentConfig = {
      id: `subagent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      task,
      agent: agentName ?? "default",
      status: "pending",
    };
    this.agents.set(cfg.id, cfg);
    this.emit("spawned", cfg);

    if (handler) {
      cfg.status = "running";
      cfg.startMs = Date.now();
      handler(task)
        .then((result) => {
          cfg.status = "complete";
          cfg.result = result;
          cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
          this.emit("complete", cfg);
        })
        .catch((err: Error) => {
          cfg.status = "failed";
          cfg.error = err.message;
          cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
          this.emit("failed", cfg);
        });
    }
    return cfg;
  }

  listAgents() { return Array.from(this.agents.values()); }
  getAgent(id: string) { return this.agents.get(id); }

  renderCrewMonitor(): string {
    const agents = this.listAgents();
    if (agents.length === 0) return "  No active subagents.";
    return agents
      .map((a) => {
        const icon = a.status === "complete" ? "✓" : a.status === "failed" ? "✗" : a.status === "running" ? "⠿" : "○";
        const dur = a.durationMs ? ` (${a.durationMs}ms)` : "";
        return `  ${icon} [${a.agent}] ${a.task.slice(0, 50)}${dur}`;
      })
      .join("\n");
  }
}

export const subagentManager = new SubagentManager();

// ── Tool executor ──────────────────────────────────────────────────────────

export interface SubagentInput {
  task: string;
  agent?: string;
  model?: string;
  max_turns?: number;
  parallel?: boolean;  // hint for the dispatcher — actual parallelism handled in AgentLoop
}

/**
 * Execute the subagent tool — spawns a nested AgentRuntime and runs it
 * to completion, returning the collected output as a string.
 */
export async function executeSubagent(
  input: SubagentInput,
  signal?: AbortSignal
): Promise<{ content: string; isError: boolean }> {
  const { task, agent = "default", model, max_turns = 20 } = input;

  const cfg = subagentManager.spawn(task, agent);
  cfg.status = "running";
  cfg.startMs = Date.now();
  subagentManager.emit("started", cfg);

  try {
    const config = loadConfig();
    const activeModel = model ?? config.model ?? "auto";
    const modelClient = createModelClientAuto(activeModel);

    // Build isolated nested runtime
    const runtime = new AgentRuntime({
      config: {
        ...config,
        model: activeModel,
        maxTurns: max_turns,
      },
      model: modelClient,
    });

    // Override system prompt with agent-role prompt
    const rolePrompt = AGENT_PROMPTS[agent] ?? AGENT_PROMPTS["default"]!;
    runtime.context.setSystemPrompt(
      `${rolePrompt}\n\nWorking directory: ${config.workingDir}\n` +
      `You have access to tools for reading/writing files, running shell commands, ` +
      `searching code, and managing git. Complete the task fully, then stop.`
    );

    // Collect output text
    let output = "";
    runtime.events.on("text", (event: AgentEvent) => {
      if (event.type === "text" && event.content) output += event.content;
    });

    await runtime.run(task, { signal });

    cfg.status = "complete";
    cfg.result = output;
    cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
    subagentManager.emit("complete", cfg);

    return {
      content: output || `Subagent [${agent}] completed task with no text output.`,
      isError: false,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    cfg.status = "failed";
    cfg.error = msg;
    cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
    subagentManager.emit("failed", cfg);

    return {
      content: `Subagent [${agent}] failed: ${msg}`,
      isError: true,
    };
  }
}