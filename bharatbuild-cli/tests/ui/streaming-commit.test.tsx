/**
 * A real session ended with the final assistant message printed twice — once
 * in full, then again immediately below it.
 *
 * `commit()` was being called from inside a `setStreaming` updater. A state
 * updater must be pure: React is free to invoke it more than once for a single
 * update, and every invocation appended the message to the transcript again.
 * The same anti-pattern was fixed for the shift+tab mode notice and missed
 * here.
 *
 * These count what is on screen rather than everything ever written: the live
 * region repaints constantly, so a raw occurrence count over the whole stream
 * conflates ordinary repaints with genuine duplicates.
 */
import { describe, it, expect, afterEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { App } from "../../src/ui/ink/App.js";
import { VirtualTerminal } from "../helpers/vt.js";
import { makeRuntime } from "../helpers/ink-harness.js";

let unmount: (() => void) | undefined;
afterEach(() => { unmount?.(); unmount = undefined; });

/** Mount the App with a scripted runtime and return the resulting screen. */
async function runScript(script: (emit: (e: any) => Promise<void>) => Promise<void>) {
  const rt = makeRuntime();
  rt.run = async () => { await script((e) => rt.events.emit(e)); };

  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = 100; stdout.rows = 40;

  const vt = new VirtualTerminal(100, 40);
  stdout.on("data", (c: Buffer) => vt.write(c.toString()));

  const app = render(
    <App runtime={rt} model="auto" mode="developer" initialMode="ask" />,
    { stdin, stdout, exitOnCtrlC: false, patchConsole: false },
  );
  unmount = () => app.unmount();

  await new Promise((r) => setTimeout(r, 200));
  stdin.write("go");
  await new Promise((r) => setTimeout(r, 120));
  stdin.write("\r");
  await new Promise((r) => setTimeout(r, 600));
  return vt;
}

const complete = (ts: number) => ({
  type: "complete", totalTokens: 10, turns: 1, durationMs: 5,
  inputTokens: 5, outputTokens: 5, timestamp: ts,
});

describe("the assistant's reply is committed exactly once", () => {
  it("does not duplicate the closing message", async () => {
    const vt = await runScript(async (emit) => {
      await emit({ type: "text", content: "FINALMARKER", delta: true, timestamp: 1 });
      await emit(complete(2));
    });
    expect(vt.countVisible("FINALMARKER")).toBe(1);
  });

  it("does not duplicate narration flushed by a tool call", async () => {
    // tool_call flushes the streamed text through the same updater.
    const vt = await runScript(async (emit) => {
      await emit({ type: "text", content: "NARRATIONMARKER", delta: true, timestamp: 1 });
      await emit({ type: "tool_call", id: "t1", toolName: "write_file", input: { path: "a.ts" }, timestamp: 2 });
      await emit({ type: "tool_result", id: "t1", toolName: "write_file", output: "ok", isError: false, durationMs: 3, timestamp: 3 });
      await emit(complete(4));
    });
    expect(vt.countVisible("NARRATIONMARKER")).toBe(1);
  });

  it("keeps both halves, once each, when a tool call splits the reply", async () => {
    const vt = await runScript(async (emit) => {
      await emit({ type: "text", content: "FIRSTHALF", delta: true, timestamp: 1 });
      await emit({ type: "tool_call", id: "t1", toolName: "write_file", input: { path: "a.ts" }, timestamp: 2 });
      await emit({ type: "tool_result", id: "t1", toolName: "write_file", output: "ok", isError: false, durationMs: 3, timestamp: 3 });
      await emit({ type: "text", content: "SECONDHALF", delta: true, timestamp: 4 });
      await emit(complete(5));
    });
    expect(vt.countVisible("FIRSTHALF")).toBe(1);
    expect(vt.countVisible("SECONDHALF")).toBe(1);
    // Narration must precede the tool card that it introduces.
    expect(vt.lastRowOf("FIRSTHALF")).toBeLessThan(vt.lastRowOf("SECONDHALF"));
  });

  it("does not lose the reply when there is no tool call at all", async () => {
    // Guard against fixing duplication by dropping the commit entirely.
    const vt = await runScript(async (emit) => {
      await emit({ type: "text", content: "PLAINREPLY", delta: true, timestamp: 1 });
      await emit(complete(2));
    });
    expect(vt.countVisible("PLAINREPLY")).toBe(1);
  });
});
