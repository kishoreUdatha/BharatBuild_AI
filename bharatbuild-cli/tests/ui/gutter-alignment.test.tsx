/**
 * The left gutter has to be one column for the whole transcript.
 *
 * Messages were wrapped in `paddingX={1}` by App and tool cards were not, so
 * an assistant line started one column right of the tool card under it. The
 * step was small enough to look like a rendering fault rather than a layout
 * choice, and it appeared on every turn, since messages and tools interleave.
 *
 * These render the same wrappers App uses and compare the resulting columns —
 * asserting on the padding prop would pass whatever App actually does.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render, Box } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { MessageBubble } from "../../src/ui/ink/ChatMessages.js";
import { ToolOutput } from "../../src/ui/ink/ToolOutput.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => setGlyphs("ascii"));
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

async function draw(node: React.ReactElement, columns = 96): Promise<string[]> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = columns; stdout.rows = 40;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
  const app = render(node, { stdout, stdin, patchConsole: false });
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 60));
  return strip(last).split("\n").filter((l) => l.trim() !== "");
}

/** Column of the first non-space character. */
const gutterOf = (line: string): number => line.length - line.trimStart().length;

const message = (content: string) => ({
  id: "m1",
  role: "assistant" as const,
  content,
  timestamp: new Date(0),
});

const tool = {
  id: "t1",
  name: "read_file",
  args: { path: "src/app.ts" },
  status: "success" as const,
  output: "export const a = 1;",
};

describe("the left gutter", () => {
  it("puts an assistant line and a tool card in the same column", async () => {
    // Exactly what App renders for each kind of history entry.
    const lines = await draw(
      <Box flexDirection="column">
        <Box paddingX={1} flexDirection="column">
          <MessageBubble message={message("Reading the entry point.")} />
        </Box>
        <Box flexDirection="column">
          <ToolOutput tool={tool} />
        </Box>
      </Box>,
    );

    const assistant = lines.find((l) => l.includes("Reading the entry point"))!;
    const card = lines.find((l) => l.includes("read_file"))!;
    expect(assistant, "assistant line rendered").toBeDefined();
    expect(card, "tool card rendered").toBeDefined();
    expect(gutterOf(card)).toBe(gutterOf(assistant));
  });

  it("keeps a tool's own rows under its marker", async () => {
    const lines = await draw(<ToolOutput tool={tool} />);
    const marker = lines.find((l) => l.includes("read_file"))!;
    const result = lines.find((l) => l.includes("export const a"))!;
    // The result hangs off an elbow, so it sits further right than the marker,
    // never left of it.
    expect(gutterOf(result)).toBeGreaterThan(gutterOf(marker));
  });

  it("indents a streaming reply the same as a committed one", async () => {
    // The live region and <Static> render the same message through different
    // wrappers; a mismatch makes the text jump sideways the moment the turn
    // commits.
    const live = await draw(
      <Box paddingX={1} flexDirection="column">
        <MessageBubble message={{ ...message("Half a sen"), isStreaming: true }} />
      </Box>,
    );
    const committed = await draw(
      <Box paddingX={1} flexDirection="column">
        <MessageBubble message={message("Half a sentence.")} />
      </Box>,
    );
    expect(gutterOf(live[0]!)).toBe(gutterOf(committed[0]!));
  });

  it("aligns every line of a multi-line reply under the first", async () => {
    // The marker sits in its own flex child, so the text column is the same on
    // every row — the marker occupies row one of that gutter and nothing else.
    // Compare where the text starts, not where the row's first ink is: on row
    // one that is the marker, which is meant to sit further left.
    const lines = await draw(
      <Box paddingX={1} flexDirection="column">
        <MessageBubble message={message("First line.\nSecond line.\nThird line.")} />
      </Box>,
    );
    const at = (needle: string) => lines.find((l) => l.includes(needle))!.indexOf(needle);
    expect(at("Second line")).toBe(at("First line"));
    expect(at("Third line")).toBe(at("First line"));
  });

  it("starts a table in the same column as the prose around it", async () => {
    // A table is rendered as its own block, so it is the one construct that
    // can drift from the text column without anything else moving.
    const lines = await draw(
      <Box paddingX={1} flexDirection="column">
        <MessageBubble
          message={message(
            ["Here is what I found.", "", "| Tool | State |", "|------|-------|", "| java | ok |"].join("\n"),
          )}
        />
      </Box>,
    );
    const prose = lines.find((l) => l.includes("Here is what I found"))!;
    const header = lines.find((l) => l.includes("Tool"))!;
    const row = lines.find((l) => l.includes("java"))!;
    expect(header.indexOf("Tool")).toBe(prose.indexOf("Here"));
    expect(row.indexOf("java")).toBe(prose.indexOf("Here"));
  });
});
