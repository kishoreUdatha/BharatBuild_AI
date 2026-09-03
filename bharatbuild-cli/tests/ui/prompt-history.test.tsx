/**
 * Up-arrow prompt history.
 *
 * The readline UI declared `history` and `historyIndex` and never read either:
 * no key was bound and the index was reset on every prompt, so the first
 * reflex anyone has in a REPL did nothing and long prompts were retyped.
 *
 * Navigation is pure, so the interesting cases — the ends of the list, the
 * draft the user was midway through — are tested directly; the key handling is
 * then checked once through the real component.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { InputPrompt } from "../../src/ui/ink/InputPrompt.js";
import {
  newCursor, historyUp, historyDown, pushEntry,
  loadHistory, saveHistory, historyFile,
} from "../../src/ui/ink/prompt-history.js";

const ESC = String.fromCharCode(27);
const UP = `${ESC}[A`;
const DOWN = `${ESC}[B`;
const ENTER = "\r";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

describe("walking the list", () => {
  const cur = () => newCursor(["first", "second", "third"]);

  it("recalls the most recent entry first", () => {
    expect(historyUp(cur(), "").value).toBe("third");
  });

  it("keeps going back", () => {
    const a = historyUp(cur(), "");
    const b = historyUp(a.cursor, a.value);
    expect(b.value).toBe("second");
    expect(historyUp(b.cursor, b.value).value).toBe("first");
  });

  it("stops at the oldest instead of wrapping", () => {
    // Wrapping would drop the user back at the newest entry, which reads as
    // the list having been lost.
    let m = historyUp(cur(), "");
    for (let i = 0; i < 5; i++) m = historyUp(m.cursor, m.value);
    expect(m.value).toBe("first");
  });

  it("comes back down through the list", () => {
    const a = historyUp(cur(), "");
    const b = historyUp(a.cursor, a.value);
    expect(historyDown(b.cursor, b.value).value).toBe("third");
  });

  it("restores the half-typed draft on the way back", () => {
    // The whole reason the draft is stashed: pressing up to check something
    // must not destroy what was being written.
    const a = historyUp(cur(), "half a thought");
    expect(a.value).toBe("third");
    const back = historyDown(a.cursor, a.value);
    expect(back.value).toBe("half a thought");
  });

  it("does not claim the key when there is nothing to recall", () => {
    // Unhandled, so the press falls through to whatever else wants it.
    expect(historyUp(newCursor([]), "x").handled).toBe(false);
  });

  it("does not claim a down press while showing the draft", () => {
    expect(historyDown(newCursor(["a"]), "x").handled).toBe(false);
  });
});

describe("what gets recorded", () => {
  it("appends in order", () => {
    expect(pushEntry(pushEntry([], "one"), "two")).toEqual(["one", "two"]);
  });

  it("ignores blank input", () => {
    expect(pushEntry([], "   ")).toEqual([]);
  });

  it("collapses an immediate repeat", () => {
    // Holding enter on one command should not push everything else out of
    // reach of the arrow key.
    expect(pushEntry(["build"], "build")).toEqual(["build"]);
  });

  it("keeps a repeat that is not immediate", () => {
    expect(pushEntry(["build", "test"], "build")).toEqual(["build", "test", "build"]);
  });

  it("caps the list rather than growing without bound", () => {
    let entries: string[] = [];
    for (let i = 0; i < 600; i++) entries = pushEntry(entries, `cmd ${i}`);
    expect(entries.length).toBeLessThanOrEqual(500);
    // The newest survive; the oldest are the ones dropped.
    expect(entries[entries.length - 1]).toBe("cmd 599");
  });
});

describe("persistence", () => {
  let home: string;
  let projectA: string;
  let projectB: string;

  beforeEach(() => {
    home = fs.mkdtempSync(path.join(os.tmpdir(), "bb-hist-"));
    process.env["BHARATBUILD_HOME"] = home;
    projectA = fs.mkdtempSync(path.join(os.tmpdir(), "bb-projA-"));
    projectB = fs.mkdtempSync(path.join(os.tmpdir(), "bb-projB-"));
  });
  afterEach(() => {
    try { fs.rmSync(home, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  it("survives a restart", () => {
    saveHistory(["build the app"], projectA);
    expect(loadHistory(projectA)).toEqual(["build the app"]);
  });

  it("keeps projects apart", () => {
    // Recalling another repo's commands is noise, not history.
    saveHistory(["deploy to prod"], projectA);
    expect(loadHistory(projectB)).toEqual([]);
  });

  it("returns an empty list when nothing was ever saved", () => {
    expect(loadHistory(projectA)).toEqual([]);
  });

  it("survives a corrupt file instead of crashing the input box", () => {
    const file = historyFile(projectA);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "{not json");
    expect(loadHistory(projectA)).toEqual([]);
  });

  it("ignores non-string junk inside a valid file", () => {
    const file = historyFile(projectA);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(["ok", 42, null, "", "fine"]));
    expect(loadHistory(projectA)).toEqual(["ok", "fine"]);
  });

  it("does not throw when the home directory cannot be written", () => {
    process.env["BHARATBUILD_HOME"] = path.join(home, "file-not-dir");
    fs.writeFileSync(path.join(home, "file-not-dir"), "x");
    expect(() => saveHistory(["a"], projectA)).not.toThrow();
  });
});

describe("the arrow keys in the real input box", () => {
  let unmount: (() => void) | undefined;
  let home: string;
  let project: string;

  beforeEach(() => {
    setGlyphs("ascii");
    home = fs.mkdtempSync(path.join(os.tmpdir(), "bb-hist-ui-"));
    process.env["BHARATBUILD_HOME"] = home;
    project = fs.mkdtempSync(path.join(os.tmpdir(), "bb-proj-ui-"));
  });
  afterEach(() => {
    unmount?.(); unmount = undefined;
    try { fs.rmSync(home, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  async function mount() {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const submitted: string[] = [];
    const app = render(
      <InputPrompt onSubmit={(v) => submitted.push(v)} historyCwd={project} />,
      { stdout, stdin, patchConsole: false },
    );
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    return {
      frame: () => strip(last),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 60)); },
      submitted,
    };
  }

  it("recalls what was just sent", async () => {
    const h = await mount();
    await h.press("build the app");
    await h.press(ENTER);
    expect(h.submitted).toEqual(["build the app"]);
    expect(h.frame(), "box cleared after sending").not.toContain("build the app");

    await h.press(UP);
    expect(h.frame()).toContain("build the app");
  });

  it("walks back through several prompts", async () => {
    const h = await mount();
    for (const p of ["first thing", "second thing"]) {
      await h.press(p);
      await h.press(ENTER);
    }
    await h.press(UP);
    expect(h.frame()).toContain("second thing");
    await h.press(UP);
    expect(h.frame()).toContain("first thing");
    await h.press(DOWN);
    expect(h.frame()).toContain("second thing");
  });

  it("clears the box on the way past the newest entry", async () => {
    const h = await mount();
    await h.press("only one");
    await h.press(ENTER);
    await h.press(UP);
    expect(h.frame()).toContain("only one");
    await h.press(DOWN);
    expect(h.frame()).not.toContain("only one");
  });

  it("reads history written by an earlier session", async () => {
    saveHistory(["from last time"], project);
    const h = await mount();
    await h.press(UP);
    expect(h.frame()).toContain("from last time");
  });

  it("leaves the arrows to the palette while it is open", async () => {
    // Both readings of the press are plausible; the visible list wins.
    saveHistory(["an earlier prompt"], project);
    const h = await mount();
    await h.press("/");
    await h.press(UP);
    expect(h.frame()).not.toContain("an earlier prompt");
  });
});
