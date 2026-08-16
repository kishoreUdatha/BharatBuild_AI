/** BharatBuild CLI - Bug Fix Agent
 *
 * Structured bug investigation and resolution.
 * Mirrors Kiro CLI's Bug Fix agent:
 *   Phase 1: Root Cause Analysis  — read-only investigation
 *   Phase 2: Fix Design           — plan the fix
 *   Phase 3: Implementation       — apply the fix
 */
import type { ModelClient } from "../runtime/agent-loop.js";
import { ContextManager } from "../runtime/context-manager.js";
import { ToolDispatcher, type ToolResult } from "../runtime/tool-dispatcher.js";
import { EventStream } from "../runtime/event-stream.js";
import { CostMeter } from "../runtime/cost-meter.js";
import { AgentLoop } from "../runtime/agent-loop.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto } from "../models/model-router.js";

// ── Phase 1: Read-only RCA dispatcher ─────────────────────────────────────

const WRITE_TOOLS = new Set(["write_file", "execute_command", "git_add", "git_commit"]);

class RCAToolDispatcher extends ToolDispatcher {
  override getDefinitions(): object[] {
    return super.getDefinitions().filter((d) => !WRITE_TOOLS.has((d as { name: string }).name));
  }
  override async execute(toolUseId: string, toolName: string, input: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult> {
    if (WRITE_TOOLS.has(toolName)) {
      return { toolUseId, content: `'${toolName}' is blocked during root cause analysis phase.`, isError: true };
    }
    return super.execute(toolUseId, toolName, input, signal);
  }
}

// ── BugFixAgent ────────────────────────────────────────────────────────────

export interface BugFixResult {
  rootCause: string;
  fixDesign: string;
  implemented: boolean;
}

export class BugFixAgent {
  readonly events: EventStream;
  private model: ModelClient;
  private modelId: string;

  constructor(model?: ModelClient, modelId?: string) {
    const config = loadConfig();
    this.modelId = modelId ?? config.model ?? "auto";
    this.model = model ?? createModelClientAuto(this.modelId);
    this.events = new EventStream();
  }

  async fix(bugDescription: string, opts?: { maxTurns?: number; skipApproval?: boolean }): Promise<BugFixResult> {
    const maxTurns = opts?.maxTurns ?? 15;

    // ── Phase 1: Root Cause Analysis (read-only) ───────────────────────────
    await this.events.emit({ type: "status", message: "Phase 1: Root cause analysis…", phase: "thinking", timestamp: Date.now() });
    console.log("\n  🔍 Phase 1: Root Cause Analysis (read-only)\n");

    const rcaContext = new ContextManager();
    rcaContext.setSystemPrompt(
      "You are a debugging expert. Analyze bugs systematically.\n" +
      "You are in READ-ONLY mode — explore files and code to find root causes.\n" +
      "Do NOT write any files or run any commands.\n" +
      "End your analysis with a clear summary:\n" +
      "ROOT CAUSE: [one clear sentence]\n" +
      "AFFECTED FILES: [list]\n" +
      "FIX APPROACH: [brief description]"
    );
    const rcaDispatcher = new RCAToolDispatcher(this.events, this.model);
    const rcaCost = new CostMeter(this.modelId);
    const rcaLoop = new AgentLoop(this.model, rcaContext, rcaDispatcher, this.events, rcaCost);

    let rootCauseOutput = "";
    this.events.on("text", (e) => { if (e.type === "text") rootCauseOutput += e.content; });

    await rcaLoop.run(
      `Investigate this bug:\n\n${bugDescription}\n\n` +
      `Read relevant files, trace the execution path, and identify the root cause. ` +
      `Do NOT make any changes yet.`,
      { model: this.modelId, maxTurns: Math.floor(maxTurns / 3) }
    );

    console.log(`\n  Root cause analysis complete.\n`);

    // ── Phase 2: Fix Design ────────────────────────────────────────────────
    await this.events.emit({ type: "status", message: "Phase 2: Designing fix…", phase: "planning", timestamp: Date.now() });
    console.log("  📐 Phase 2: Fix Design\n");

    const designContext = new ContextManager();
    designContext.setSystemPrompt(
      "You are a debugging expert. Based on the root cause analysis, " +
      "design the minimal fix that resolves the bug without breaking existing functionality.\n" +
      "Output a fix plan:\n" +
      "FIX PLAN:\n" +
      "1. [File to change]: [What to change and why]\n" +
      "2. ...\n" +
      "RISK ASSESSMENT: [What could go wrong]\n" +
      "TESTING: [How to verify the fix]"
    );
    const designDispatcher = new RCAToolDispatcher(this.events, this.model);
    const designCost = new CostMeter(this.modelId);
    const designLoop = new AgentLoop(this.model, designContext, designDispatcher, this.events, designCost);

    let fixDesignOutput = "";
    this.events.on("text", (e) => { if (e.type === "text") fixDesignOutput += e.content; });

    await designLoop.run(
      `Root cause analysis:\n${rootCauseOutput}\n\n` +
      `Original bug: ${bugDescription}\n\n` +
      `Design the minimal fix. List exact files and changes needed.`,
      { model: this.modelId, maxTurns: Math.floor(maxTurns / 3) }
    );

    console.log(`\n  Fix design complete.\n`);

    // ── Phase 3: Implementation ────────────────────────────────────────────
    await this.events.emit({ type: "status", message: "Phase 3: Implementing fix…", phase: "coding", timestamp: Date.now() });
    console.log("  🔧 Phase 3: Implementation\n");

    const implContext = new ContextManager();
    implContext.setSystemPrompt(
      "You are a debugging expert implementing a planned fix.\n" +
      "Apply the fix exactly as designed. After implementing:\n" +
      "1. Verify the fix by reading the changed files\n" +
      "2. Run any relevant tests\n" +
      "3. Confirm the bug is resolved\n" +
      "Be minimal — only change what is needed to fix the bug."
    );
    const implDispatcher = new ToolDispatcher(this.events, this.model);
    const implCost = new CostMeter(this.modelId);
    const implLoop = new AgentLoop(this.model, implContext, implDispatcher, this.events, implCost);

    await implLoop.run(
      `Implement this fix:\n\n${fixDesignOutput}\n\n` +
      `Original bug: ${bugDescription}\n` +
      `Root cause: ${rootCauseOutput.slice(0, 500)}\n\n` +
      `Apply the minimal fix, then verify it works.`,
      { model: this.modelId, maxTurns: Math.floor(maxTurns / 3) }
    );

    console.log(`\n  ✓ Bug fix complete.\n`);

    return {
      rootCause: rootCauseOutput,
      fixDesign: fixDesignOutput,
      implemented: true,
    };
  }
}