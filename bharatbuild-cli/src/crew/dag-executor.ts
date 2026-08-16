/**
 * BharatBuild CLI - DAG Task Executor
 *
 * Implements Kiro CLI's parallel execution model:
 *   - Tasks defined as a DAG (directed acyclic graph) with dependencies
 *   - Independent tasks run in parallel via Promise.all
 *   - Dependent tasks wait for their prerequisites
 *   - Review loops: stage A -> stage B -> loop back to A if output contains trigger text
 *
 * Matches Kiro CLI's subagent pipeline exactly.
 */

import { AgentRuntime } from "../runtime/agent-runtime.js";
import { createModelClientAuto } from "../models/model-router.js";
import { loadConfig } from "../config/config.js";
import type { AgentEvent } from "../runtime/event-stream.js";

// ── Types ──────────────────────────────────────────────────────────────────

export interface DAGStage {
  name: string;
  task: string;
  agent?: string;         // agent role: default | planner | coder | tester | fixer | reviewer
  model?: string;
  depends_on?: string[];  // names of stages that must complete before this one starts
  loop_to?: {             // review loop config
    target: string;       // stage to re-run when trigger fires
    trigger: string;      // text in output that fires the loop (e.g. "NEEDS_CHANGES")
    max_iterations: number;
  };
}

export type StageStatus = "pending" | "running" | "complete" | "failed" | "skipped";

export interface StageResult {
  name: string;
  status: StageStatus;
  output: string;
  durationMs: number;
  iterations?: number;  // for review loops
  error?: string;
}

export interface DAGPlan {
  stages: DAGStage[];
  onProgress?: (name: string, status: StageStatus, output?: string) => void;
}

export interface DAGResult {
  stages: StageResult[];
  totalDurationMs: number;
  success: boolean;
}

// ── Agent system prompts ───────────────────────────────────────────────────

const AGENT_PROMPTS: Record<string, string> = {
  default:  "You are BharatBuild AI, an expert software engineer. Complete the given task thoroughly.",
  planner:  "You are a senior software architect. Create clear, ordered implementation plans.",
  coder:    "You are an expert software engineer. Write clean, production-quality code.",
  tester:   "You are a QA engineer. Write comprehensive tests and ensure they pass.",
  fixer:    "You are a debugging expert. Identify root causes and apply minimal fixes.",
  reviewer: "You are a code reviewer. Check for bugs, security issues, and quality problems. " +
            "If changes are needed, include 'NEEDS_CHANGES' in your response and describe what to fix.",
};

// ── Stage runner ───────────────────────────────────────────────────────────

async function runStage(
  stage: DAGStage,
  previousResults: Map<string, StageResult>,
  signal?: AbortSignal
): Promise<StageResult> {
  const start = Date.now();

  if (signal?.aborted) {
    return { name: stage.name, status: "skipped", output: "Aborted", durationMs: 0 };
  }

  const config = loadConfig();
  const activeModel = stage.model ?? config.model ?? "auto";
  const modelClient = createModelClientAuto(activeModel);
  const agentRole = stage.agent ?? "default";

  // Build context from dependency outputs
  const depContext = stage.depends_on
    ?.map((dep) => {
      const r = previousResults.get(dep);
      return r ? `--- Output from [${dep}] ---\n${r.output}` : "";
    })
    .filter(Boolean)
    .join("\n\n") ?? "";

  const fullTask = depContext
    ? `${stage.task}\n\n--- Context from previous stages ---\n${depContext}`
    : stage.task;

  const runtime = new AgentRuntime({ config: { ...config, model: activeModel }, model: modelClient });
  const rolePrompt = AGENT_PROMPTS[agentRole] ?? AGENT_PROMPTS["default"]!;
  runtime.context.setSystemPrompt(
    `${rolePrompt}\n\nWorking directory: ${config.workingDir}\n` +
    `You have access to all tools. Complete the task fully, then stop.`
  );

  let output = "";
  runtime.events.on("text", (e: AgentEvent) => {
    if (e.type === "text" && e.content) output += e.content;
  });

  try {
    await runtime.run(fullTask, { signal });
    return {
      name: stage.name,
      status: "complete",
      output,
      durationMs: Date.now() - start,
    };
  } catch (err) {
    return {
      name: stage.name,
      status: "failed",
      output,
      error: err instanceof Error ? err.message : String(err),
      durationMs: Date.now() - start,
    };
  }
}

