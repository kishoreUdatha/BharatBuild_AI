/**
 * Esc-esc rewind.
 *
 * `/rewind` could already fork the conversation, but it took three steps:
 * remember the command, run it bare to see the numbered list, run it again
 * with a number. Wanting to go back a step is exactly the moment you do not
 * want to look up a command.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { App } from "../../src/ui/ink/App.js";
import { RewindPicker } from "../../src/ui/ink/RewindPicker.js";
import { userTurns, keepBefore, type Turn } from "../../src/ui/ink/rewind.js";

const ESC = String.fromCharCode(27);
const UP = `${ESC}[A`;
const ENTER = "\r";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("unicode"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

describe("which messages are offered", () => {
  const convo = [
    { role: "user", content: "build a login page" },
    { role: "assistant", content: "done" },
    { role: "user", content: "now add validation" },
    { role: "assistant", content: "done" },
  ];

  it("offers the user's own turns, in order", () => {
    expect(userTurns(convo).map((t) => t.preview)).toEqual([
      "build a login page", "now add validation",
    ]);
  });

  it("ignores assistant replies", () => {
    expect(userTurns(convo).every((t) => convo[t.index]!.role === "user")).toBe(true);
  });

  it("leaves out a shell result recorded as a user turn", () => {
    // `!command` output is stored as a user message but is not something the
    // user asked, so it would be noise in the list.
    const withBang = [
      ...convo,
      { role: "user", content: "I ran this command myself:\n\n$ npm test\n\nok" },
    ];
    expect(userTurns(withBang)).toHaveLength(2);
  });

  it("shows only the question when a mention attached files", () => {
    // The attached file body would otherwise become the preview.
    const turns = userTurns([
      { role: "user", content: "explain @a.ts\n--- Files referenced above, attached in full ---\n### a.ts\nlots" },
    ]);
    expect(turns[0]!.preview).toBe("explain @a.ts");
    expect(turns[0]!.content).toBe("explain @a.ts");
  });

  it("reads content blocks, not just plain strings", () => {
    const turns = userTurns([
      { role: "user", content: [{ type: "text", text: "from a block" }] },
    ]);
    expect(turns[0]!.preview).toBe("from a block");
  });

  it("shortens a long message for the list but keeps it whole for editing", () => {
    const long = "x".repeat(200);
    const turns = userTurns([{ role: "user", content: long }]);
    expect(turns[0]!.preview.length).toBeLessThanOrEqual(60);
    expect(turns[0]!.content).toHaveLength(200);
  });

  it("has nothing to offer in a fresh session", () => {
    expect(userTurns([])).toEqual([]);
  });
});

describe("where the cut falls", () => {
  const convo = [
    { role: "user", content: "one" },
    { role: "assistant", content: "reply one" },
    { role: "user", content: "two" },
    { role: "assistant", content: "reply two" },
  ];

  it("drops the chosen turn and everything after it", () => {
    // The chosen message is being replaced, so it goes too.
    const turns = userTurns(convo);
    expect(keepBefore(convo, turns[1]!)).toHaveLength(2);
  });

  it("empties the conversation when rewinding to the first turn", () => {
    expect(keepBefore(convo, userTurns(convo)[0]!)).toEqual([]);
  });
});

describe("the picker", () => {
  async function mount(turns: Turn[]) {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 88; stdout.rows = 40;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const chosen: Array<Turn | null> = [];
    const app = render(<RewindPicker turns={turns} onDecide={(t) => chosen.push(t)} />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    return {
      frame: () => strip(last),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 60)); },
      chosen,
    };
  }

  const three = userTurns([
    { role: "user", content: "first" },
    { role: "user", content: "second" },
    { role: "user", content: "third" },
  ]);

  it("starts on the most recent message", async () => {
    // Going back one step is the common case and should cost no keystrokes.
    const h = await mount(three);
    expect(h.frame()).toContain("❯  3. third");
  });

  it("moves up the list", async () => {
    const h = await mount(three);
    await h.press(UP);
    expect(h.frame()).toContain("❯  2. second");
  });

  it("returns the chosen turn on enter", async () => {
    const h = await mount(three);
    await h.press(UP);
    await h.press(ENTER);
    expect(h.chosen[0]?.content).toBe("second");
  });

  it("cancels on escape without choosing anything", async () => {
    const h = await mount(three);
    await h.press(ESC);
    expect(h.chosen).toEqual([null]);
  });

  it("does not run off the end of the list", async () => {
    const h = await mount(three);
    for (let i = 0; i < 8; i++) await h.press(UP);
    await h.press(ENTER);
    expect(h.chosen[0]?.content).toBe("first");
  });

  it("scrolls a long conversation instead of printing all of it", async () => {
    const many = userTurns(
      Array.from({ length: 30 }, (_, i) => ({ role: "user", content: `message ${i + 1}` })),
    );
    const h = await mount(many);
    const f = h.frame();
    expect(f).toContain("message 30");
    expect(f).toMatch(/earlier/);
    expect(f).not.toContain("message 1 ");
  });
});

describe("the double tap", () => {
  const convo = [
    { role: "user", content: "build a login page" },
    { role: "assistant", content: "done" },
  ];

  function makeRuntime(busy = false) {
    const messages = [...convo];
    return {
      on: () => {}, off: () => {},
      run: () => new Promise<void>((resolve) => { if (!busy) resolve(); }),
      cancel: () => {},
      context: {
        messages,
        clear: () => { messages.length = 0; },
        pushAll: (m: any[]) => { messages.push(...m); },
        push: () => {},
      },
    };
  }

  async function mountApp(runtime: any) {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 90; stdout.rows = 40;
    let all = "";
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); all += s; if (strip(s).trim()) last = s; });
    const app = render(<App runtime={runtime} model="auto" initialMode="ask" />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 200));
    return {
      frame: () => strip(last),
      all: () => strip(all),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 90)); },
    };
  }

  it("opens the list on two quick presses", async () => {
    const h = await mountApp(makeRuntime());
    await h.press(ESC);
    await h.press(ESC);
    expect(h.frame()).toContain("Rewind to a message");
  }, 20_000);

  it("does nothing on a single press", async () => {
    const h = await mountApp(makeRuntime());
    await h.press(ESC);
    expect(h.frame()).not.toContain("Rewind to a message");
  }, 20_000);

  it("does not treat two slow presses as a pair", async () => {
    const h = await mountApp(makeRuntime());
    await h.press(ESC);
    await new Promise((r) => setTimeout(r, 800));
    await h.press(ESC);
    expect(h.frame()).not.toContain("Rewind to a message");
  }, 20_000);

  it("says so when there is nothing to rewind to", async () => {
    const empty = makeRuntime();
    empty.context.messages.length = 0;
    const h = await mountApp(empty);
    await h.press(ESC);
    await h.press(ESC);
    expect(h.all()).toContain("Nothing to rewind to yet");
  }, 20_000);

  it("truncates the conversation and hands the message back", async () => {
    const runtime = makeRuntime();
    const h = await mountApp(runtime);
    await h.press(ESC);
    await h.press(ESC);
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 150));
    expect(runtime.context.messages).toHaveLength(0);
    // Back in the box so the near-right instruction can be edited rather than
    // retyped — the reason for going back in the first place.
    expect(h.frame()).toContain("build a login page");
  }, 20_000);

  it("closes without changing anything on escape", async () => {
    const runtime = makeRuntime();
    const h = await mountApp(runtime);
    await h.press(ESC);
    await h.press(ESC);
    await h.press(ESC);
    await new Promise((r) => setTimeout(r, 120));
    expect(h.frame()).not.toContain("Rewind to a message");
    expect(runtime.context.messages).toHaveLength(2);
  }, 20_000);
});
