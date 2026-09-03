/**
 * The Unicode markers (⏺ ✓ ⎿ ▍ braille) fell back to tofu on a default Windows
 * Terminal font — ⏺ showed as a filled box and ✓ as "/" — so the interface
 * looked broken rather than styled. ASCII is the default; BHARATBUILD_UNICODE=1
 * opts back in.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render, Box } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs, getGlyphs, getGlyphMode, type GlyphSet } from "../../src/ui/ink/glyphs.js";
import { MessageBubble } from "../../src/ui/ink/ChatMessages.js";
import { ToolOutput } from "../../src/ui/ink/ToolOutput.js";
import { StatusBar } from "../../src/ui/ink/StatusBar.js";
import { PermissionPrompt } from "../../src/ui/ink/PermissionPrompt.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => setGlyphs("ascii"));
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

async function draw(node: React.ReactElement, columns = 96): Promise<string> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = columns; stdout.rows = 40;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
  const app = render(node, { stdin, stdout, exitOnCtrlC: false, patchConsole: false });
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 250));
  return strip(last).replace(/[ \t]+$/gm, "");
}

const nonAscii = (s: string) => [...new Set(s.split("").filter((c) => c.charCodeAt(0) > 126))];
const msg = (role: any, content: string) => ({ id: "m", role, content, timestamp: new Date(0) });

describe("defaults", () => {
  it("uses ASCII unless explicitly opted out", () => {
    expect(getGlyphMode()).toBe("ascii");
  });

  it("defines every glyph in both sets", () => {
    const keys: (keyof GlyphSet)[] = [
      "user", "assistant", "system", "toolOk", "toolFail", "elbow", "elbowCont",
      "caret", "idle", "spinner", "bullet", "quote", "rule", "up", "down",
      "ellipsis", "warn", "sep", "currency",
    ];
    for (const mode of ["ascii", "unicode"] as const) {
      setGlyphs(mode);
      const g = getGlyphs();
      for (const k of keys) expect(g[k], `${mode}.${String(k)}`).toBeDefined();
      expect(g.spinner.length).toBeGreaterThan(1);
    }
  });

  it("keeps the ASCII set inside 7-bit range, except the rule", () => {
    // The rule is box-drawing in both sets on purpose: U+2500 is proven to
    // render in the target terminal (the palette frame always did), while a
    // repeated "-" reads as a dashed line. Only the rarer marks fell back.
    setGlyphs("ascii");
    const g = getGlyphs();
    const markers = Object.entries(g)
      .filter(([k, v]) => typeof v === "string" && k !== "rule")
      .map(([, v]) => v as string);
    expect(nonAscii([...markers, ...g.spinner].join(""))).toEqual([]);
    expect(g.rule).toBe("─");
  });

  it("does not collide the spinner with the separator", () => {
    // A "|" spinner frame next to the "|" separator read as a column divider.
    setGlyphs("ascii");
    const g = getGlyphs();
    expect(g.spinner).not.toContain(g.sep);
    expect(g.spinner).not.toContain(g.rule);
  });
});

describe("components render pure ASCII by default", () => {
  it("a user message", async () => {
    const out = await draw(<MessageBubble message={msg("user", "build a page") as any} />);
    expect(nonAscii(out)).toEqual([]);
    expect(out).toContain("> build a page");
  });

  it("an assistant message with markdown", async () => {
    const out = await draw(
      <MessageBubble message={msg("assistant", "## Files\n\n- **index.html** done") as any} />,
    );
    expect(nonAscii(out)).toEqual([]);
    expect(out).toContain("- index.html done");
  });

  it("a successful tool call with output", async () => {
    const out = await draw(
      <ToolOutput tool={{ id: "1", name: "write_file", status: "success",
        input: { path: "a.txt" }, output: "line1\nline2\nline3\nline4", durationMs: 12 }} />,
    );
    expect(nonAscii(out)).toEqual([]);
    expect(out).toContain("+ write_file(a.txt)");
    expect(out).toContain("+- line1");
  });

  it("a failed tool call", async () => {
    const out = await draw(
      <ToolOutput tool={{ id: "1", name: "run_tests", status: "error", input: {}, output: "2 failed" }} />,
    );
    expect(nonAscii(out)).toEqual([]);
    expect(out).toContain("X run_tests");
    // No empty parens when the tool takes no arguments.
    expect(out).not.toContain("run_tests()");
  });

  it("the status bar", async () => {
    const out = await draw(
      <StatusBar model="auto" agent="default" tokenCount={31100} creditBalance={0}
        phase="coding" mode="developer" contextPercent={5} elapsedSec={47} queuedCount={1} />,
    );
    expect(nonAscii(out)).toEqual([]);
    // The credit figure is hidden at zero; assert what the row always carries.
    expect(out).toContain("auto");
    expect(out).toContain("default");
  });

  it("the approval prompt", async () => {
    const out = await draw(
      <PermissionPrompt pending={{ toolName: "write_file", input: { path: "a.txt" } }} onDecide={() => {}} />,
    );
    // Framed now, like the welcome panel and the input box, so box-drawing
    // borders are expected here — ink has no ASCII border style. Everything
    // this component chooses for itself must still be ASCII, which is the
    // part that actually falls back to tofu.
    const BORDER = new Set([..."╭─╮│╰╯"]);
    expect(nonAscii(out).filter((c) => !BORDER.has(c))).toEqual([]);
    expect(out).toContain("Write file");
    expect(out).toContain("> 1. Yes");
  });
});

describe("the unicode layout", () => {
  // These asserted U+23FA and U+23BF. Both are Miscellaneous Technical, a
  // block most monospace fonts cover poorly, and both fell back to boxes on a
  // terminal that renders Box Drawing perfectly well — which is what led to
  // the whole set being abandoned for ASCII. Claude Code uses U+25CF.
  it("marks the assistant with a filled circle", async () => {
    setGlyphs("unicode");
    const out = await draw(<MessageBubble message={msg("assistant", "hello") as any} />);
    expect(out).toContain("●");
  });

  it("hangs tool output off a box-drawing elbow", async () => {
    setGlyphs("unicode");
    const out = await draw(
      <ToolOutput tool={{ id: "1", name: "write_file", status: "success", input: { path: "a" }, output: "ok" }} />,
    );
    expect(out).toContain("●");
    expect(out).toContain("└");
  });

  it("keeps the marker column aligned across outcomes", async () => {
    // Claude Code distinguishes success from failure by colour, not by a
    // different glyph, so the markers stay in one column.
    setGlyphs("unicode");
    const ok = await draw(
      <ToolOutput tool={{ id: "1", name: "write_file", status: "success", input: { path: "a" }, output: "ok" }} />,
    );
    const bad = await draw(
      <ToolOutput tool={{ id: "2", name: "write_file", status: "error", input: { path: "a" }, output: "no" }} />,
    );
    expect(ok.indexOf("●")).toBe(bad.indexOf("●"));
  });

  it("avoids the blocks with patchy font coverage", async () => {
    // U+23xx (Miscellaneous Technical) and U+28xx (Braille) are the two that
    // actually failed to render. Nothing in the set should reach for them.
    setGlyphs("unicode");
    const { getGlyphs } = await import("../../src/ui/ink/glyphs.js");
    const all = Object.values(getGlyphs()).flat().join("");
    for (const ch of all) {
      const cp = ch.codePointAt(0)!;
      expect(cp >= 0x2300 && cp <= 0x23ff, `U+${cp.toString(16)} is Miscellaneous Technical`).toBe(false);
      expect(cp >= 0x2800 && cp <= 0x28ff, `U+${cp.toString(16)} is Braille`).toBe(false);
    }
  });
});

/**
 * claude-code's own glyphs, offered rather than imposed.
 *
 * U+23FA (⏺) and U+23BF (⎿) are Miscellaneous Technical, a block many
 * monospace fonts cover poorly. On this machine they rendered as tofu boxes,
 * which is what made the interface look broken and got the whole Unicode set
 * abandoned once already. So they are a mode you can switch to and away from
 * in one command, not the default.
 */
