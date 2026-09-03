/**
 * The live region must never be as tall as the viewport.
 *
 * Ink erases a frame by moving the cursor up by that frame's height. A region
 * the full height of the terminal leaves that erase no margin — writing N
 * lines into an N-row terminal scrolls by one, and every erase after that is
 * off by one, so the interface ends up on screen twice. Two attempts at
 * bottom-anchoring (a computed spacer, then flexbox `height={rows}`) both hit
 * this on a real terminal.
 *
 * NOTE ON THE HARNESS: the VirtualTerminal here models cursor movement and
 * erase, but it did NOT reproduce the duplication that a real terminal showed.
 * It is useful for catching gross layout errors and useless for certifying
 * this particular class of bug. Treat a pass here as necessary, not
 * sufficient, and confirm scroll-sensitive changes in a real terminal.
 */
import { describe, it, expect, afterEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { App } from "../../src/ui/ink/App.js";
import { VirtualTerminal } from "../helpers/vt.js";
import { makeRuntime } from "../helpers/ink-harness.js";

let unmount: (() => void) | undefined;
afterEach(() => { unmount?.(); unmount = undefined; });

async function paint(rows: number, cols = 100, settle = 400): Promise<VirtualTerminal> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = cols; stdout.rows = rows;

  const vt = new VirtualTerminal(cols, rows);
  stdout.on("data", (c: Buffer) => vt.write(c.toString()));

  const app = render(<App runtime={makeRuntime()} model="auto" mode="developer" />,
    { stdin, stdout, exitOnCtrlC: false, patchConsole: false });
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, settle));
  return vt;
}

describe("the interface is drawn once", () => {
  it.each([20, 28, 40])("at %i rows", async (rows) => {
    // Padding by `rows - <estimate>` once made the region taller than the
    // viewport; the terminal scrolled, Ink's cursor-up erase could not reach
    // the scrolled-off rows, and the whole UI stayed on screen twice.
    const vt = await paint(rows);
    expect(vt.countVisible("BharatBuild AI")).toBe(1);
    expect(vt.countVisible("Type a message")).toBe(1);
  });
});

describe("the prompt follows the conversation", () => {
  it.each([20, 28, 40])("sits just under the welcome panel at %i rows", async (rows) => {
    // It used to be pinned to the viewport bottom by blank spacers, which
    // bought a motionless input at the price of a permanent band of empty
    // rows between a short reply and the prompt. claude-code does not pin —
    // its prompt sits under the last line of output — so neither does this.
    const vt = await paint(rows);
    const promptRow = vt.lastRowOf("Type a message");
    const panelRow = vt.lastRowOf("cwd:");
    expect(panelRow, "welcome panel is on screen").toBeGreaterThanOrEqual(0);
    expect(promptRow, "prompt is below the panel").toBeGreaterThan(panelRow);
    // Close under it, not parked at the bottom of the terminal.
    expect(promptRow - panelRow).toBeLessThan(8);
  });

  it("still shows the welcome panel above it", async () => {
    // The emptiness check counted spacers as content, which made the welcome
    // panel vanish the moment any padding was printed.
    const vt = await paint(40);
    expect(vt.countVisible("BharatBuild AI")).toBe(1);
    expect(vt.lastRowOf("BharatBuild AI")).toBeLessThan(vt.lastRowOf("Type a message"));
  });

  it("leaves the live region far shorter than the viewport", async () => {
    // The invariant behind the whole design: however much is printed above,
    // the region ink has to erase each frame stays a handful of rows.
    //
    // This measured from the banner, which was live at the time. The banner is
    // printed into <Static> now, so that span is the whole screen rather than
    // the live region - it has to start at the input box instead.
    const vt = await paint(40);
    const top = vt.lastRowOf("Type a message");
    const bottom = vt.lastRowOf("idle");
    expect(bottom - top).toBeLessThan(6);
  });
});

describe("a very short terminal", () => {
  it("does not pad when there is no room, and still draws once", async () => {
    // Below the threshold the padding would push the prompt off the screen.
    const vt = await paint(12);
    expect(vt.countVisible("Type a message")).toBe(1);
  });
});

