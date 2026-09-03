/**
 * `!command` — run the shell without spending a model turn.
 *
 * Checking the branch, whether the build passes, or what a directory holds
 * meant either leaving the session or asking the agent to run it, which cost a
 * whole turn and a model call to do something the user could type directly.
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
import { App } from "../../src/ui/ink/App.js";
import { executeCommand, runUserCommand } from "../../src/tools/shell/index.js";

const ESC = String.fromCharCode(27);
const ENTER = "\r";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => setGlyphs("ascii"));
afterEach(() => { unmount?.(); unmount = undefined; });

describe("who the blocklist is for", () => {
  it("still stops the model from running a destructive command", async () => {
    // The rails exist to gate a decision the model made on its own.
    const r = await executeCommand({ command: "git push --force origin main" });
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/blocked/i);
  });

  it("does not second-guess the same command typed by the user", async () => {
    // Typing it character by character is already an explicit instruction.
    // Refusing would make this prompt less useful than the shell it stands in
    // front of. It is not run here — only the guard is checked, by using a
    // command that is on the list but harmless.
    const r = await runUserCommand({ command: "chmod --help" });
    expect(r.content).not.toMatch(/^Command blocked/);
  });

  it("still reports a real failure from a user command", async () => {
    const r = await runUserCommand({ command: "exit 3" });
    expect(r.isError).toBe(true);
  });

  it("returns output for a user command that works", async () => {
    const r = await runUserCommand({ command: "node -v" });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/v\d+/);
  });
});

describe("the prompt while a command is typed", () => {
  async function mount() {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 80; stdout.rows = 24;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-bang-"));
    const app = render(<InputPrompt onSubmit={() => {}} historyCwd={dir} />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 60));
    return {
      frame: () => strip(last),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 60)); },
    };
  }

  it("shows > normally", async () => {
    const h = await mount();
    await h.press("hello");
    expect(h.frame()).toContain("> hello");
  });

  it("switches the marker to ! so Enter is not a surprise", async () => {
    const h = await mount();
    await h.press("!npm test");
    expect(h.frame()).toContain("! !npm test");
  });

  it("does not open the command palette for !", async () => {
    const h = await mount();
    await h.press("!he");
    expect(h.frame()).not.toContain("/help");
  });
});

describe("running one from the session", () => {
  let dir: string;
  let pushed: Array<{ role: string; content: string }>;

  const makeRuntime = () => ({
    on: () => {},
    off: () => {},
    run: async () => {},
    context: { push: (m: any) => pushed.push(m) },
  });

  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-bangapp-"));
    pushed = [];
  });
  afterEach(() => {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
  });

  async function mountApp() {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 90; stdout.rows = 40;
    let all = "";
    stdout.on("data", (c: Buffer) => { all += c.toString(); });
    const app = render(
      <App runtime={makeRuntime()} model="auto" initialMode="ask" />,
      { stdout, stdin, patchConsole: false },
    );
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 200));
    return {
      // Everything printed, since finished output goes to <Static> and is
      // never repainted into a later frame.
      all: () => strip(all),
      press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 120)); },
    };
  }

  it("runs the command and shows its output", async () => {
    const h = await mountApp();
    await h.press("!node -v");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 900));
    expect(h.all()).toMatch(/v\d+/);
  }, 20_000);

  it("tells the model what was run, so a follow-up can build on it", async () => {
    // Without this the output is on screen but absent from the conversation,
    // and the next question gets an answer that ignores it.
    const h = await mountApp();
    await h.press("!node -v");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 900));
    expect(pushed).toHaveLength(1);
    expect(pushed[0]!.role).toBe("user");
    expect(pushed[0]!.content).toContain("node -v");
    expect(pushed[0]!.content).toMatch(/v\d+/);
  }, 20_000);

  it("never starts a model turn", async () => {
    // runtime.run is what costs a call; a shell check must not spend one.
    let ran = 0;
    const runtime = { on: () => {}, off: () => {}, run: async () => { ran++; }, context: { push: () => {} } };
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 90; stdout.rows = 40;
    stdout.on("data", () => {});
    const app = render(<App runtime={runtime} model="auto" initialMode="ask" />, { stdout, stdin, patchConsole: false });
    unmount = () => app.unmount();
    await new Promise((r) => setTimeout(r, 200));
    stdin.write("!node -v");
    await new Promise((r) => setTimeout(r, 120));
    stdin.write(ENTER);
    await new Promise((r) => setTimeout(r, 900));
    expect(ran).toBe(0);
  }, 20_000);

  it("says what to do when ! is sent on its own", async () => {
    const h = await mountApp();
    await h.press("!");
    await h.press(ENTER);
    await new Promise((r) => setTimeout(r, 300));
    expect(h.all()).toMatch(/Type a command after !/);
  }, 20_000);
});
