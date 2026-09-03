/**
 * Parallel tool execution asked for permission inside Promise.all, so every
 * prompt fired at once. The TUI has a single pending slot: the second prompt
 * overwrote the first, whose promise never resolved, and Promise.all then
 * waited forever. The turn hung with no error and no way out but Ctrl+C.
 *
 * Approval is a conversation with one human. It cannot be parallelised even
 * when the work can.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { AgentLoop } from "../../src/runtime/agent-loop.js";
import { ContextManager } from "../../src/runtime/context-manager.js";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { EventStream } from "../../src/runtime/event-stream.js";
import { CostMeter } from "../../src/runtime/cost-meter.js";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-approve-"));
for (const n of ["a.txt", "b.txt", "c.txt"]) fs.writeFileSync(path.join(dir, n), "x");

/** A model that asks for three parallel-safe reads, then finishes. */
function threeReads() {
  let turn = 0;
  return {
    async *complete() {
      if (turn++ === 0) {
        for (const n of ["a.txt", "b.txt", "c.txt"]) {
          yield {
            type: "tool_use" as const,
            toolUseId: `t-${n}`,
            toolName: "read_file",
            toolInput: { path: path.join(dir, n) },
          };
        }
        yield { type: "stop" as const, stopReason: "tool_use" as const };
        return;
      }
      yield { type: "text_delta" as const, text: "done" };
      yield { type: "stop" as const, stopReason: "end_turn" as const };
    },
  };
}

function makeLoop(onPermission: (n: string, i: Record<string, unknown>) => Promise<"allow" | "deny" | "cancel">) {
  const events = new EventStream();
  const ctx = new ContextManager();
  const loop = new AgentLoop(threeReads() as never, ctx, new ToolDispatcher(events), events, new CostMeter("auto"));
  return { ctx, run: () => loop.run("go", { model: "auto", maxTurns: 3, onPermission }) };
}

describe("approvals for parallel tools", () => {
  it("are requested one at a time", async () => {
    // The failing shape: a UI that can only show one prompt, answering each as
    // it arrives. Concurrent asks lost all but the last and hung.
    let open = 0;
    let maxOpen = 0;
    const asker = async () => {
      open++;
      maxOpen = Math.max(maxOpen, open);
      await new Promise((r) => setTimeout(r, 20));
      open--;
      return "allow" as const;
    };

    const { run } = makeLoop(asker);
    await run();
    expect(maxOpen, "two prompts were open at once").toBe(1);
  });

  it("completes rather than hanging", async () => {
    const { run } = makeLoop(async () => "allow");
    const finished = await Promise.race([
      run().then(() => "finished"),
      new Promise((r) => setTimeout(() => r("hung"), 4000)),
    ]);
    expect(finished).toBe("finished");
  }, 10_000);

  it("records a result for every tool, denied ones included", async () => {
    // Every tool_use needs a matching tool_result or the next request is
    // rejected outright.
    const { ctx, run } = makeLoop(async (_n, input) =>
      String(input["path"]).endsWith("b.txt") ? "deny" : "allow",
    );
    await run();

    let uses = 0;
    let results = 0;
    for (const m of ctx.forRequest()) {
      for (const c of Array.isArray(m.content) ? m.content : []) {
        if ((c as { type?: string }).type === "tool_use") uses++;
        if ((c as { type?: string }).type === "tool_result") results++;
      }
    }
    expect(uses).toBeGreaterThan(0);
    expect(results).toBe(uses);
  });

  it("stops the turn when the user cancels", async () => {
    const { run } = makeLoop(async () => "cancel");
    await expect(run()).resolves.toBeUndefined();
  });
});
