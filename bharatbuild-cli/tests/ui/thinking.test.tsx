/**
 * `<thinking>` blocks.
 *
 * Nothing handled them, so one reply printed 190 lines of internal monologue
 * into the transcript — literal XML tags and all — with the actual conclusion
 * buried underneath. Stripping it entirely would be the wrong fix: reading
 * that reasoning is how a confidently wrong answer got caught.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render, Box } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { MessageBubble } from "../../src/ui/ink/ChatMessages.js";
import { parseThinking, hasThinking } from "../../src/ui/ink/thinking.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("unicode"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

async function draw(content: string, columns = 88): Promise<string[]> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = columns; stdout.rows = 50;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
  const app = render(
    <Box paddingX={1} flexDirection="column">
      <MessageBubble message={{ id: "a", role: "assistant", content, timestamp: new Date(0) }} />
    </Box>,
    { stdout, stdin, patchConsole: false },
  );
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 90));
  return strip(last).split("\n");
}

describe("splitting reasoning from the answer", () => {
  it("separates the two", () => {
    const parts = parseThinking("<thinking>weighing it up</thinking>Here is the answer.");
    expect(parts).toEqual([
      { kind: "thinking", content: "weighing it up" },
      { kind: "text", content: "Here is the answer." },
    ]);
  });

  it("leaves an ordinary reply completely alone", () => {
    expect(parseThinking("just a normal reply")).toEqual([
      { kind: "text", content: "just a normal reply" },
    ]);
  });

  it("handles reasoning that arrives after some text", () => {
    const parts = parseThinking("First.<thinking>hmm</thinking>Second.");
    expect(parts.map((p) => p.kind)).toEqual(["text", "thinking", "text"]);
  });

  it("handles several blocks in one reply", () => {
    const parts = parseThinking("<thinking>a</thinking>mid<thinking>b</thinking>end");
    expect(parts.filter((p) => p.kind === "thinking")).toHaveLength(2);
  });

  it("treats an unclosed tag as reasoning to the end", () => {
    // While a reply streams, the opening tag arrives long before the closing
    // one. Requiring both would print the raw tag and the monologue as prose
    // until the block finished, then snap it into place.
    const parts = parseThinking("<thinking>still going, no close tag yet");
    expect(parts).toEqual([{ kind: "thinking", content: "still going, no close tag yet" }]);
  });

  it("is case-insensitive", () => {
    expect(parseThinking("<Thinking>x</Thinking>y").map((p) => p.kind)).toEqual(["thinking", "text"]);
  });

  it("does not hang on an empty tag pair", () => {
    expect(parseThinking("<thinking></thinking>done")).toEqual([{ kind: "text", content: "done" }]);
  });

  it("detects whether a reply has reasoning at all", () => {
    expect(hasThinking("<thinking>x</thinking>")).toBe(true);
    expect(hasThinking("no tags here")).toBe(false);
  });
});

describe("how it renders", () => {
  /** Shaped like the reply that prompted this: long monologue, short answer. */
  const REAL = [
    "<thinking>",
    ...Array.from({ length: 40 }, (_, i) => `reasoning step ${i + 1}`),
    "</thinking>",
    "",
    "The two orders are not equivalent.",
  ].join("\n");

  it("never shows the raw tags", async () => {
    const lines = await draw(REAL);
    expect(lines.some((l) => l.includes("<thinking>"))).toBe(false);
    expect(lines.some((l) => l.includes("</thinking>"))).toBe(false);
  });

  it("folds a long monologue instead of printing all of it", async () => {
    // 190 lines of reasoning above a two-line conclusion is why this exists.
    const lines = await draw(REAL);
    const shown = lines.filter((l) => l.includes("reasoning step"));
    expect(shown.length).toBeLessThanOrEqual(3);
    expect(lines.some((l) => /more lines/.test(l))).toBe(true);
  });

  it("says how much reasoning there was", async () => {
    expect((await draw(REAL)).some((l) => l.includes("40 lines"))).toBe(true);
  });

  it("keeps the answer fully visible", async () => {
    // The conclusion is the point; folding must never touch it.
    const lines = await draw(REAL);
    expect(lines.some((l) => l.includes("The two orders are not equivalent."))).toBe(true);
  });

  it("puts the answer after the reasoning, not buried inside it", async () => {
    const lines = await draw(REAL);
    const marker = lines.findIndex((l) => l.includes("thinking"));
    const answer = lines.findIndex((l) => l.includes("not equivalent"));
    expect(marker).toBeGreaterThanOrEqual(0);
    expect(answer).toBeGreaterThan(marker);
  });

  it("does not fold a short monologue", async () => {
    const lines = await draw("<thinking>one quick thought</thinking>Answer.");
    expect(lines.some((l) => l.includes("one quick thought"))).toBe(true);
    expect(lines.some((l) => /more lines/.test(l))).toBe(false);
  });

  it("still renders markdown in the answer", async () => {
    // The answer half must keep everything it had before.
    const lines = await draw("<thinking>x</thinking>Use **bold** and `code`.");
    const line = lines.find((l) => l.includes("bold"))!;
    expect(line).not.toContain("**");
    expect(line).not.toContain("`");
  });

  it("leaves a reply with no reasoning untouched", async () => {
    const lines = await draw("# Heading\n\nJust prose.");
    expect(lines.some((l) => l.includes("Heading"))).toBe(true);
    expect(lines.some((l) => l.includes("thinking"))).toBe(false);
  });
});
