/**
 * BharatBuild CLI — Built-in Tool: subagent
 * Spawn and coordinate multiple AI agents in a pipeline (DAG).
 * Each stage runs as a persistent session.
 */

import { EventEmitter } from "events";
import type { BuiltInTool, ToolResult } from "./types.js";
import { AgentRuntime } from "../../runtime/agent-runtime.js";
import type { AgentEvent } from "../../runtime/event-stream.js";
import { createModelClientAuto } from "../../models/model-router.js";
import { loadConfig } from "../../config/config.js";

/** Cap per stage: a looping stage spends tokens with nobody watching. */
const STAGE_MAX_TURNS = 15;

/**
 * System prompt per role. The roles are the three the schema advertises;
 * anything else falls back to kiro_default rather than running with no prompt.
 */
/**
 * Roles that only think. A prompt saying "do not write the implementation" is
 * not a constraint - the planner stage in a live run wrote the file anyway,
 * then the build stage rewrote it. Plan mode makes the role mean something.
 */
const READ_ONLY_ROLES = new Set(["kiro_planner", "kiro_guide"]);

const ROLE_PROMPTS: Record<string, string> = {
  kiro_default: "You are BharatBuild AI, an expert software engineer. Complete the given task thoroughly using the available tools.",
  kiro_planner: "You are a senior software architect. Produce a clear, concrete plan for the task: the files to change, the order to change them, and the risks. Do not write the implementation.",
  kiro_guide: "You are a technical guide. Explain what the task involves, the options available, and which you recommend and why. Prefer reading the codebase over guessing.",
};

/**
 * How a single stage gets run. Injectable so the pipeline can be tested
 * without a model or a network - the default spawns a real nested agent.
 */
export type StageRunner = (
  stage: StageConfig,
  prompt: string,
  signal?: AbortSignal,
) => Promise<string>;

export const subagentTool: BuiltInTool = {
  definition: {
    name: "subagent",
    source: "built-in",
    status: "approval_required",
    description:
      "Hand a task to a separate agent with its own context. For one task, pass " +
      "just task and optionally role — no stages needed. For work that has to " +
      "happen in order, pass stages to build a pipeline (a DAG); stages with no " +
      "depends_on start in parallel.",
    parameters: {
      type: "object",
      properties: {
        task: { type: "string", description: "What the agent should do. Be specific — it starts with no context." },
        role: {
          type: "string",
          enum: ["kiro_default", "kiro_planner", "kiro_guide"],
          description:
            "Role for the single-stage form. kiro_planner and kiro_guide are " +
            "read-only. Ignored when stages is given.",
        },
        mode: {
          type: "string",
          enum: ["blocking"],
          description: "Execution mode: 'blocking' (wait for completion).",
        },
        stages: {
          type: "array",
          description:
            "Optional. Only for multi-step work that must happen in order — omit it " +
            "to run the task as one stage.",
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
              // loop_to was advertised here but never implemented: a stage
              // whose output contained the trigger reported that it "would
              // loop back", and nothing retried. The `crew` command's DAG
              // executor does implement it - see src/crew/dag-executor.ts -
              // so the capability exists, just not through this tool.
            },
            required: ["name", "role", "prompt_template"],
          },
        },
      },
      required: ["task"],
    },
  },

  async execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult> {
    const task = params["task"] as string;
    if (!task) return { content: "Error: 'task' is required.", isError: true };

    // Requiring a stages array meant the model had to author a DAG before it
    // could delegate anything. For "write unit tests for auth.ts" that is more
    // work than doing the task, so the tool went unused. One task is now the
    // simple case, and a pipeline is what you opt into.
    const stages = stagesFor(params);

    // The schema marks name/role/prompt_template required per stage, but only
    // the two fields above were ever checked. A stage missing prompt_template
    // reached `stage.prompt_template.replace(...)` and surfaced as
    // "Cannot read properties of undefined (reading 'replace')" - a stack
    // detail the model cannot act on. Say which stage and which field.
    const problems: string[] = [];
    const seen = new Set<string>();
    stages.forEach((stage, i) => {
      const label = stage?.name ? `'${stage.name}'` : `at index ${i}`;
      if (!stage || typeof stage !== "object") { problems.push(`stage ${label} is not an object`); return; }
      for (const field of ["name", "role", "prompt_template"] as const) {
        if (typeof stage[field] !== "string" || !stage[field]) {
          problems.push(`stage ${label} is missing '${field}'`);
        }
      }
      if (stage.name) {
        // Results are keyed by name, so a duplicate silently overwrites the
        // earlier stage and the pipeline reports fewer stages than it was given.
        if (seen.has(stage.name)) problems.push(`stage name '${stage.name}' is used more than once`);
        seen.add(stage.name);
      }
      for (const dep of stage.depends_on ?? []) {
        if (!stages.some((s) => s?.name === dep)) {
          problems.push(`stage ${label} depends on '${dep}', which is not one of the stages`);
        }
      }
    });
    if (problems.length) {
      return {
        content: `Error: invalid 'stages'.\n${problems.map((p) => `  - ${p}`).join("\n")}\n\n` +
          `Each stage needs name, role and prompt_template; depends_on must name another stage.`,
        isError: true,
      };
    }

    const pipeline = new SubagentPipeline(task, stages);
    const result = await pipeline.execute(signal);
    return result;
  },
};

