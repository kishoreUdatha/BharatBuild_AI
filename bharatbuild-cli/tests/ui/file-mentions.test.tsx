/**
 * `@file` mentions.
 *
 * Pointing the agent at a file used to mean typing the path into a sentence
 * and hoping the model read it — which it often did not, answering from the
 * name alone. A mention attaches the file to the message instead.
 *
 * The parsing cases are the ones worth guarding: an email address is not a
 * mention, and a path at the end of a clause should not swallow the comma.
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
  activeMention, applyMention, parseMentions, readMention, expandMentions,
} from "../../src/ui/ink/file-mentions.js";
import { listProjectFiles, clearFileIndex } from "../../src/ui/ink/file-index.js";

const ESC = String.fromCharCode(27);
const TAB = "\t";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

describe("spotting the mention being typed", () => {
  it("sees a bare @", () => {
    expect(activeMention("@")).toEqual({ query: "", start: 0 });
  });

  it("sees one mid-sentence", () => {
    const m = activeMention("explain @src/ap");
    expect(m?.query).toBe("src/ap");
    expect("explain @src/ap".slice(m!.start)).toBe("@src/ap");
  });

  it("ignores an email address", () => {
    // No whitespace before the @, so it is not a mention.
    expect(activeMention("write to user@example")).toBeNull();
  });

  it("stops once the mention is finished", () => {
    // A trailing space means the user moved on; the picker should close.
    expect(activeMention("look at @src/app.ts ")).toBeNull();
  });

  it("only tracks the token at the caret", () => {
    const m = activeMention("compare @a.ts with @b");
    expect(m?.query).toBe("b");
  });
});

describe("completing one", () => {
  it("replaces the typed fragment with the chosen path", () => {
    const value = "explain @src/ap";
    const m = activeMention(value)!;
    expect(applyMention(value, m, "src/app.ts")).toBe("explain @src/app.ts ");
  });

  it("leaves a trailing space so the sentence can continue", () => {
    const value = "@";
    expect(applyMention(value, activeMention(value)!, "a.ts")).toBe("@a.ts ");
  });

  it("produces a value the picker no longer matches", () => {
    const value = "@sr";
    const next = applyMention(value, activeMention(value)!, "src/app.ts");
    expect(activeMention(next)).toBeNull();
  });
});

describe("finding mentions in a sent message", () => {
  it("finds several", () => {
    expect(parseMentions("compare @a.ts and @b/c.ts")).toEqual(["a.ts", "b/c.ts"]);
  });

  it("leaves an email address alone", () => {
    expect(parseMentions("mail user@example.com about it")).toEqual([]);
  });

  it("does not swallow trailing punctuation", () => {
    // "see @src/app.ts, then…" must not look for a file ending in a comma.
    expect(parseMentions("see @src/app.ts, then run it")).toEqual(["src/app.ts"]);
  });

  it("de-duplicates a repeated mention", () => {
    expect(parseMentions("@a.ts and again @a.ts")).toEqual(["a.ts"]);
  });

  it("finds one at the very start", () => {
    expect(parseMentions("@a.ts explain this")).toEqual(["a.ts"]);
  });
});

describe("attaching the file", () => {
  let dir: string;
  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-mention-"));
    fs.writeFileSync(path.join(dir, "app.ts"), "export const a = 1;");
    fs.mkdirSync(path.join(dir, "sub"));
  });
  afterEach(() => {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  it("includes the contents", () => {
    const out = expandMentions("explain @app.ts", dir);
    expect(out).toContain("export const a = 1;");
    expect(out).toContain("### app.ts");
  });

  it("leaves the user's own words exactly as typed", () => {
    // The transcript shows what was typed; rewriting it would make the two
    // disagree about what was sent.
    expect(expandMentions("explain @app.ts", dir).startsWith("explain @app.ts")).toBe(true);
  });

  it("does nothing to a message with no mentions", () => {
    expect(expandMentions("just a question", dir)).toBe("just a question");
  });

  it("reports a missing file instead of failing the message", () => {
    // The user may well be talking about a file that does not exist yet.
    const out = expandMentions("make @nope.ts", dir);
    expect(out).toContain("nope.ts");
    expect(out).toContain("could not be read");
  });

  it("refuses a directory", () => {
    expect(readMention("sub", dir).error).toMatch(/directory/);
  });

  it("truncates a very long file rather than sending all of it", () => {
    fs.writeFileSync(path.join(dir, "big.txt"), "x\n".repeat(3000));
    const att = readMention("big.txt", dir);
    expect(att.content).toContain("more lines not shown");
    expect(att.content.split("\n").length).toBeLessThan(2100);
  });

  it("skips a file too large to be worth attaching", () => {
    fs.writeFileSync(path.join(dir, "huge.bin"), "x".repeat(300 * 1024));
    expect(readMention("huge.bin", dir).error).toMatch(/too large/);
  });
});

describe("the file index", () => {
  let dir: string;
  beforeEach(() => {
    clearFileIndex();
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-index-"));
    fs.mkdirSync(path.join(dir, "src"));
    fs.writeFileSync(path.join(dir, "src", "app.ts"), "x");
    fs.writeFileSync(path.join(dir, "readme.md"), "x");
    fs.mkdirSync(path.join(dir, "node_modules", "pkg"), { recursive: true });
    fs.writeFileSync(path.join(dir, "node_modules", "pkg", "index.js"), "x");
    fs.mkdirSync(path.join(dir, ".git"));
    fs.writeFileSync(path.join(dir, ".git", "config"), "x");
  });
  afterEach(() => {
    clearFileIndex();
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  it("lists project files with forward slashes on every platform", () => {
    expect(listProjectFiles(dir)).toContain("src/app.ts");
  });

  it("leaves out node_modules and dot directories", () => {
    const files = listProjectFiles(dir);
    expect(files.some((f) => f.includes("node_modules"))).toBe(false);
    expect(files.some((f) => f.includes(".git"))).toBe(false);
  });

  it("caches so a keystroke does not re-walk the tree", () => {
    const first = listProjectFiles(dir, 1_000);
    fs.writeFileSync(path.join(dir, "new.ts"), "x");
    expect(listProjectFiles(dir, 1_500)).toBe(first);
  });

  it("picks up a file the agent just wrote once the cache expires", () => {
    // A picker that cannot see the file written a moment ago is worse than a
    // slow one.
    listProjectFiles(dir, 1_000);
    fs.writeFileSync(path.join(dir, "new.ts"), "x");
    expect(listProjectFiles(dir, 9_000)).toContain("new.ts");
  });
});

describe("the picker in the real input box", () => {
  let unmount: (() => void) | undefined;
  let dir: string;

  beforeEach(() => {
    setGlyphs("ascii");
    clearFileIndex();
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-pick-"));
    fs.mkdirSync(path.join(dir, "src"));
    fs.writeFileSync(path.join(dir, "src", "server.ts"), "x");
    fs.writeFileSync(path.join(dir, "src", "client.ts"), "x");
  });
  afterEach(() => {
    unmount?.(); unmount = undefined; clearFileIndex();
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
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
      <InputPrompt onSubmit={(v) => submitted.push(v)} historyCwd={dir} />,
      { stdout, stdin, patchConsole: false },
    );
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    return {
      frame: () => strip(last),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 70)); },
      submitted,
    };
  }

  it("offers project files on @", async () => {
    const h = await mount();
    await h.press("@");
    expect(h.frame()).toContain("src/server.ts");
  });

  it("narrows as the path is typed", async () => {
    const h = await mount();
    await h.press("@serv");
    const f = h.frame();
    expect(f).toContain("src/server.ts");
    expect(f).not.toContain("src/client.ts");
  });

  it("completes into the sentence rather than sending it", async () => {
    const h = await mount();
    await h.press("explain @serv");
    await h.press(TAB);
    expect(h.frame()).toContain("@src/server.ts");
    expect(h.submitted, "nothing sent by completing").toHaveLength(0);
  });

  it("keeps the words already typed", async () => {
    const h = await mount();
    await h.press("explain @serv");
    await h.press(TAB);
    expect(h.frame()).toContain("explain @src/server.ts");
  });

  it("does not open on an email address", async () => {
    const h = await mount();
    await h.press("mail me@example");
    expect(h.frame()).not.toContain("src/server.ts");
  });
});

describe("how the picker labels files", () => {
  let unmount2: (() => void) | undefined;
  afterEach(() => { unmount2?.(); unmount2 = undefined; });

  it("prefixes paths with @, not /", async () => {
    // The overlay was written for slash commands and hardcoded the "/", so
    // reusing it for mentions listed every file as "/README.md" — a path that
    // does not exist and is not what gets inserted.
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-sigil-"));
    fs.writeFileSync(path.join(dir, "README.md"), "x");
    clearFileIndex();

    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const app = render(<InputPrompt onSubmit={() => {}} historyCwd={dir} />, { stdout, stdin, patchConsole: false });
    unmount2 = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    stdin.write("@");
    await new Promise((r) => setTimeout(r, 90));

    const frame = strip(last);
    expect(frame).toContain("@README.md");
    expect(frame, "no bogus leading slash").not.toContain("/README.md");
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  it("still prefixes commands with /", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-sigil2-"));
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const app = render(<InputPrompt onSubmit={() => {}} historyCwd={dir} />, { stdout, stdin, patchConsole: false });
    unmount2 = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    stdin.write("/he");
    await new Promise((r) => setTimeout(r, 90));
    expect(strip(last)).toContain("/help");
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
  });
});
