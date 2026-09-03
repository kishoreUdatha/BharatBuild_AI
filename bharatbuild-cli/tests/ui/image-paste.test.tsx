/**
 * Pasting an image.
 *
 * The ink TUI's /paste read text only, so a screenshot on the clipboard came
 * through as "Clipboard is empty" — the capability existed, but only on the
 * classic UI that most users never see.
 *
 * The classic implementation is not copied here. It pushed its own combined
 * message and then called run() anyway, and the loop pushes the user message
 * itself, so the model received the image and then a duplicate text-only turn
 * right behind it.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { App } from "../../src/ui/ink/App.js";
import { AgentLoop } from "../../src/runtime/agent-loop.js";
import { ContextManager } from "../../src/runtime/context-manager.js";
import { EventStream } from "../../src/runtime/event-stream.js";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { CostMeter } from "../../src/runtime/cost-meter.js";

const ESC = String.fromCharCode(27);
const ENTER = "\r";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("ascii"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; vi.restoreAllMocks(); });

describe("attaching it to the message", () => {
  /** A model client that answers once with no tool calls. */
  const oneShotModel = () => ({
    async *stream() {
      yield { type: "text" as const, text: "ok", stopReason: "end_turn" as const };
    },
  });

  function makeLoop() {
    const context = new ContextManager();
    const events = new EventStream();
    const loop = new AgentLoop(
      oneShotModel() as any, context, new ToolDispatcher(events), events, new CostMeter("auto"),
    );
    return { loop, context };
  }

  it("sends exactly one user message, not two", async () => {
    // The bug in the implementation this replaces.
    const { loop, context } = makeLoop();
    await loop.run("what is wrong here?", {
      model: "auto",
      attachments: [{ type: "image", imageBase64: "AAAA", mimeType: "image/png" }],
    });
    const users = context.messages.filter((m) => m.role === "user");
    expect(users).toHaveLength(1);
  });

  it("puts the image ahead of the text in that message", async () => {
    const { loop, context } = makeLoop();
    await loop.run("what is wrong here?", {
      model: "auto",
      attachments: [{ type: "image", imageBase64: "AAAA", mimeType: "image/png" }],
    });
    const blocks = context.messages.find((m) => m.role === "user")!.content as any[];
    expect(Array.isArray(blocks)).toBe(true);
    expect(blocks[0].type).toBe("image");
    expect(blocks[0].imageBase64).toBe("AAAA");
    expect(blocks[1]).toEqual({ type: "text", text: "what is wrong here?" });
  });

  it("still sends a plain string when nothing is attached", async () => {
    // The ordinary path must not become an array-of-one-block.
    const { loop, context } = makeLoop();
    await loop.run("just a question", { model: "auto" });
    expect(context.messages.find((m) => m.role === "user")!.content).toBe("just a question");
  });

  it("treats an empty attachment list as nothing attached", async () => {
    const { loop, context } = makeLoop();
    await loop.run("hello", { model: "auto", attachments: [] });
    expect(context.messages.find((m) => m.role === "user")!.content).toBe("hello");
  });
});

describe("/paste in the ink TUI", () => {
  async function mountApp() {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 90; stdout.rows = 36;
    let all = "";
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); all += s; if (strip(s).trim()) last = s; });

    const runs: Array<{ input: string; opts: any }> = [];
    const runtime: any = {
      on: () => {}, off: () => {}, cancel: () => {},
      run: async (input: string, opts: any) => { runs.push({ input, opts }); },
      context: { messages: [], push: () => {}, clear: () => {}, pushAll: () => {} },
    };

    const app = render(<App runtime={runtime} model="auto" initialMode="auto" />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 200));
    return {
      frame: () => strip(last),
      all: () => strip(all),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 130)); },
      runs,
    };
  }

  /** Put an image on the clipboard, as far as the code can tell. */
  function clipboardHasImage() {
    vi.doMock("../../src/ui/clipboard.js", () => ({
      readClipboard: async () => ({
        type: "image", imagePath: "/tmp/x.png",
        imageBase64: "QUFB", mimeType: "image/png",
      }),
    }));
  }

  it("says an image was attached rather than that the clipboard is empty", async () => {
    // This is what a screenshot used to produce, because /paste read text only.
    clipboardHasImage();
    const h = await mountApp();
    await h.press("/paste");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));
    expect(h.all()).toMatch(/image attached/i);
    expect(h.all()).not.toMatch(/Clipboard is empty/i);
  }, 20_000);

  it("shows that something is waiting to be sent", async () => {
    // Otherwise the attachment is invisible: not in the box, not in the
    // transcript, nothing to say it is about to go.
    clipboardHasImage();
    const h = await mountApp();
    await h.press("/paste");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));
    expect(h.frame()).toMatch(/image attached/i);
  }, 20_000);

  it("sends it with the next message and then forgets it", async () => {
    clipboardHasImage();
    const h = await mountApp();
    await h.press("/paste");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));

    await h.press("why does this look wrong?");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));

    expect(h.runs).toHaveLength(1);
    expect(h.runs[0]!.opts?.attachments?.[0]?.type).toBe("image");
    // The fixture's own bytes, so this cannot pass by reading a real
    // clipboard that happens to hold an image.
    expect(h.runs[0]!.opts?.attachments?.[0]?.imageBase64).toBe("QUFB");
    expect(h.runs[0]!.input).toBe("why does this look wrong?");

    // A second message must not carry the same image again.
    await h.press("and this one?");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));
    expect(h.runs).toHaveLength(2);
    expect(h.runs[1]!.opts?.attachments).toBeUndefined();
  }, 25_000);
});
