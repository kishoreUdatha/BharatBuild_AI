/** BharatBuild CLI - Anthropic Provider (Claude) */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import { toWireMessages } from "../wire-format.js";
import type { Message, MessageContent } from "../../runtime/context-manager.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";
import { thinkingFor, configuredLevel, effortFor } from "../thinking-config.js";

const API_URL = "https://api.anthropic.com/v1/messages";
const API_VERSION = "2023-06-01";

/** A tool_use block being assembled across streaming events, keyed by block index. */
interface PendingBlock {
  id: string;
  name: string;
  json: string;
}

// Wire translation lives in ../wire-format.js so the proxy client shares it.

export class AnthropicProvider extends BaseModelProvider {
  constructor(config: ModelProviderConfig) { super(config); }

  async *complete(params: {
    model: string;
    system: string;
    messages: unknown[];
    tools: object[];
    maxTokens: number;
    signal?: AbortSignal;
  }): AsyncIterable<ModelChunk> {
    const apiKey = this.config.apiKey ?? process.env["ANTHROPIC_API_KEY"];
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set");

    const body: Record<string, unknown> = {
      model: params.model,
      system: params.system,
      messages: toWireMessages(params.messages),
      max_tokens: params.maxTokens,
      stream: true,
    };
    // An empty tools array is rejected; omit the key entirely when there are none.
    if (params.tools.length > 0) body["tools"] = params.tools;

    // Native extended thinking, when the model takes it and it is switched on.
    // Omitted rather than disabled: the API rejects the parameter outright on
    // models that do not support it.
    const level = configuredLevel();
    const thinking = thinkingFor(params.model, level, params.maxTokens);
    if (thinking) body["thinking"] = thinking;
    // Claude 5 pairs adaptive thinking with an effort level rather than a
    // token budget; sending a budget to it is a 400.
    const effort = effortFor(params.model, level);
    if (effort) body["output_config"] = effort;

    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": API_VERSION,
      },
      body: JSON.stringify(body),
      signal: params.signal,
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const e = await res.json() as { error?: { message?: string } };
        if (e.error?.message) detail = e.error.message;
      } catch { /* non-JSON error body */ }
      throw new Error(`Anthropic API error (${res.status}): ${detail}`);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    // Tool calls arrive across three events: content_block_start carries the id
    // and name, input_json_delta streams the arguments as JSON text fragments,
    // and content_block_stop marks the block complete. We assemble per index
    // because blocks for parallel tool calls interleave.
    const pending = new Map<number, PendingBlock>();
    /** Indices currently carrying a thinking block. */
    const thinkingBlocks = new Set<number>();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";

      for (const part of parts) {
        const dataLine = part.split("\n").find((l) => l.startsWith("data: "))?.slice(6);
        if (!dataLine || dataLine === "[DONE]") continue;

        let ev: Record<string, unknown>;
        try {
          ev = JSON.parse(dataLine) as Record<string, unknown>;
        } catch {
          continue; // skip malformed frame
        }

        switch (ev["type"] as string) {
          case "message_start": {
            const u = (ev["message"] as Record<string, unknown>)?.["usage"] as Record<string, unknown> | undefined;
            if (u) {
              yield {
                type: "usage",
                inputTokens: Number(u["input_tokens"] ?? 0),
                outputTokens: Number(u["output_tokens"] ?? 0),
              };
            }
            break;
          }

          case "content_block_start": {
            const index = Number(ev["index"] ?? 0);
            const block = ev["content_block"] as Record<string, unknown> | undefined;
            if (block?.["type"] === "thinking") {
              // Its deltas arrive against this index as thinking_delta events.
              thinkingBlocks.add(index);
            } else if (block?.["type"] === "tool_use") {
              pending.set(index, {
                id: String(block["id"] ?? ""),
                name: String(block["name"] ?? ""),
                json: "",
              });
            }
            break;
          }

          case "content_block_delta": {
            const index = Number(ev["index"] ?? 0);
            const delta = ev["delta"] as Record<string, unknown>;

            if (delta["type"] === "text_delta") {
              yield { type: "text_delta", text: String(delta["text"] ?? "") };
            } else if (delta["type"] === "thinking_delta") {
              // Its own chunk type, not text: reasoning is displayed
              // differently and must never be concatenated into the reply.
              yield { type: "thinking_delta", text: String(delta["thinking"] ?? "") };
            } else if (delta["type"] === "signature_delta") {
              // Authenticates the block when it is sent back on a later turn.
              yield { type: "thinking_signature", text: String(delta["signature"] ?? "") };
            } else if (delta["type"] === "input_json_delta") {
              // Accumulate; the fragments are only valid JSON once concatenated.
              const block = pending.get(index);
              if (block) block.json += String(delta["partial_json"] ?? "");
            }
            break;
          }

          case "content_block_stop": {
            const index = Number(ev["index"] ?? 0);
            const block = pending.get(index);
            if (!block) break;
            pending.delete(index);

            let input: Record<string, unknown> = {};
            // A tool called with no arguments streams no deltas at all, leaving
            // an empty string rather than "{}".
            if (block.json.trim()) {
              try {
                input = JSON.parse(block.json) as Record<string, unknown>;
              } catch {
                // Emit anyway with the raw text so the dispatcher can report a
                // usable error instead of the call vanishing silently.
                input = { __malformed_input: block.json };
              }
            }

            yield {
              type: "tool_use",
              toolUseId: block.id,
              toolName: block.name,
              toolInput: input,
            };
            break;
          }

          case "message_delta": {
            const d = ev["delta"] as Record<string, unknown> | undefined;
            const u = ev["usage"] as Record<string, unknown> | undefined;
            // Final output token count only appears here, not in message_start.
            if (u && u["output_tokens"] !== undefined) {
              yield { type: "usage", inputTokens: 0, outputTokens: Number(u["output_tokens"]) };
            }
            if (d?.["stop_reason"]) {
              yield { type: "stop", stopReason: d["stop_reason"] as ModelChunk["stopReason"] };
            }
            break;
          }

          case "error": {
            const e = ev["error"] as Record<string, unknown> | undefined;
            throw new Error(`Anthropic stream error: ${String(e?.["message"] ?? "unknown")}`);
          }
        }
      }
    }
  }
}