describe("the prompt does not move during a turn", () => {
  // The input box renders below the live region, so its position used to be
  // whatever that region happened to contain: ~4 rows idle, ~19 mid-turn with
  // a reply streaming and a tool running. The prompt slid down as the answer
  // arrived and snapped back when it was committed.
  async function promptRowsAcrossATurn(rows: number): Promise<number[]> {
    const stdin: any = new PassThrough();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PassThrough();
    stdout.isTTY = true; stdout.columns = 100; stdout.rows = rows;
    const vt = new VirtualTerminal(100, rows);
    stdout.on("data", (c: Buffer) => vt.write(c.toString()));

    const rt: any = makeRuntime();
    rt.run = async () => {};
    const app = render(
      <App runtime={rt} model="auto" mode="developer" initialMode="auto" />,
      { stdin, stdout, exitOnCtrlC: false, patchConsole: false },
    );
    unmount = () => app.unmount();

    const seen: number[] = [];
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
    await wait(350);
    seen.push(vt.lastRowOf("Type a message"));

    await rt.events.emit({ type: "text", content: "Working on it.", delta: true, timestamp: 1 });
    await wait(150);
    seen.push(vt.lastRowOf("Type a message"));

    // Far more text than the pane can show — the cap has to absorb it.
    const long = Array.from({ length: 30 }, (_, i) => `line ${i}`).join("\n");
    await rt.events.emit({ type: "text", content: `\n${long}`, delta: true, timestamp: 2 });
    await wait(150);
    seen.push(vt.lastRowOf("Type a message"));

    await rt.events.emit({ type: "tool_call", id: "t1", toolName: "write_file", input: { path: "a.ts" }, timestamp: 3 });
    await wait(150);
    seen.push(vt.lastRowOf("Type a message"));

    await rt.events.emit({ type: "tool_result", id: "t1", toolName: "write_file", output: "ok", isError: false, durationMs: 5, timestamp: 4 });
    await rt.events.emit({ type: "complete", totalTokens: 10, turns: 1, durationMs: 5, inputTokens: 5, outputTokens: 5, timestamp: 5 });
    await wait(250);
    seen.push(vt.lastRowOf("Type a message"));

    return seen;
  }

  it.each([24, 30, 40])("does not drift as more output streams in at %i rows", async (rows) => {
    // Samples: [idle, first text, a screenful of text, tool running, complete].
    //
    // The guarantee that matters is samples 1 and 2: however much text
    // arrives, the input must not move under the user's hands. That was the
    // original complaint and it still holds — the pane is a fixed height for
    // as long as it holds anything, and the tail is capped to fit.
    const seen = await promptRowsAcrossATurn(rows);
    expect(seen[1], `moved while streaming: ${seen[1]} then ${seen[2]}`).toBe(seen[2]);
  });

  it.each([24, 30, 40])("reclaims the reserved rows when idle at %i rows", async (rows) => {
    // The point of dropping the pin: no dead band under a finished reply.
    // The prompt does move when the pane opens and closes — a tool card
    // appearing pushes it down, as it does in claude-code — but it must end
    // up above where it sat mid-turn, not parked below it.
    const seen = await promptRowsAcrossATurn(rows);
    const busiest = Math.max(...seen.slice(1, 4));
    expect(seen[0], "idle before the turn").toBeLessThanOrEqual(busiest);
    expect(seen[4], "idle after the turn").toBeLessThanOrEqual(busiest);
  });
});

describe("the live region is anchored to the bottom", () => {
  it("declares flex-end on the fixed-height pane", () => {
    const fs = require("node:fs") as typeof import("node:fs");
    const path = require("node:path") as typeof import("node:path");
    const src = fs.readFileSync(
      path.resolve(__dirname, "../../src/ui/ink/App.tsx"), "utf8",
    );
    const pane = src.slice(src.indexOf("height={liveActive"));
    const open = pane.slice(0, pane.indexOf(">"));
    expect(open, "live pane keeps a fixed height while a turn runs")
      .toContain("height={liveActive ? liveRows : 0}");
    expect(open, "and is anchored to the end").toContain('justifyContent="flex-end"');
  });

  it("keeps overflow hidden so it cannot outgrow its reserved rows", () => {
    // Ink erases a frame by cursor-up over its height; a live region that
    // grows past what was reserved outruns the erase and duplicates.
    const fs = require("node:fs") as typeof import("node:fs");
    const path = require("node:path") as typeof import("node:path");
    const src = fs.readFileSync(
      path.resolve(__dirname, "../../src/ui/ink/App.tsx"), "utf8",
    );
    const pane = src.slice(src.indexOf("height={liveActive"));
    expect(pane.slice(0, pane.indexOf(">"))).toContain('overflow="hidden"');
  });
});

/**
 * The status bar has to stay one row.
 *
 * It is counted in FIXED_ROWS, so a second row shifts everything above it —
 * and at 68 columns it wrapped, collapsing the gaps into "default· esc to /
 * interrupt". The existing width gates only shed the right-hand figures; the
 * left group grew unchecked.
 */
describe("the status bar at narrow widths", () => {
  const ESCC = String.fromCharCode(27);
  const clean = (s: string) => s.replace(new RegExp(`${ESCC}\[[0-9;?]*[A-Za-z]`, "g"), "");

  async function rowsAt(cols: number): Promise<string[]> {
    const { render: r } = await import("ink");
    const { StatusBar } = await import("../../src/ui/ink/StatusBar.js");
    const { PassThrough: PT } = await import("node:stream");
    const React2 = (await import("react")).default;
    const stdin: any = new PT();
    stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
    const stdout: any = new PT();
    stdout.isTTY = true; stdout.columns = cols; stdout.rows = 20;
    let last = "";
    stdout.on("data", (c: Buffer) => { const s = c.toString(); if (clean(s).trim()) last = s; });
    const app = r(
      React2.createElement(StatusBar, {
        model: "auto", agent: "default", tokenCount: 16, creditBalance: 0,
        phase: "streaming" as const, elapsedSec: 0, permMode: "auto" as const, streamingTokens: 16,
      }),
      { stdout, stdin, patchConsole: false },
    );
    await new Promise((res) => setTimeout(res, 80));
    app.unmount();
    return clean(last).split("\n").filter((l) => l.trim());
  }

  it("stays on one row at 60 columns", async () => {
    expect(await rowsAt(60)).toHaveLength(1);
  });

  it("stays on one row at 68 columns", async () => {
    // The width that produced the wrap.
    expect(await rowsAt(68)).toHaveLength(1);
  });

  it("still shows the agent and the hint when there is room", async () => {
    // Shedding must be a narrow-terminal concession, not a permanent loss.
    const wide = (await rowsAt(100))[0]!;
    expect(wide).toContain("default");
    expect(wide).toMatch(/esc to interrupt/);
  });

  it("keeps what matters most when narrow", async () => {
    // Whatever is dropped, the mode badge has to survive: it says whether the
    // agent will stop before writing to disk.
    expect((await rowsAt(60))[0]!).toContain("auto-accept");
  });
});

