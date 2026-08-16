/** BharatBuild CLI - Fixer Agent */
import { getAgent } from "./agent-registry.js";
import type { ModelClient } from "../runtime/agent-loop.js";
import { ContextManager } from "../runtime/context-manager.js";
import { ToolDispatcher } from "../runtime/tool-dispatcher.js";
import { EventStream } from "../runtime/event-stream.js";
import { CostMeter } from "../runtime/cost-meter.js";
import { AgentLoop } from "../runtime/agent-loop.js";
import { loadConfig } from "../config/config.js";

export class FixerAgent {
  private _loop: AgentLoop;
  private _context: ContextManager;
  readonly events: EventStream;

  constructor(model: ModelClient, modelId?: string) {
    const config = loadConfig();
    const resolvedModelId = modelId ?? config.model ?? "auto";
    const agent = getAgent("fixer");
    this.events = new EventStream();
    this._context = new ContextManager();
    this._context.setSystemPrompt(agent.systemPrompt);
    const dispatcher = new ToolDispatcher(this.events, model);
    const cost = new CostMeter(resolvedModelId);
    this._loop = new AgentLoop(model, this._context, dispatcher, this.events, cost);
  }

  async fix(errorOutput: string, opts?: { model?: string; maxTurns?: number }): Promise<void> {
    const config = loadConfig();
    await this._loop.run(
      `Fix the following errors:\n\n${errorOutput}\n\nIdentify root cause, then apply the minimal fix.`,
      { model: opts?.model ?? config.model ?? "auto", maxTurns: opts?.maxTurns ?? 20 }
    );
  }
}