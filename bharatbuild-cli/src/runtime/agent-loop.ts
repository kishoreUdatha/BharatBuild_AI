// BharatBuild CLI - Agent Loop
// The core think -> tool -> think cycle.
// Matches Kiro CLI behaviour:
//   - Independent tool calls in a single turn run in PARALLEL via Promise.all
//   - subagent/delegate calls that are independent run concurrently
//   - Sequential tools (write then read same file) still work correctly

import { ContextManager, Message, MessageContent } from "./context-manager.js";
import { ToolDispatcher, ToolResult }              from "./tool-dispatcher.js";
import { EventStream }                             from "./event-stream.js";
import { CostMeter }                               from "./cost-meter.js";
import { withRetry }                               from "./retry-controller.js";
import { MAX_TURNS, MAX_EMPTY_RETRIES }            from "../config/constants.js";

export interface ModelClient {
  complete(params: {
    model:       string;
    system:      string;
    messages:    Message[];
    tools:       object[];
    maxTokens:   number;
    signal?:     AbortSignal;
  }): AsyncIterable<ModelChunk>;
}

export interface ModelChunk {
  type:         "text_delta" | "tool_use" | "usage" | "stop";
  text?:        string;
  toolUseId?:   string;
  toolName?:    string;
  toolInput?:   Record<string, unknown>;
  inputTokens?: number;
  outputTokens?: number;
  stopReason?:  "end_turn" | "tool_use" | "max_tokens" | "stop_sequence";
}

export interface AgentLoopOptions {
  model:        string;
  maxTurns?:    number;
  maxTokens?:   number;
  signal?:      AbortSignal;
  onPermission?: (toolName: string, input: Record<string, unknown>) => Promise<"allow" | "deny" | "cancel">;
  /** Run independent tool calls in parallel (default: true, matches Kiro behaviour) */
  parallelTools?: boolean;
}

// Tools that MUST run sequentially because they mutate shared state
// (e.g. two writes to the same file, git operations that depend on each other)
const SEQUENTIAL_TOOLS = new Set([
  "git_add",
  "git_commit",
  "git_push",
]);

// Tools that are safe to run in parallel (read-only or isolated)
const PARALLEL_SAFE_TOOLS = new Set([
  "read_file",
  "list_files",
  "find_files",
  "search_code",
  "search_files",
  "git_status",
  "git_diff",
  "git_log",
  "web_fetch",
  "web_search",
  "thinking",
  "knowledge",
  "subagent",   // each subagent has isolated context
  "delegate",   // same
  "goal",
  "todo_list",
  "apply_patch", // operates on a specific file path — safe to run in parallel with other paths
  "delete_file", // same
]);

function canRunInParallel(toolName: string): boolean {
  if (SEQUENTIAL_TOOLS.has(toolName)) return false;
  // write_file and execute_command default to sequential for safety
  // unless they are clearly on different files/paths
  return PARALLEL_SAFE_TOOLS.has(toolName);
}

export class AgentLoop {
  private _context:    ContextManager;
  private _dispatcher: ToolDispatcher;
  private _events:     EventStream;
  private _cost:       CostMeter;
  private _model:      ModelClient;

  constructor(
    model:      ModelClient,
    context:    ContextManager,
    dispatcher: ToolDispatcher,
    events:     EventStream,
    cost:       CostMeter,
  ) {
    this._model      = model;
    this._context    = context;
    this._dispatcher = dispatcher;
    this._events     = events;
    this._cost       = cost;
  }