// ── Review loop runner ─────────────────────────────────────────────────────

/**
 * Run a review-loop pair: targetStage (e.g. "code") and reviewStage (e.g. "review").
 *
 * Iteration contract (matches Kiro CLI):
 *   Iteration 1: run target → run review
 *   If review output contains trigger AND iterations < max_iterations:
 *     re-run target with reviewer feedback, re-run review  (iteration 2, 3, …)
 *   Stop when: review passes OR max_iterations reached.
 *
 * With max_iterations: 3 you get at most 3 target runs and 3 review runs.
 */
async function runStageWithLoop(
  reviewStage: DAGStage,
  targetStage: DAGStage,
  previousResults: Map<string, StageResult>,
  signal?: AbortSignal
): Promise<{ reviewResult: StageResult; targetResult: StageResult }> {
  const { trigger, max_iterations } = reviewStage.loop_to!;

  // Iteration 1: first target run
  let targetResult = await runStage(targetStage, previousResults, signal);
  let reviewResult!: StageResult;

  for (let iteration = 1; iteration <= max_iterations; iteration++) {
    if (signal?.aborted) break;

    // Run the reviewer with the current target output in context
    const reviewCtx = new Map(previousResults);
    reviewCtx.set(targetStage.name, targetResult);
    reviewResult = await runStage(reviewStage, reviewCtx, signal);
    reviewResult.iterations = iteration;

    // Reviewer approved, or we've exhausted iterations — stop
    if (!reviewResult.output.includes(trigger) || iteration >= max_iterations) {
      break;
    }

    // Loop back: re-run the target with reviewer feedback as context
    const loopCtx = new Map(previousResults);
    loopCtx.set(targetStage.name, targetResult);
    loopCtx.set(reviewStage.name, reviewResult);

    const retryTask =
      `${targetStage.task}\n\n` +
      `--- Reviewer feedback (iteration ${iteration}) ---\n` +
      `${reviewResult.output}\n\n` +
      `Address all the reviewer's concerns.`;

    const retryStage: DAGStage = { ...targetStage, task: retryTask };
    targetResult = await runStage(retryStage, loopCtx, signal);
    targetResult.iterations = iteration + 1;
  }

  return { reviewResult, targetResult };
}

// ── Topological sort ───────────────────────────────────────────────────────

function topologicalLayers(stages: DAGStage[]): DAGStage[][] {
  const nameSet = new Set(stages.map((s) => s.name));
  const inDegree = new Map<string, number>();
  const dependents = new Map<string, string[]>(); // name -> who depends on it

  for (const s of stages) {
    inDegree.set(s.name, (s.depends_on ?? []).filter((d) => nameSet.has(d)).length);
    dependents.set(s.name, []);
  }
  for (const s of stages) {
    for (const dep of s.depends_on ?? []) {
      if (nameSet.has(dep)) {
        dependents.get(dep)!.push(s.name);
      }
    }
  }

  const layers: DAGStage[][] = [];
  let ready = stages.filter((s) => inDegree.get(s.name) === 0);

  while (ready.length > 0) {
    layers.push(ready);
    const next: DAGStage[] = [];
    for (const s of ready) {
      for (const dep of dependents.get(s.name) ?? []) {
        const deg = (inDegree.get(dep) ?? 1) - 1;
        inDegree.set(dep, deg);
        if (deg === 0) next.push(stages.find((x) => x.name === dep)!);
      }
    }
    ready = next;
  }

  return layers;
}

