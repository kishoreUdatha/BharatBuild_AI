﻿/**
 * BharatBuild CLI - Delegate Tool
 *
 * Similar to subagent but designed for fire-and-forget delegation.
 * The main agent can hand off a task to a specialist and get back
 * a structured result. Runs synchronously (awaits completion) so the
 * main agent can use the result in its next reasoning step.
 *
 * Difference from subagent:
 *   - subagent: general purpose, any agent role, full tool access
 *   - delegate: targeted delegation with a specific goal and structured output
 */

import { EventEmitter } from "events";
import { AgentRuntime } from "../../runtime/agent-runtime.js";
import type { AgentEvent } from "../../runtime/event-stream.js";
import { createModelClientAuto } from "../../models/model-router.js";
import { loadConfig } from "../../config/config.js";

// ── Tool Definition ────────────────────────────────────────────────────────

export const delegateDefinition = {
  name: "delegate",
  description:
    "Delegate a focused task to a specialist AI agent and get back its result. " +
    "Use this when you want to hand off a well-defined subtask (e.g. 'write unit tests " +
    "for this function', 'review this code for security issues', 'create a plan for X'). " +
    "The delegated agent runs to completion and returns its findings/output.",
  input_schema: {
    type: "object",
    properties: {
      task: {
        type: "string",
        description: "The specific task to delegate. Include all necessary context since the delegate agent starts fresh.",
      },
      specialist: {
        type: "string",
        enum: ["coder", "tester", "reviewer", "planner", "fixer", "analyst"],
        description: "Which specialist to delegate to. Choose based on the task type.",
      },
      context: {
        type: "string",
        description: "Optional extra context to pass to the delegate (e.g. relevant file contents, constraints).",
      },
      model: {
        type: "string",
        description: "Override the model for this delegate. Defaults to 'auto'.",
      },
    },
    required: ["task", "specialist"],
  },
} as const;

// ── Specialist system prompts ──────────────────────────────────────────────

const SPECIALIST_PROMPTS: Record<string, string> = {
  coder:    "You are an expert software engineer. Write clean, well-tested, production-quality code. Follow existing patterns. Return the complete implementation.",
  tester:   "You are a QA engineer. Write comprehensive tests. Cover edge cases and happy paths. Return the complete test code.",
  reviewer: "You are a code reviewer. Check for bugs, security issues, performance problems, and code quality. Return a structured review with findings and recommendations.",
  planner:  "You are a senior software architect. Create a clear, ordered implementation plan. Break the work into concrete actionable steps with dependencies noted.",
  fixer:    "You are a debugging expert. Identify root causes, not symptoms. Return the fix with an explanation of what was wrong and why your fix is correct.",
  analyst:  "You are a technical analyst. Analyze the given problem or codebase thoroughly. Return structured findings with clear conclusions.",
};

// ── DelegatedTask state ────────────────────────────────────────────────────

export interface DelegatedTask {
  id: string;
  task: string;
  specialist: string;
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

export class DelegateManager extends EventEmitter {
  private tasks = new Map<string, DelegatedTask>();

  /** Legacy handler-based delegation (kept for backwards compat) */
  delegate(task: string, handler: (task: string) => Promise<string>): DelegatedTask {
    const t: DelegatedTask = {
      id: `delegate-${Date.now()}`,
      task,
      specialist: "default",
      status: "pending",
    };
    this.tasks.set(t.id, t);
    t.status = "running";
    t.startedAt = new Date().toISOString();
    handler(task)
      .then((result) => {
        t.status = "complete";
        t.result = result;
        t.completedAt = new Date().toISOString();
        this.emit("complete", t);
      })
      .catch((err: Error) => {
        t.status = "failed";
        t.error = err.message;
        t.completedAt = new Date().toISOString();
        this.emit("failed", t);
      });
    return t;
  }

  track(id: string, task: DelegatedTask): void {
    this.tasks.set(id, task);
  }

  getTask(id: string) { return this.tasks.get(id); }
  listTasks() { return Array.from(this.tasks.values()); }
  getStatus(id: string) { return this.tasks.get(id)?.status ?? "not found"; }
}

export const delegateManager = new DelegateManager();

// ── Tool executor ──────────────────────────────────────────────────────────

export interface DelegateInput {
  task: string;
  specialist: string;
  context?: string;
  model?: string;
}

/**
 * Execute the delegate tool — runs a specialist nested AgentRuntime
 * and returns its output to the parent agent.
 */
export async function executeDelegate(
  input: DelegateInput,
  signal?: AbortSignal
): Promise<{ content: string; isError: boolean }> {
  const { task, specialist, context, model } = input;

  const taskRecord: DelegatedTask = {
    id: `delegate-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    task,
    specialist,
    status: "running",
    startedAt: new Date().toISOString(),
  };
  delegateManager.track(taskRecord.id, taskRecord);
  delegateManager.emit("started", taskRecord);

  try {
    const config = loadConfig();
    const activeModel = model ?? config.model ?? "auto";
    const modelClient = createModelClientAuto(activeModel);

    const runtime = new AgentRuntime({
      config: {
        ...config,
        model: activeModel,
        maxTurns: 15,
      },
      model: modelClient,
    });

    // Set specialist system prompt
    const promptBase = SPECIALIST_PROMPTS[specialist] ?? SPECIALIST_PROMPTS["coder"]!;
    runtime.context.setSystemPrompt(
      `${promptBase}\n\nWorking directory: ${config.workingDir}\n` +
      `You have access to tools: read_file, write_file, execute_command, search_code, git_status, etc.\n` +
      `Complete the task fully, then stop.`
    );

    // Build the full task message, including optional extra context
    const fullTask = context
      ? `${task}\n\n--- Additional Context ---\n${context}`
      : task;

    // Collect output
    let output = "";
    runtime.events.on("text", (event: AgentEvent) => {
      if (event.type === "text" && event.content) output += event.content;
    });

    await runtime.run(fullTask, { signal });

    taskRecord.status = "complete";
    taskRecord.result = output;
    taskRecord.completedAt = new Date().toISOString();
    delegateManager.emit("complete", taskRecord);

    return {
      content: output || `Delegate [${specialist}] completed with no text output.`,
      isError: false,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    taskRecord.status = "failed";
    taskRecord.error = msg;
    taskRecord.completedAt = new Date().toISOString();
    delegateManager.emit("failed", taskRecord);

    return {
      content: `Delegate [${specialist}] failed: ${msg}`,
      isError: true,
    };
  }
}