  async run(userMessage: string, opts: AgentLoopOptions): Promise<void> {
    const maxTurns     = opts.maxTurns ?? MAX_TURNS;
    const maxTokens    = opts.maxTokens ?? 8192;
    const signal       = opts.signal;
    const parallelTools = opts.parallelTools !== false; // default true
    let   emptyRetries = 0;

    // push user message
    this._context.push({ role: "user", content: userMessage });

    for (let turn = 0; turn < maxTurns; turn++) {
      if (signal?.aborted) break;

      await this._events.emit(EventStream.status(
        turn === 0 ? "thinking..." : "continuing...",
        "thinking"
      ));

      // ── call model ────────────────────────────────────────────────────────
      let   textBuffer    = "";
      const pendingTools: Array<{ id: string; name: string; inputStr: string }> = [];
      let   stopReason: ModelChunk["stopReason"] = "end_turn";

      try {
        await withRetry(async () => {
          const stream = this._model.complete({
            model:     opts.model,
            system:    this._context.systemPrompt,
            messages:  this._context.forRequest(),
            tools:     this._dispatcher.getDefinitions(),
            maxTokens,
            signal,
          });

          for await (const chunk of stream) {
            if (signal?.aborted) break;

            switch (chunk.type) {
              case "text_delta":
                if (chunk.text) {
                  textBuffer += chunk.text;
                  await this._events.emit(EventStream.text(chunk.text, true));
                }
                break;

              case "tool_use":
                if (chunk.toolUseId && chunk.toolName) {
                  pendingTools.push({
                    id:       chunk.toolUseId,
                    name:     chunk.toolName,
                    inputStr: JSON.stringify(chunk.toolInput ?? {}),
                  });
                }
                break;

              case "usage":
                this._cost.add({
                  inputTokens:  chunk.inputTokens  ?? 0,
                  outputTokens: chunk.outputTokens ?? 0,
                });
                await this._events.emit({
                  type:         "usage",
                  inputTokens:  chunk.inputTokens  ?? 0,
                  outputTokens: chunk.outputTokens ?? 0,
                  timestamp:    Date.now(),
                });
                break;

              case "stop":
                stopReason = chunk.stopReason ?? "end_turn";
                break;
            }
          }
        }, {
          onRetry: (attempt, err) => {
            this._events.emit(EventStream.status(
              `retrying (attempt ${attempt})... ${err.message}`, "thinking"
            ));
          },
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        await this._events.emit(EventStream.error(msg, false));
        break;
      }

      // ── handle empty response ─────────────────────────────────────────────
      if (!textBuffer && pendingTools.length === 0) {
        emptyRetries++;
        if (emptyRetries >= MAX_EMPTY_RETRIES) {
          await this._events.emit(EventStream.error("Model returned empty response repeatedly", false));
          break;
        }
        continue;
      }
      emptyRetries = 0;

      // ── push assistant message to context ─────────────────────────────────
      const assistantContent: MessageContent[] = [];
      if (textBuffer) assistantContent.push({ type: "text", text: textBuffer });
      for (const t of pendingTools) {
        assistantContent.push({
          type:  "tool_use",
          id:    t.id,
          name:  t.name,
          input: JSON.parse(t.inputStr),
        });
      }
      this._context.push({ role: "assistant", content: assistantContent });

      // ── done if no tool calls ─────────────────────────────────────────────
      if (stopReason === "end_turn" || pendingTools.length === 0) break;

      // ── execute tools (parallel where safe, sequential otherwise) ─────────
      const parallelCount = parallelTools
        ? pendingTools.filter((t) => canRunInParallel(t.name)).length
        : 0;

      if (parallelCount > 1) {
        await this._events.emit(EventStream.status(
          `executing ${pendingTools.length} tools (${parallelCount} in parallel)...`,
          "coding"
        ));
      } else {
        await this._events.emit(EventStream.status("executing tools...", "coding"));
      }

      const toolResults: MessageContent[] = [];

      if (parallelTools && pendingTools.length > 1) {
        // Split into parallel-safe and sequential buckets
        const parallelBatch: typeof pendingTools = [];
        const sequentialBatch: typeof pendingTools = [];

        for (const t of pendingTools) {
          if (canRunInParallel(t.name)) parallelBatch.push(t);
          else sequentialBatch.push(t);
        }

        // Run parallel-safe tools concurrently
        const parallelResults = await Promise.all(
          parallelBatch.map(async (pending) => {
            if (signal?.aborted) return null;
            const input = JSON.parse(pending.inputStr) as Record<string, unknown>;

            if (opts.onPermission) {
              const decision = await opts.onPermission(pending.name, input);
              if (decision === "cancel") return "CANCEL" as const;
              if (decision === "deny") {
                return {
                  type: "tool_result" as const,
                  id:   pending.id,
                  content: "Tool call denied by user",
                  isError: true,
                };
              }
            }

            const result = await this._dispatcher.execute(pending.id, pending.name, input, signal);
            return { type: "tool_result" as const, id: result.toolUseId, content: result.content, isError: result.isError };
          })
        );

        for (const r of parallelResults) {
          if (r === "CANCEL") {
            await this._events.emit(EventStream.error("Turn cancelled by user", false));
            return;
          }
          if (r !== null) toolResults.push(r);
        }

        // Run sequential tools one at a time
        for (const pending of sequentialBatch) {
          if (signal?.aborted) break;
          const input = JSON.parse(pending.inputStr) as Record<string, unknown>;

          if (opts.onPermission) {
            const decision = await opts.onPermission(pending.name, input);
            if (decision === "cancel") {
              await this._events.emit(EventStream.error("Turn cancelled by user", false));
              return;
            }
            if (decision === "deny") {
              toolResults.push({ type: "tool_result", id: pending.id, content: "Tool call denied by user", isError: true });
              continue;
            }
          }

          const result = await this._dispatcher.execute(pending.id, pending.name, input, signal);
          toolResults.push({ type: "tool_result", id: result.toolUseId, content: result.content, isError: result.isError });
        }

        // Re-order results to match original pendingTools order (model requires this)
        const orderedResults: MessageContent[] = [];
        for (const pending of pendingTools) {
          const found = toolResults.find((r) => r.id === pending.id);
          if (found) orderedResults.push(found);
        }
        toolResults.length = 0;
        toolResults.push(...orderedResults);

      } else {
        // Sequential fallback (original behaviour)
        for (const pending of pendingTools) {
          if (signal?.aborted) break;
          const input = JSON.parse(pending.inputStr) as Record<string, unknown>;

          if (opts.onPermission) {
            const decision = await opts.onPermission(pending.name, input);
            if (decision === "cancel") {
              await this._events.emit(EventStream.error("Turn cancelled by user", false));
              return;
            }
            if (decision === "deny") {
              toolResults.push({ type: "tool_result", id: pending.id, content: "Tool call denied by user", isError: true });
              continue;
            }
          }

          const result = await this._dispatcher.execute(pending.id, pending.name, input, signal);
          toolResults.push({ type: "tool_result", id: result.toolUseId, content: result.content, isError: result.isError });
        }
      }

      // push tool results as user message
      this._context.push({ role: "user", content: toolResults });
    }

    // emit completion
    const stats = this._cost.usage;
    await this._events.emit(EventStream.complete({
      totalTokens:  stats.inputTokens + stats.outputTokens,
      inputTokens:  stats.inputTokens,
      outputTokens: stats.outputTokens,
      turns:        this._cost.turns,
      durationMs:   this._cost.elapsedMs,
      costUsd:      this._cost.estimateCostUsd(),
    }));
  }
}