// ── Main DAG executor ──────────────────────────────────────────────────────

/**
 * Execute a DAG of stages.
 * - Stages with no dependencies (or whose deps are done) run in parallel.
 * - Stages with review loops use the loop runner.
 * - Results accumulate and are passed as context to dependent stages.
 */
export async function executeDag(plan: DAGPlan, signal?: AbortSignal): Promise<DAGResult> {
  const start = Date.now();
  const results = new Map<string, StageResult>();
  const stageMap = new Map(plan.stages.map((s) => [s.name, s]));

  // Validate loop_to references
  for (const s of plan.stages) {
    if (s.loop_to) {
      if (!stageMap.has(s.loop_to.target)) {
        throw new Error(`Stage "${s.name}" loop_to.target "${s.loop_to.target}" not found`);
      }
      if (s.loop_to.trigger.length < 4) {
        throw new Error(`Stage "${s.name}" loop_to.trigger must be at least 4 characters`);
      }
      if (s.loop_to.max_iterations < 1 || s.loop_to.max_iterations > 10) {
        throw new Error(`Stage "${s.name}" loop_to.max_iterations must be between 1 and 10`);
      }
    }
  }

  // Build a global set of ALL stages that are owned by a loop runner.
  // These stages must NEVER be run by the regular executor — they are
  // exclusively managed inside runStageWithLoop().
  const loopTargets = new Set<string>(
    plan.stages
      .filter((s) => s.loop_to)
      .map((s) => s.loop_to!.target)
  );

  // Get execution layers (parallel groups)
  const layers = topologicalLayers(plan.stages);

  for (const layer of layers) {
    if (signal?.aborted) break;

    // Within each layer, identify review-loop stages vs independent stages.
    // IMPORTANT: exclude loop targets from regularStages — they will be
    // executed (potentially multiple times) inside runStageWithLoop().
    const loopStages    = layer.filter((s) => s.loop_to);
    const regularStages = layer.filter((s) => !s.loop_to && !loopTargets.has(s.name));

    // Run regular stages in parallel
    const regularPromises = regularStages.map(async (stage) => {
      plan.onProgress?.(stage.name, "running");
      const result = await runStage(stage, results, signal);
      results.set(stage.name, result);
      plan.onProgress?.(stage.name, result.status, result.output);
      return result;
    });

    // Run loop stages (reviewer + target, iterated until approval or max_iterations)
    const loopPromises = loopStages.map(async (reviewStage) => {
      const targetName  = reviewStage.loop_to!.target;
      const targetStage = stageMap.get(targetName)!;

      plan.onProgress?.(targetStage.name, "running");
      plan.onProgress?.(reviewStage.name, "pending");

      const { reviewResult, targetResult } = await runStageWithLoop(
        reviewStage, targetStage, results, signal
      );

      results.set(targetStage.name, targetResult);
      results.set(reviewStage.name, reviewResult);
      plan.onProgress?.(targetStage.name, targetResult.status, targetResult.output);
      plan.onProgress?.(reviewStage.name, reviewResult.status, reviewResult.output);
    });

    // Wait for all stages in this layer to complete before advancing
    await Promise.all([...regularPromises, ...loopPromises]);
  }

  const allResults = Array.from(results.values());
  return {
    stages: allResults,
    totalDurationMs: Date.now() - start,
    success: allResults.every((r) => r.status === "complete" || r.status === "skipped"),
  };
}

/**
 * Simple parallel runner — no DAG, just runs all stages concurrently.
 * Used by crew spawn when no dependencies are defined.
 */
export async function executeParallel(
  stages: Omit<DAGStage, "depends_on">[],
  signal?: AbortSignal
): Promise<DAGResult> {
  return executeDag({
    stages: stages.map((s) => ({ ...s, depends_on: [] })),
  }, signal);
}