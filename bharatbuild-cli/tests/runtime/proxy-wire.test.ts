/**
 * Regression tests for the bugs that made the agent announce work and then do
 * nothing: the proxy client's wire format did not match what the backend
 * actually sends, so tool calls were dropped and usage was never recorded.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { ProxyModelClient } from "../../src/api/proxy-model.js";
import { toWireMessages, toWireContent } from "../../src/models/wire-format.js";

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

/** Serve a canned SSE body shaped exactly like the real backend's. */
function serveSSE(events: unknown[]) {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
  globalThis.fetch = vi.fn(async () =>
    new Response(new TextEncoder().encode(body), {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }),
  ) as any;
}

async function collect(client: ProxyModelClient) {
  const out: any[] = [];
  for await (const chunk of client.complete({
    model: "auto", system: "s", messages: [], tools: [], maxTokens: 100,
  })) out.push(chunk);
  return out;
}

const client = () => new ProxyModelClient("http://x", "token");

describe("proxy stream parsing", () => {
  it("reads a tool call nested under `tool`", async () => {
    // Backend sends {"type":"tool_use","tool":{id,name,input}}. The client only
    // looked at flat tool_use_id/tool_name, so every call was silently dropped
    // and the agent stopped after its preamble.
    serveSSE([
      { type: "text_delta", text: "I'll create it." },
      { type: "tool_use", tool: { id: "toolu_1", name: "write_file", input: { path: "a.txt", content: "hi" } } },
      { type: "done", stop_reason: "tool_use", usage: { input_tokens: 10, output_tokens: 5 } },
    ]);

    const chunks = await collect(client());
    const tool = chunks.find((c) => c.type === "tool_use");
    expect(tool).toBeDefined();
    expect(tool.toolUseId).toBe("toolu_1");
    expect(tool.toolName).toBe("write_file");
    expect(tool.toolInput).toEqual({ path: "a.txt", content: "hi" });
  });

  it("still reads the flat alias shape", async () => {
    serveSSE([
      { type: "tool_use", tool_use_id: "t2", tool_name: "read_file", tool_input: { path: "b" } },
      { type: "done", stop_reason: "tool_use" },
    ]);
    const tool = (await collect(client())).find((c) => c.type === "tool_use");
    expect(tool.toolUseId).toBe("t2");
    expect(tool.toolName).toBe("read_file");
  });

  it("reports usage from the terminal done event", async () => {
    // "done" was unhandled, so every session showed tokens: 0 / turns: 0.
    serveSSE([
      { type: "text_delta", text: "hi" },
      { type: "done", stop_reason: "end_turn", usage: { input_tokens: 1475, output_tokens: 93 } },
    ]);
    const usage = (await collect(client())).find((c) => c.type === "usage");
    expect(usage).toBeDefined();
    expect(usage.inputTokens).toBe(1475);
    expect(usage.outputTokens).toBe(93);
  });

  it("propagates the tool_use stop reason so the loop keeps going", async () => {
    serveSSE([
      { type: "tool_use", tool: { id: "t", name: "write_file", input: {} } },
      { type: "done", stop_reason: "tool_use", usage: {} },
    ]);
    const stop = (await collect(client())).find((c) => c.type === "stop");
    expect(stop.stopReason).toBe("tool_use");
  });

  it("falls back to end_turn for an unrecognised stop reason", async () => {
    serveSSE([{ type: "done", stop_reason: "something_new" }]);
    const stop = (await collect(client())).find((c) => c.type === "stop");
    expect(stop.stopReason).toBe("end_turn");
  });

  it("does not emit a call twice when done repeats it", async () => {
    serveSSE([
      { type: "tool_use", tool: { id: "dup", name: "write_file", input: {} } },
      { type: "done", stop_reason: "tool_use", tool_calls: [{ id: "dup", name: "write_file", input: {} }] },
    ]);
    const calls = (await collect(client())).filter((c) => c.type === "tool_use");
    expect(calls).toHaveLength(1);
  });

  it("recovers calls that only appear in done", async () => {
    serveSSE([
      { type: "done", stop_reason: "tool_use", tool_calls: [{ id: "only", name: "read_file", input: { path: "p" } }] },
    ]);
    const calls = (await collect(client())).filter((c) => c.type === "tool_use");
    expect(calls).toHaveLength(1);
    expect(calls[0].toolUseId).toBe("only");
  });

  it("streams text deltas in order", async () => {
    serveSSE([
      { type: "text_delta", text: "Hello " },
      { type: "text_delta", text: "world" },
      { type: "done", stop_reason: "end_turn" },
    ]);
    const text = (await collect(client())).filter((c) => c.type === "text_delta").map((c) => c.text).join("");
    expect(text).toBe("Hello world");
  });
});

describe("wire format translation", () => {
  it("maps tool_result id to tool_use_id", () => {
    // The proxy sent the internal shape straight through, so the turn after a
    // tool call was malformed and the model replied with nothing.
    const wire = toWireContent({ type: "tool_result", id: "toolu_9", content: "ok" } as any);
    expect(wire).toMatchObject({ type: "tool_result", tool_use_id: "toolu_9", content: "ok" });
    expect(wire).not.toHaveProperty("id");
  });

  it("only sends is_error when the result actually failed", () => {
    expect(toWireContent({ type: "tool_result", id: "a", content: "x" } as any)).not.toHaveProperty("is_error");
    expect(toWireContent({ type: "tool_result", id: "a", content: "x", isError: true } as any))
      .toHaveProperty("is_error", true);
  });

  it("keeps `id` on tool_use blocks, where the API expects it", () => {
    const wire = toWireContent({ type: "tool_use", id: "t1", name: "write_file", input: { a: 1 } } as any);
    expect(wire).toMatchObject({ type: "tool_use", id: "t1", name: "write_file" });
  });

  it("folds a system role into a user turn", () => {
    const [msg] = toWireMessages([{ role: "system", content: "be brief" }]) as any[];
    expect(msg.role).toBe("user");
  });

  it("translates a full tool round trip", () => {
    const wire = toWireMessages([
      { role: "user", content: "make a file" },
      { role: "assistant", content: [
        { type: "text", text: "sure" },
        { type: "tool_use", id: "t1", name: "write_file", input: { path: "a" } },
      ] },
      { role: "user", content: [{ type: "tool_result", id: "t1", content: "written" }] },
    ]) as any[];
    expect(wire[2].content[0]).toMatchObject({ type: "tool_result", tool_use_id: "t1" });
  });
});
