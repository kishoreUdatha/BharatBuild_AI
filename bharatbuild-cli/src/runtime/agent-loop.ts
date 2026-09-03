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
// A refusal must say why. "denied by user" is also wrong for a mode-driven
// deny - nobody was asked - and the model just invents reasons for it.
import { takeDenyReason } from "../permissions/deny-reason.js";
import { takeBackgroundNotices } from "../tools/shell/background.js";

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
  // tool_progress reports that a tool call is being composed. The backend
  // buffered the argument JSON and emitted nothing until the block closed, so
  // writing a large file produced no visible activity for its whole duration —
  // measured at 9s of silence before the first sign anything was happening.
  /**
   * "status" is shown to the user but never becomes part of the reply.
   *
   * The auto-router announced its choice as a text_delta, so the banner
   * "✦ Auto → Claude Haiku 4.5 (moderate, 0.4x)" — ANSI escapes and all — was
   * accumulated into the assistant message and pushed into the conversation.
   * Every model call added one, and every later call re-sent all of them.
   */
  type:         "text_delta" | "thinking_delta" | "thinking_signature" | "status"
              | "tool_use" | "tool_progress" | "usage" | "stop";
  text?:        string;
  toolUseId?:   string;
  toolName?:    string;
  toolInput?:   Record<string, unknown>;
  /** Bytes of tool arguments received so far. tool_progress only. */
  toolBytes?:   number;
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
  /**
   * Content blocks to send ahead of the text — a pasted image, say.
   *
   * Needed because this method always pushes the user message itself. The
   * caller that wanted to attach an image pushed its own combined message
   * first and then called run() anyway, so the model received the attachment
   * and then a duplicate text-only turn right behind it.
   */
  attachments?: MessageContent[];
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
  // glob and grep are the survivors of the duplicate-pair collapse and were
  // missed here, so the two search tools the model actually reaches for ran
  // one at a time. The retired names stay listed: a resumed session or a
  // backend advertising the old spelling still dispatches them.
  "glob",
  "grep",
  "code",          // AST and symbol search - reads only
  "introspect",    // reads bundled documentation
  "read_process_output",  // reads a buffer; starting and stopping stay serial
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

    // push user message, with anything attached to it in front of the text
    this._context.push(
      opts.attachments?.length
        ? { role: "user", content: [...opts.attachments, { type: "text", text: userMessage }] }
        : { role: "user", content: userMessage },
    );

    for (let turn = 0; turn < maxTurns; turn++) {
      if (signal?.aborted) break;

      // A background process that died says so here, without waiting to be
      // asked. The agent only polls when it decides to, so a server that
      // crashes while it is busy editing files would otherwise go unnoticed
      // until something else tripped over it.
      for (const notice of takeBackgroundNotices()) {
        this._context.push({ role: "user", content: notice });
        await this._events.emit(EventStream.status(notice.split("\n")[0] ?? "", "thinking"));
      }

      await this._events.emit(EventStream.status(
        turn === 0 ? "thinking..." : "continuing...",
        "thinking"
      ));

      // ── call model ────────────────────────────────────────────────────────
      let   textBuffer    = "";
      /** Native extended thinking for this turn, and its signature. */
      let   thinkingBuffer = "";
      let   thinkingSignature = "";
      /** Whether an opening <thinking> tag has been emitted and not yet closed. */
      let   thinkingOpen = false;
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
                  // The reply has started, so the reasoning is over.
                  if (thinkingOpen) {
                    thinkingOpen = false;
                    await this._events.emit(EventStream.text("\n</thinking>\n\n", true));
                  }
                  textBuffer += chunk.text;
                  await this._events.emit(EventStream.text(chunk.text, true));
                }
                break;

              // Displayed, not remembered: it is information about the request
              // rather than part of the answer, so it must not reach the
              // context and be charged for again on every later turn.
              // Reasoning, kept apart from the reply. It is accumulated rather
              // than streamed into textBuffer so it cannot end up inside the
              // answer, and it is pushed back to the API with the assistant
              // turn — with tools in play, omitting it is a hard error, not a
              // degradation.
              case "thinking_delta":
                if (chunk.text) {
                  thinkingBuffer += chunk.text;
                  // Wrapped in the tags the renderer already folds, so native
                  // thinking is set apart and dimmed exactly like the inline
                  // kind. Emitted raw it read as the reply itself, and ran
                  // straight into the real answer with no break between them.
                  if (!thinkingOpen) {
                    thinkingOpen = true;
                    await this._events.emit(EventStream.text("<thinking>\n", true));
                  }
                  await this._events.emit(EventStream.text(chunk.text, true));
                }
                break;

              case "thinking_signature":
                if (chunk.text) thinkingSignature = chunk.text;
                break;

              case "status":
                if (chunk.text) await this._events.emit(EventStream.text(chunk.text, true));
                break;

              // Forwarded straight through: the model is still composing the
              // call, so there is nothing to execute yet — only something to
              // show, which is the whole point of the event.
              case "tool_progress":
                if (chunk.toolUseId) {
                  await this._events.emit({
                    type: "tool_progress",
                    id: chunk.toolUseId,
                    toolName: chunk.toolName ?? "",
                    bytes: chunk.toolBytes ?? 0,
                    timestamp: Date.now(),
                  });
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
      if (!textBuffer && !thinkingBuffer && pendingTools.length === 0) {
        emptyRetries++;
        if (emptyRetries >= MAX_EMPTY_RETRIES) {
          await this._events.emit(EventStream.error("Model returned empty response repeatedly", false));
          break;
        }
        continue;
      }
      emptyRetries = 0;

      // A turn can think and then go straight to a tool call without saying
      // anything, so the tag has to be closed here too or it swallows the rest.
      if (thinkingOpen) {
        thinkingOpen = false;
        await this._events.emit(EventStream.text("\n</thinking>\n\n", true));
      }

      // ── push assistant message to context ─────────────────────────────────
      const assistantContent: MessageContent[] = [];
      // Thinking goes first, in the order the API produced it. It has to be
      // sent back verbatim, signature included: the signature is what lets the
      // API verify the block was not edited between turns.
      if (thinkingBuffer) {
        assistantContent.push({
          type: "thinking",
          thinking: thinkingBuffer,
          signature: thinkingSignature,
        });
      }
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

        // Ask about every parallel tool FIRST, one at a time, and only then
        // run them together.
        //
        // Asking inside Promise.all fired every prompt simultaneously. The
        // TUI has a single pending slot, so the second prompt overwrote the
        // first and the first promise never resolved — Promise.all then
        // waited forever and the turn hung with no error and no way out but
        // Ctrl+C. Approval is a conversation with one human; it cannot be
        // parallelised even when the work can.
        const approved: typeof parallelBatch = [];
        const preResults: MessageContent[] = [];
        let cancelled = false;

        for (const pending of parallelBatch) {
          if (signal?.aborted) break;
          const input = JSON.parse(pending.inputStr) as Record<string, unknown>;

          if (opts.onPermission) {
            const decision = await opts.onPermission(pending.name, input);
            if (decision === "cancel") { cancelled = true; break; }
            if (decision === "deny") {
              preResults.push({
                type: "tool_result",
                id: pending.id,
                content: takeDenyReason() ?? "Tool call denied by user.",
                isError: true,
              });
              continue;
            }
          }
          approved.push(pending);
        }

        if (cancelled) {
          await this._events.emit(EventStream.error("Turn cancelled by user", false));
          return;
        }

        const parallelResults: Array<MessageContent | null> = [
          ...preResults,
          ...(await Promise.all(
            approved.map(async (pending) => {
              if (signal?.aborted) return null;
              const input = JSON.parse(pending.inputStr) as Record<string, unknown>;
              const result = await this._dispatcher.execute(pending.id, pending.name, input, signal);
              return { type: "tool_result" as const, id: result.toolUseId, content: result.content, isError: result.isError };
            }),
          )),
        ];

        for (const r of parallelResults) {
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
              toolResults.push({ type: "tool_result", id: pending.id, content: takeDenyReason() ?? "Tool call denied by user.", isError: true });
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
              toolResults.push({ type: "tool_result", id: pending.id, content: takeDenyReason() ?? "Tool call denied by user.", isError: true });
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