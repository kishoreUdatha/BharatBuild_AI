/** BharatBuild CLI - Anthropic Provider (Claude) */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import type { Message, MessageContent } from "../../runtime/context-manager.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";

const API_URL = "https://api.anthropic.com/v1/messages";
const API_VERSION = "2023-06-01";

/** A tool_use block being assembled across streaming events, keyed by block index. */
interface PendingBlock {
  id: string;
  name: string;
  json: string;
}

/**
 * Translate our internal message shape to the Anthropic wire format.
 *
 * The internal MessageContent uses `id` and `isError` for every block type;
 * the API expects `tool_use_id` and `is_error` on tool_result specifically.
 * Sending the internal shape through unchanged makes the API reject the turn
 * that follows any tool call, so the mapping has to happen here.
 */
function toWireContent(block: MessageContent): Record<string, unknown> | null {
  switch (block.type) {
    case "text":
      return { type: "text", text: block.text ?? "" };

    case "tool_use":
      return { type: "tool_use", id: block.id, name: block.name, input: block.input ?? {} };

    case "tool_result": {
      const wire: Record<string, unknown> = {
        type: "tool_result",
        tool_use_id: block.id,
        content: typeof block.content === "string" ? block.content : (block.content ?? ""),
      };
      // Only send is_error when true - the API treats presence as meaningful.
      if (block.isError) wire["is_error"] = true;
      return wire;
    }

    default:
      // Image blocks — send as base64 source to Claude Vision
      if (block.type === "image") {
        const b64 = block.imageBase64;
        const mime = block.mimeType ?? "image/png";
        if (b64) {
          return {
            type: "image",
            source: {
              type: "base64",
              media_type: mime,
              data: b64,
            },
          };
        }
      }
      return null;
  }
}

function toWireMessages(messages: unknown[]): unknown[] {
  return (messages as Message[]).map((msg) => {
    // The API has no top-level "system" role in messages; fold it into a user turn.
    const role = msg.role === "system" ? "user" : msg.role;
    if (typeof msg.content === "string") return { role, content: msg.content };
    return { role, content: msg.content.map(toWireContent).filter(Boolean) };
  });
}

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
            if (block?.["type"] === "tool_use") {
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
