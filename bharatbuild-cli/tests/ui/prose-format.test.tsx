/**
 * How a reply reads on screen: colour, paragraph spacing, and the markdown
 * constructs models actually emit.
 *
 * Several of these were wrong in ways that only show up in a real terminal —
 * body text carried no colour at all and inherited whatever the profile used,
 * and a code fence butted straight against the paragraph above it.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render, Box } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { MessageBubble } from "../../src/ui/ink/ChatMessages.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("unicode"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

/** Returns the frame both with and without its escape codes. */
async function draw(content: string, columns = 84): Promise<{ raw: string; lines: string[] }> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = columns; stdout.rows = 60;
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
  return { raw: last, lines: strip(last).split("\n") };
}

describe("body text colour", () => {
  it("is the theme's, not the terminal's default", async () => {
    // This carried no SGR code at all, so a reply rendered in whatever
    // foreground the profile happened to use while the headings, tool output
    // and status line around it were themed. 97 is whiteBright; 37 is the
    // "white" that actually renders grey.
    const { raw } = await draw("An ordinary sentence.");
    const line = raw.split("\n").find((l) => strip(l).includes("An ordinary sentence"))!;
    expect(line).toContain(`${ESC}[97m`);
  });

  it("colours list items too", async () => {
    const { raw } = await draw("- a bulleted item\n\n1. a numbered item");
    for (const needle of ["a bulleted item", "a numbered item"]) {
      const line = raw.split("\n").find((l) => strip(l).includes(needle))!;
      expect(line, needle).toContain(`${ESC}[97m`);
    }
  });
});

describe("inline constructs", () => {
  it("shows a link's label and its address, not the markdown", async () => {
    // A terminal cannot click the label, so dropping the URL loses it; the
    // raw form showed the address twice.
    const { lines } = await draw("See the [docs](https://example.com) for more.");
    const line = lines.find((l) => l.includes("docs"))!;
    expect(line).toContain("docs");
    expect(line).toContain("https://example.com");
    expect(line).not.toContain("](");
    expect(line).not.toContain("[docs]");
  });

  it("does not print the address twice when it is its own label", async () => {
    const { lines } = await draw("[https://example.com](https://example.com)");
    const line = lines.find((l) => l.includes("example.com"))!;
    expect(line.match(/example\.com/g)).toHaveLength(1);
  });

  it("strikes text through instead of printing tildes", async () => {
    const { lines } = await draw("This is ~~gone~~ now.");
    const line = lines.find((l) => l.includes("gone"))!;
    expect(line).not.toContain("~~");
  });

  it("still handles bold and code", async () => {
    const { lines } = await draw("A **bold** word and `some_code`.");
    const line = lines.find((l) => l.includes("bold"))!;
    expect(line).not.toContain("**");
    expect(line).not.toContain("`");
  });
});

describe("lists", () => {
  it("draws a checklist as boxes, not literal brackets", async () => {
    const { lines } = await draw("- [ ] not done\n- [x] done");
    const undone = lines.find((l) => l.includes("not done"))!;
    const done = lines.find((l) => l.includes("done") && !l.includes("not done"))!;
    expect(undone).not.toContain("[ ]");
    expect(done).not.toContain("[x]");
    expect(undone).toContain("☐");
    expect(done).toContain("☑");
  });

  it("keeps nesting indentation", async () => {
    const { lines } = await draw("- top\n  - nested");
    const top = lines.find((l) => l.includes("top"))!;
    const nested = lines.find((l) => l.includes("nested"))!;
    expect(nested.indexOf("•")).toBeGreaterThan(top.indexOf("•"));
  });
});

describe("the horizontal rule", () => {
  it("spans the text column rather than a fixed stub", async () => {
    // It was 24 characters whatever the terminal width, which read as a stray
    // dash beside full-width paragraphs.
    const { lines } = await draw("above\n\n---\n\nbelow", 100);
    const rule = lines.find((l) => l.includes("──"))!;
    expect(rule.trim().length).toBeGreaterThan(60);
  });

  it("does not overrun a narrow terminal", async () => {
    const { lines } = await draw("above\n\n---\n\nbelow", 40);
    const rule = lines.find((l) => l.includes("──"))!;
    expect(rule.length).toBeLessThanOrEqual(40);
  });
});

describe("code fences", () => {
  it("leaves a blank row between prose and the box", async () => {
    // `.trim()` on the surrounding prose ate the separator, so the box sat
    // hard against the sentence above it.
    const { lines } = await draw("Before the code.\n\n```ts\nconst x = 1;\n```\n\nAfter the code.");
    const before = lines.findIndex((l) => l.includes("Before the code"));
    const boxTop = lines.findIndex((l) => l.includes("╭"));
    const boxBottom = lines.findIndex((l) => l.includes("╰"));
    const after = lines.findIndex((l) => l.includes("After the code"));
    expect(lines[boxTop - 1]!.trim()).toBe("");
    expect(lines[boxBottom + 1]!.trim()).toBe("");
    expect(before).toBeLessThan(boxTop);
    expect(after).toBeGreaterThan(boxBottom);
  });

  it("renders an unfinished fence as code while it streams", async () => {
    // The regex required the closing fence, so a half-arrived block showed as
    // prose with visible backticks and then snapped into a box when it
    // completed — a flicker on every code reply.
    const { lines } = await draw("Here you go:\n\n```ts\nconst x = 1;\nconst y = 2;");
    expect(lines.some((l) => l.includes("╭")), "drawn as a box").toBe(true);
    expect(lines.some((l) => l.includes("```")), "no raw backticks").toBe(false);
    expect(lines.some((l) => l.includes("const y = 2;"))).toBe(true);
  });

  it("does not hang on a bare opening fence", async () => {
    // A zero-length match at end-of-text would loop forever.
    const { lines } = await draw("Starting:\n\n```ts\n");
    expect(lines.some((l) => l.includes("Starting"))).toBe(true);
  });
});