describe("the claude glyph set", () => {
  it("uses the exact characters claude-code uses", () => {
    setGlyphs("claude");
    const g = getGlyphs();
    expect(g.assistant).toBe("\u23fa");
    expect(g.toolOk).toBe("\u23fa");
    expect(g.elbow).toContain("\u23bf");
  });

  it("is not the default, because those characters are not safe everywhere", () => {
    setGlyphs("unicode");
    expect(getGlyphs().assistant).toBe("\u25cf");
    expect(getGlyphMode()).toBe("unicode");
  });

  it("can be switched back", () => {
    // The way out has to be as quick as the way in — a user who sees boxes
    // needs to undo it without restarting or editing a config file.
    setGlyphs("claude");
    expect(getGlyphMode()).toBe("claude");
    setGlyphs("unicode");
    expect(getGlyphMode()).toBe("unicode");
  });

  it("keeps the elbow and its continuation the same width", () => {
    // A mismatch here steps every wrapped result line out of alignment.
    setGlyphs("claude");
    const g = getGlyphs();
    expect(g.elbow.length).toBe(g.elbowCont.length);
  });

  it("defines every glyph the other sets define", () => {
    setGlyphs("unicode");
    const uni = Object.keys(getGlyphs()).sort();
    setGlyphs("claude");
    expect(Object.keys(getGlyphs()).sort()).toEqual(uni);
  });
});
