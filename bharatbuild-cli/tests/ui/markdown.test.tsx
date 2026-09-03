/**
 * Model replies are markdown. They were printed literally, so an answer showed
 * up as `## 📦 **Files Created:**` and `- **Hero Section** — Eye-catching`.
 */
import { describe, it, expect, afterEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { Markdown } from "../../src/ui/ink/markdown.js";
import { getGlyphs } from "../../src/ui/ink/glyphs.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
afterEach(() => { unmount?.(); unmount = undefined; });

async function draw(content: string, columns = 100): Promise<string> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = columns; stdout.rows = 60;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });

  const app = render(<Markdown content={content} />, { stdin, stdout, exitOnCtrlC: false, patchConsole: false });
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 250));
  return strip(last).replace(/[ \t]+$/gm, "");
}

describe("headings", () => {
  it("drops the hashes", async () => {
    const out = await draw("## Files Created");
    expect(out).toContain("Files Created");
    expect(out).not.toContain("##");
  });

  it("handles every level", async () => {
    const out = await draw("# One\n## Two\n### Three\n#### Four");
    expect(out).not.toMatch(/#/);
    for (const h of ["One", "Two", "Three", "Four"]) expect(out).toContain(h);
  });
});

describe("inline styling", () => {
  it("removes bold markers", async () => {
    const out = await draw("This is **important** text");
    expect(out).toContain("important");
    expect(out).not.toContain("**");
  });

  it("removes inline code backticks", async () => {
    const out = await draw("Open the `index.html` file");
    expect(out).toContain("index.html");
    expect(out).not.toContain("`");
  });

  it("handles bold inside a bullet", async () => {
    // The exact shape from the reported screenshot.
    const out = await draw("- **Hero Section** - Eye-catching intro");
    expect(out).toContain("Hero Section");
    expect(out).toContain("Eye-catching intro");
    expect(out).not.toContain("**");
  });

  it("leaves bare asterisks in prose alone", async () => {
    const out = await draw("use 2 * 3 to multiply");
    expect(out).toContain("2 * 3");
  });
});

describe("lists", () => {
  it("renders a bullet marker", async () => {
    // Assert the active glyph, not a literal — the marker set is swappable.
    const bullet = getGlyphs().bullet;
    const out = await draw("- first\n- second");
    expect(out).toContain(`${bullet}first`);
    expect(out).toContain(`${bullet}second`);
  });

  it("keeps numbered lists numbered", async () => {
    const out = await draw("1. first\n2. second");
    expect(out).toContain("1. first");
    expect(out).toContain("2. second");
  });

  it("preserves indentation of nested bullets", async () => {
    const marker = getGlyphs().bullet.trim();
    const out = await draw("- top\n   - nested");
    const nested = out.split("\n").find((l) => l.includes("nested")) ?? "";
    const top = out.split("\n").find((l) => l.includes("top")) ?? "";
    expect(nested.indexOf(marker)).toBeGreaterThan(top.indexOf(marker));
  });
});

describe("spacing", () => {
  it("keeps blank lines between sections", async () => {
    // Ink collapses an empty <Text>, which ran every section together.
    const out = await draw("## One\n\nbody one\n\n## Two\n\nbody two");
    const lines = out.split("\n").map((l) => l.trim());
    const i1 = lines.indexOf("One");
    const iBody = lines.indexOf("body one");
    expect(iBody - i1).toBe(2);
  });
});

describe("passthrough", () => {
  it("leaves plain prose untouched", async () => {
    const out = await draw("Just a normal sentence.");
    expect(out).toContain("Just a normal sentence.");
  });

  it("does not choke on an empty string", async () => {
    await expect(draw("")).resolves.toBeDefined();
  });
});
