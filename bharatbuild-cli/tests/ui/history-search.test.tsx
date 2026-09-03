/**
 * ctrl+r — reverse search through prompt history.
 *
 * The arrow keys walk history one entry at a time. That is fine for the last
 * thing you typed and useless for something forty prompts ago, which is
 * exactly when you want it back. The history was already stored per project;
 * it just had no way in.
 *
 * ctrl+o already toggles expanded tool output, so ctrl+r is free to mean what
 * it means in every shell.
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
  beginSearch, searchType, searchBackspace, searchOlder, searchValue, searchLabel,
  saveHistory,
} from "../../src/ui/ink/prompt-history.js";

const ESC = String.fromCharCode(27);
const CTRL_R = String.fromCharCode(18);
const ENTER = "\r";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\[[0-9;?]*[A-Za-z]`, "g"), "");

const HISTORY = ["fix the login redirect", "add validation rules", "run the tests", "fix the build"];

describe("searching", () => {
  it("finds the newest match", () => {
    // Two entries contain "fix"; the recent one is what you meant.
    const s = searchType(beginSearch(""), HISTORY, "f");
    expect(searchValue(searchType(s, HISTORY, "i"), HISTORY)).toBe("fix the build");
  });

  it("steps to the next older match", () => {
    let s = beginSearch("");
    for (const ch of "fix") s = searchType(s, HISTORY, ch);
    expect(searchValue(s, HISTORY)).toBe("fix the build");
    s = searchOlder(s, HISTORY);
    expect(searchValue(s, HISTORY)).toBe("fix the login redirect");
  });

  it("stays put when there is no older match", () => {
    let s = beginSearch("");
    for (const ch of "fix") s = searchType(s, HISTORY, ch);
    s = searchOlder(s, HISTORY);
    const stuck = searchOlder(s, HISTORY);
    expect(searchValue(stuck, HISTORY)).toBe("fix the login redirect");
  });

  it("matches anywhere in the entry, not just the start", () => {
    let s = beginSearch("");
    for (const ch of "valid") s = searchType(s, HISTORY, ch);
    expect(searchValue(s, HISTORY)).toBe("add validation rules");
  });

  it("ignores case", () => {
    let s = beginSearch("");
    for (const ch of "LOGIN") s = searchType(s, HISTORY, ch);
    expect(searchValue(s, HISTORY)).toBe("fix the login redirect");
  });

  it("says so when nothing matches", () => {
    let s = beginSearch("");
    for (const ch of "zzz") s = searchType(s, HISTORY, ch);
    expect(searchValue(s, HISTORY)).toBe("");
    expect(searchLabel(s, HISTORY)).toMatch(/failed reverse-i-search/);
  });

  it("re-matches after a backspace", () => {
    let s = beginSearch("");
    for (const ch of "fixz") s = searchType(s, HISTORY, ch);
    expect(searchLabel(s, HISTORY)).toMatch(/failed/);
    s = searchBackspace(s, HISTORY);
    expect(searchValue(s, HISTORY)).toBe("fix the build");
  });

  it("keeps the draft so cancelling can restore it", () => {
    const s = beginSearch("half a thought");
    expect(s.draft).toBe("half a thought");
    expect(searchValue(s, HISTORY)).toBe("half a thought");
  });
});

describe("in the real input box", () => {
  let unmount: (() => void) | undefined;
  let dir: string;
  let home: string;
  const originalHome = process.env["BHARATBUILD_HOME"];

  beforeEach(() => {
    setGlyphs("ascii");
    home = fs.mkdtempSync(path.join(os.tmpdir(), "bb-srchhome-"));
    process.env["BHARATBUILD_HOME"] = home;
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-srch-"));
    saveHistory(HISTORY, dir);
  });
  afterEach(() => {
    unmount?.(); unmount = undefined;
    if (originalHome === undefined) delete process.env["BHARATBUILD_HOME"];
    else process.env["BHARATBUILD_HOME"] = originalHome;
    for (const d of [dir, home]) {
      try { fs.rmSync(d, { recursive: true, force: true }); } catch { /* windows lock */ }
    }
  });

  async function mount() {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const submitted: string[] = [];
    const app = render(<InputPrompt onSubmit={(v) => submitted.push(v)} historyCwd={dir} />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 70));
    return {
      frame: () => strip(last),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 70)); },
      submitted,
    };
  }

  it("opens a search line on ctrl+r", async () => {
    const h = await mount();
    await h.press(CTRL_R);
    expect(h.frame()).toContain("reverse-i-search");
  });

  it("finds an entry as the query is typed", async () => {
    const h = await mount();
    await h.press(CTRL_R);
    await h.press("valid");
    expect(h.frame()).toContain("add validation rules");
  });

  it("accepts the match into the box on enter", async () => {
    const h = await mount();
    await h.press(CTRL_R);
    await h.press("valid");
    await h.press(ENTER);
    const f = h.frame();
    expect(f).not.toContain("reverse-i-search");
    expect(f).toContain("add validation rules");
    expect(h.submitted, "accepting is not sending").toHaveLength(0);
  });

  it("restores what was being typed when cancelled", async () => {
    const h = await mount();
    await h.press("my draft");
    await h.press(CTRL_R);
    await h.press("valid");
    await h.press(ESC);
    const f = h.frame();
    expect(f).not.toContain("reverse-i-search");
    expect(f).toContain("my draft");
  });

  it("steps back through matches on a second ctrl+r", async () => {
    const h = await mount();
    await h.press(CTRL_R);
    await h.press("fix");
    expect(h.frame()).toContain("fix the build");
    await h.press(CTRL_R);
    expect(h.frame()).toContain("fix the login redirect");
  });
});

describe("the input box while searching", () => {
  it("does not also collect the query", async () => {
    // The text input was left mounted and received the same keys, so ctrl+r
    // then "valid" left "rvalid" sitting in the box behind the search line.
    const ESCC = String.fromCharCode(27);
    const clean = (s: string) => s.replace(new RegExp(`${ESCC}\[[0-9;?]*[A-Za-z]`, "g"), "");
    const fsx = await import("node:fs");
    const osx = await import("node:os");
    const px = await import("node:path");
    const { render: r } = await import("ink");
    const { PassThrough: PT } = await import("node:stream");
    const React2 = (await import("react")).default;
    const { InputPrompt: IP } = await import("../../src/ui/ink/InputPrompt.js");
    const { saveHistory: sh } = await import("../../src/ui/ink/prompt-history.js");

    const home = fsx.mkdtempSync(px.join(osx.tmpdir(), "bb-sh-"));
    process.env["BHARATBUILD_HOME"] = home;
    const d = fsx.mkdtempSync(px.join(osx.tmpdir(), "bb-sd-"));
    sh(["add validation rules"], d);

    const stdin: any = new PT();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PT();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (clean(s).trim()) last = s; });
    const app = r(React2.createElement(IP, { onSubmit: () => {}, historyCwd: d }), { stdout, stdin, patchConsole: false });
    await new Promise((res) => setTimeout(res, 70));
    stdin.write(String.fromCharCode(18));
    await new Promise((res) => setTimeout(res, 70));
    stdin.write("valid");
    await new Promise((res) => setTimeout(res, 70));
    const frame = clean(last);
    app.unmount();
    expect(frame, "the r and the query must not leak into the box").not.toContain("rvalid");
    expect(frame).toContain("add validation rules");
    try { fsx.rmSync(home, { recursive: true, force: true }); fsx.rmSync(d, { recursive: true, force: true }); } catch { /* lock */ }
  });
});
