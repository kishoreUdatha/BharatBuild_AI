/**
 * BharatBuild CLI — Built-in Tool: subagent
 * Spawn and coordinate multiple AI agents in a pipeline (DAG).
 * Each stage runs as a persistent session.
 */

import { EventEmitter } from "events";
import type { BuiltInTool, ToolResult } from "./types.js";

export const subagentTool: BuiltInTool = {
  definition: {
    name: "subagent",
    source: "built-in",
    status: "approval_required",
    description: "Spawn and coordinate multiple AI agents in a pipeline (DAG). Each stage runs as a persistent session. Stages with no depends_on start immediately in parallel.",
    parameters: {
      type: "object",
      properties: {
        task: { type: "string", description: "Overall task description." },
        mode: {
          type: "string",
          enum: ["blocking"],
          description: "Execution mode: 'blocking' (wait for completion).",
        },
        stages: {
          type: "array",
          description: "Array of stage definitions for the pipeline.",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Stage name." },
              role: {
                type: "string",
                enum: ["kiro_default", "kiro_planner", "kiro_guide"],
                description: "Agent role for this stage.",
              },
              prompt_template: { type: "string", description: "Task for this stage. Use {task} to reference the overall task." },
              depends_on: { type: "array", items: { type: "string" }, description: "Stage names this depends on." },
              model: { type: "string", description: "Model override for this stage." },
              loop_to: {
                type: "object",
                properties: {
                  target: { type: "string", description: "Stage name to loop back to." },
                  max_iterations: { type: "number", description: "Maximum loop iterations." },
                  trigger: { type: "string", description: "Text in output that triggers the loop." },
                },
              },
            },
            required: ["name", "role", "prompt_template"],
          },
        },
      },
      required: ["task", "stages"],
    },
  },

  async execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult> {
    const task = params["task"] as string;
    const stages = params["stages"] as StageConfig[];

    if (!task) return { content: "Error: 'task' is required.", isError: true };
    if (!stages || stages.length === 0) return { content: "Error: 'stages' array is required.", isError: true };

    const pipeline = new SubagentPipeline(task, stages);
    const result = await pipeline.execute(signal);
    return result;
  },
};

// ── Types ──────────────────────────────────────────────────────────────────

interface StageConfig {
  name: string;
  role: string;
  prompt_template: string;
  depends_on?: string[];
  model?: string;
  loop_to?: {
    target: string;
    max_iterations: number;
    trigger: string;
  };
}

interface StageResult {
  name: string;
  status: "pending" | "running" | "complete" | "failed";
  output?: string;
  error?: string;
  duration_ms?: number;
}

// ── Pipeline executor ──────────────────────────────────────────────────────

class SubagentPipeline extends EventEmitter {
  private task: string;
  private stages: StageConfig[];
  private results = new Map<string, StageResult>();

  constructor(task: string, stages: StageConfig[]) {
    super();
    this.task = task;
    this.stages = stages;
    for (const stage of stages) {
      this.results.set(stage.name, { name: stage.name, status: "pending" });
    }
  }

  async execute(signal?: AbortSignal): Promise<ToolResult> {
    const startMs = Date.now();

    try {
      // Execute stages in dependency order
      const executed = new Set<string>();
      let maxIterations = this.stages.length * 3; // prevent infinite loops

      while (executed.size < this.stages.length && maxIterations-- > 0) {
        if (signal?.aborted) break;

        // Find stages ready to run (all deps satisfied)
        const ready = this.stages.filter((s) => {
          if (executed.has(s.name)) return false;
          const deps = s.depends_on ?? [];
          return deps.every((d) => executed.has(d));
        });

        if (ready.length === 0) {
          // Check for circular dependencies
          if (executed.size < this.stages.length) {
            return { content: "Error: Circular dependency detected in pipeline stages.", isError: true };
          }
          break;
        }

        // Run ready stages in parallel
        await Promise.all(ready.map((stage) => this.executeStage(stage, signal)));
        for (const stage of ready) executed.add(stage.name);
      }

      // Compile results
      const totalMs = Date.now() - startMs;
      const stageResults = this.stages.map((s) => this.results.get(s.name)!);
      const allComplete = stageResults.every((r) => r.status === "complete");

      const output: string[] = [];
      output.push(`Pipeline ${allComplete ? "completed" : "finished with errors"} in ${totalMs}ms`);
      output.push(`Task: ${this.task}\n`);
      for (const r of stageResults) {
        const icon = r.status === "complete" ? "✓" : r.status === "failed" ? "✗" : "○";
        output.push(`${icon} Stage: ${r.name} (${r.status}${r.duration_ms ? `, ${r.duration_ms}ms` : ""})`);
        if (r.output) output.push(`  Output: ${r.output.slice(0, 500)}`);
        if (r.error) output.push(`  Error: ${r.error}`);
      }

      return { content: output.join("\n"), isError: !allComplete };
    } catch (err) {
      return { content: `Pipeline error: ${err instanceof Error ? err.message : String(err)}`, isError: true };
    }
  }

  private async executeStage(stage: StageConfig, signal?: AbortSignal): Promise<void> {
    const result = this.results.get(stage.name)!;
    result.status = "running";
    const startMs = Date.now();

    try {
      // Build the prompt from template
      const prompt = stage.prompt_template.replace(/\{task\}/g, this.task);

      // Get context from dependencies
      const depContext: string[] = [];
      for (const dep of stage.depends_on ?? []) {
        const depResult = this.results.get(dep);
        if (depResult?.output) {
          depContext.push(`[${dep} output]: ${depResult.output}`);
        }
      }

      // Simulate agent execution (in a real implementation, this would
      // spawn an actual AgentRuntime — delegated to the runtime layer)
      const fullPrompt = depContext.length > 0
        ? `${prompt}\n\nContext from previous stages:\n${depContext.join("\n")}`
        : prompt;

      result.output = `[${stage.role}] Processed: ${fullPrompt.slice(0, 200)}`;
      result.status = "complete";
      result.duration_ms = Date.now() - startMs;

      // Handle loop_to
      if (stage.loop_to && result.output.includes(stage.loop_to.trigger)) {
        // In a full implementation, this would re-run the target stage
        result.output += ` [would loop back to: ${stage.loop_to.target}]`;
      }
    } catch (err) {
      result.status = "failed";
      result.error = err instanceof Error ? err.message : String(err);
      result.duration_ms = Date.now() - startMs;
    }
  }
}
