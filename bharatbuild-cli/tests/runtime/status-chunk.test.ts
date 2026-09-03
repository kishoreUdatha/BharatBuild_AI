/**
 * A status line is shown, not remembered.
 *
 * The auto-router announced its choice by yielding a `text_delta`, so the
 * banner — `✦ Auto → Claude Haiku 4.5 (moderate, 0.4x)`, ANSI escapes included
 * — was accumulated into the assistant message and pushed into the
 * conversation. Every model call added one, and because each request re-sends
 * the whole history, the cost of them compounded across a session.
 */
import { describe, it, expect } from "vitest";
import { AgentLoop, type ModelChunk } from "../../src/runtime/agent-loop.js";
import { ContextManager } from "../../src/runtime/context-manager.js";
import { EventStream } from "../../src/runtime/event-stream.js";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { CostMeter } from "../../src/runtime/cost-meter.js";

const BANNER = "[2m  ✦ Auto → Claude Haiku 4.5  (moderate, 0.4x)[0m\n";

/** A model that emits a routing banner, then a real answer. */
function modelEmitting(chunks: ModelChunk[]) {
  return {
    async *complete() {
      for (const c of chunks) yield c;
    },
  };
}

function makeLoop(chunks: ModelChunk[]) {
  const context = new ContextManager();
  const events = new EventStream();
  const loop = new AgentLoop(
    modelEmitting(chunks) as any, context, new ToolDispatcher(events), events, new CostMeter("auto"),
  );
  return { loop, context, events };
}

const assistantText = (context: ContextManager): string =>
  context.messages
    .filter((m) => m.role === "assistant")
    .map((m) => (typeof m.content === "string" ? m.content
      : (m.content as Array<{ type: string; text?: string }>)
          .filter((b) => b.type === "text").map((b) => b.text ?? "").join("")))
    .join("");

describe("a status chunk", () => {
  it("never reaches the conversation", async () => {
    const { loop, context } = makeLoop([
      { type: "status", text: BANNER },
      { type: "text_delta", text: "Here is the answer." },
      { type: "stop", stopReason: "end_turn" },
    ]);
    await loop.run("a question", { model: "auto" });

    const said = assistantText(context);
    expect(said).toBe("Here is the answer.");
    expect(said, "no banner").not.toContain("Auto →");
    expect(said, "no ANSI escapes").not.toContain("[");
  });

  it("is still shown to the user", async () => {
    // Suppressing it from context must not suppress it from the screen — the
    // point of the line is telling the user which model answered.
    const { loop, events } = makeLoop([
      { type: "status", text: BANNER },
      { type: "text_delta", text: "answer" },
      { type: "stop", stopReason: "end_turn" },
    ]);
    const seen: string[] = [];
    events.on("text", (e: any) => { if (e.type === "text") seen.push(e.content); });
    await loop.run("a question", { model: "auto" });
    expect(seen.join("")).toContain("Auto →");
  });

  it("does not by itself count as a reply", async () => {
    // A turn that produced only a status line has said nothing, and must not
    // be recorded as an assistant message at all.
    const { loop, context } = makeLoop([
      { type: "status", text: BANNER },
      { type: "stop", stopReason: "end_turn" },
    ]);
    await loop.run("a question", { model: "auto" });
    expect(assistantText(context)).toBe("");
  });

  it("leaves ordinary text alone", async () => {
    const { loop, context } = makeLoop([
      { type: "text_delta", text: "plain " },
      { type: "text_delta", text: "reply" },
      { type: "stop", stopReason: "end_turn" },
    ]);
    await loop.run("a question", { model: "auto" });
    expect(assistantText(context)).toBe("plain reply");
  });
});