/**
 * The stages a call describes: the ones given, or a single stage built from
 * the task.
 *
 * Exported so the shorthand can be tested without spawning an agent - the
 * default runner makes real model calls, which a test suite has no business
 * doing.
 */
export function stagesFor(params: Record<string, unknown>): StageConfig[] {
  const given = params["stages"] as StageConfig[] | undefined;
  if (given && given.length > 0) return given;
  return [{
    name: "main",
    role: (params["role"] as string) ?? "kiro_default",
    prompt_template: "{task}",
  }];
}

// ── Types ──────────────────────────────────────────────────────────────────

interface StageConfig {
  name: string;
  role: string;
  prompt_template: string;
  depends_on?: string[];
  model?: string;
}

interface StageResult {
  name: string;
  status: "pending" | "running" | "complete" | "failed" | "skipped";
  output?: string;
  error?: string;
  duration_ms?: number;
}

// ── Pipeline executor ──────────────────────────────────────────────────────

export class SubagentPipeline extends EventEmitter {
  private task: string;
  private stages: StageConfig[];
  private results = new Map<string, StageResult>();
  private runStage: StageRunner;

  constructor(task: string, stages: StageConfig[], runStage: StageRunner = runStageWithRuntime) {
    super();
    this.task = task;
    this.stages = stages;
    this.runStage = runStage;
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
        const icon = r.status === "complete" ? "✓" : r.status === "failed" ? "✗" : r.status === "skipped" ? "-" : "○";
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
    const startMs = Date.now();

    // Running a stage whose input never arrived produces confident nonsense:
    // the prompt asks it to build on a plan that does not exist, so it invents
    // one. Skip instead, and say which upstream stage is responsible.
    const brokenDeps = (stage.depends_on ?? []).filter((d) => {
      const s = this.results.get(d)?.status;
      return s === "failed" || s === "skipped";
    });
    if (brokenDeps.length > 0) {
      result.status = "skipped";
      result.error = `did not run: depends on ${brokenDeps.join(", ")}, which did not succeed`;
      result.duration_ms = 0;
      return;
    }

    result.status = "running";

    try {
      if (signal?.aborted) throw new Error("cancelled before the stage started");

      const prompt = stage.prompt_template.replace(/\{task\}/g, this.task);

      // Each stage starts with no memory of the others, so anything it needs
      // has to be passed in explicitly.
      const depContext: string[] = [];
      for (const dep of stage.depends_on ?? []) {
        const depResult = this.results.get(dep);
        if (depResult?.output) depContext.push(`[${dep} output]:\n${depResult.output}`);
      }
      const fullPrompt = depContext.length > 0
        ? `${prompt}\n\nContext from previous stages:\n${depContext.join("\n\n")}`
        : prompt;

      const output = await this.runStage(stage, fullPrompt, signal);

      result.output = output.trim() || `Stage '${stage.name}' finished without producing any text.`;
      result.status = "complete";
    } catch (err) {
      result.status = "failed";
      result.error = err instanceof Error ? err.message : String(err);
    }
    result.duration_ms = Date.now() - startMs;
  }
}

/**
 * Config for one stage, split out so the two decisions it encodes can be
 * tested without spawning an agent.
 */
export function stageConfig<T extends Record<string, any>>(
  stage: StageConfig,
  config: T,
  model: string,
): T {
  return {
    ...config,
    model,
    // A stage that loops burns the user's tokens with nobody watching, so it
    // gets a tighter budget than an interactive turn.
    maxTurns: Math.min(config["maxTurns"] ?? STAGE_MAX_TURNS, STAGE_MAX_TURNS),
    // Enforce the role rather than asking for it. A planning stage that can
    // write files will write files - one did, in a live run - and the pipeline
    // then builds on work that happened in the wrong order.
    permissionMode: READ_ONLY_ROLES.has(stage.role) ? "plan" : config["permissionMode"],
  };
}

/**
 * Run one stage as a nested agent.
 *
 * This is the default StageRunner. It was previously a stub that echoed the
 * prompt back and reported the stage complete, so the pipeline claimed work it
 * had never done. Each stage now gets its own AgentRuntime - own context, own
 * dispatcher - and returns whatever text that agent produced.
 */
async function runStageWithRuntime(
  stage: StageConfig,
  prompt: string,
  signal?: AbortSignal,
): Promise<string> {
  const config = loadConfig();
  const model = stage.model ?? config.model ?? "auto";

  const runtime = new AgentRuntime({
    config: stageConfig(stage, config, model),
    model: createModelClientAuto(model),
  });

  // Without this a stage can spawn its own pipeline, and each of those can
  // spawn more. There is no depth counter anywhere in the loop, so the only
  // safe answer is one level.
  runtime.dispatcher.denyBuiltInTool("subagent");

  runtime.context.setSystemPrompt(
    `${ROLE_PROMPTS[stage.role] ?? ROLE_PROMPTS["kiro_default"]!}\n\n` +
    `Working directory: ${config.workingDir ?? process.cwd()}\n` +
    `You are one stage ("${stage.name}") of a larger pipeline. Complete only this ` +
    `stage, then stop. End with a short summary of what you produced, because ` +
    `that summary is the only thing later stages will see.`,
  );

  let output = "";
  runtime.events.on("text", (event: AgentEvent) => {
    if (event.type === "text" && event.content) output += event.content;
  });

  await runtime.run(prompt, { signal });
  return output;
}
