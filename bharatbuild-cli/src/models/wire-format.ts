/**
 * Internal message shape → Anthropic wire format.
 *
 * The internal MessageContent uses `id` and `isError` for every block type;
 * the API expects `tool_use_id` and `is_error` on tool_result specifically.
 *
 * This lived only inside the direct Anthropic provider. The proxy client sent
 * `params.messages` through untranslated, so on the proxy path (which is what
 * a logged-in user gets) the turn *after* any tool call carried malformed
 * tool_result blocks — the model could not correlate them to its own call and
 * came back empty, which surfaced as "Model returned empty response
 * repeatedly" right after a tool ran. Both clients now share this one copy.
 */

import type { Message, MessageContent } from "../runtime/context-manager.js";

export function toWireContent(block: MessageContent): Record<string, unknown> | null {
  switch (block.type) {
    case "text":
      return { type: "text", text: block.text ?? "" };

    // Passed through unchanged. With extended thinking and tools together the
    // API requires the thinking blocks of the assistant turn to come back
    // exactly as issued, signature and all — a rewritten or dropped block is
    // rejected outright.
    case "thinking":
      return {
        type: "thinking",
        thinking: block.thinking ?? "",
        signature: block.signature ?? "",
      };

    case "tool_use":
      return { type: "tool_use", id: block.id, name: block.name, input: block.input ?? {} };

    case "tool_result": {
      const wire: Record<string, unknown> = {
        type: "tool_result",
        tool_use_id: block.id,
        content: typeof block.content === "string" ? block.content : (block.content ?? ""),
      };
      // Only send is_error when true — the API treats presence as meaningful.
      if (block.isError) wire["is_error"] = true;
      return wire;
    }

    default:
      if (block.type === "image" && block.imageBase64) {
        return {
          type: "image",
          source: {
            type: "base64",
            media_type: block.mimeType ?? "image/png",
            data: block.imageBase64,
          },
        };
      }
      return null;
  }
}

export function toWireMessages(messages: unknown[]): unknown[] {
  return (messages as Message[]).map((msg) => {
    // The API has no top-level "system" role in messages; fold it into a user turn.
    const role = msg.role === "system" ? "user" : msg.role;
    if (typeof msg.content === "string") return { role, content: msg.content };
    return { role, content: msg.content.map(toWireContent).filter(Boolean) };
  });
}
