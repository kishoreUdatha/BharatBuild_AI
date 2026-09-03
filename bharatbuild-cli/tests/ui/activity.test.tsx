/**
 * A static "coding 47s" gives no sign of life on a long turn, and a wall of
 * near-identical shell cards is unreadable. These cover the rotating status
 * verb, the tip line, and the "Ran N shell commands" roll-up.
 */
import { describe, it, expect, afterEach } from "vitest";
import {
  activityVerb, activityTip, formatElapsed, formatTokens, ACTIVITY_VERBS, TIPS,
} from "../../src/ui/ink/activity.js";
import { mountApp, makeRuntime, keys, type Harness } from "../helpers/ink-harness.js";

let h: Harness | undefined;
afterEach(() => { h?.unmount(); h = undefined; });

describe("activity verb", () => {
  it("is stable within its hold window", () => {
    // Repaints happen many times a second; the word must not flicker.
    expect(activityVerb(0)).toBe(activityVerb(5));
  });

  it("changes once the window passes", () => {
    expect(activityVerb(0)).not.toBe(activityVerb(6));
  });

  it("cycles rather than running out", () => {
    const far = activityVerb(6 * ACTIVITY_VERBS.length);
    expect(ACTIVITY_VERBS).toContain(far as never);
  });

  it("handles a negative elapsed without throwing", () => {
    expect(activityVerb(-5)).toBeTruthy();
  });
});

describe("tips", () => {
  it("rotates on a slower cadence than the verb", () => {
    expect(activityTip(0)).toBe(activityTip(11));
    expect(activityTip(0)).not.toBe(activityTip(12));
  });

  it("only mentions things the CLI actually has", () => {
    // A tip for a feature that does not exist is worse than no tip.
    const commands = TIPS.join(" ").match(/\/[a-z-]+/g) ?? [];
    const known = new Set([
      "/plan", "/rewind", "/context", "/checkpoint", "/usage", "/compact",
    ]);
    for (const c of commands) expect(known.has(c), `${c} is not a real command`).toBe(true);
  });

  it("stays inside 7-bit ASCII", () => {
    const bad = TIPS.join("").split("").filter((c) => c.charCodeAt(0) > 126);
    expect(bad).toEqual([]);
  });
});

describe("formatting", () => {
  it.each([
    [0, "0s"], [45, "45s"], [60, "1m 0s"], [529, "8m 49s"],
  ])("formats %is as %s", (secs, expected) => {
    expect(formatElapsed(secs)).toBe(expected);
  });

  it.each([
    [0, "0"], [999, "999"], [19_500, "19.5k"], [1_200_000, "1.2M"],
  ])("formats %i tokens as %s", (n, expected) => {
    expect(formatTokens(n)).toBe(expected);
  });
});

/** A runtime that runs `count` shell commands then waits to be released. */
function shellRuntime(count: number, toolName = "execute_command") {
  let release!: () => void;
  const gate = new Promise<void>((r) => { release = r; });
  const rt = makeRuntime({
    async run() {
      for (let i = 0; i < count; i++) {
        await rt.events.emit({ type: "tool_call", id: `s${i}`, toolName, input: { command: `cmd ${i}` }, timestamp: 1 });
        await rt.events.emit({ type: "tool_result", id: `s${i}`, toolName, output: "ok", isError: false, durationMs: 5, timestamp: 2 });
      }
      await rt.events.emit({ type: "usage", inputTokens: 19_000, outputTokens: 500, timestamp: 3 });
      await gate;
      await rt.events.emit({ type: "complete", totalTokens: 19_500, turns: 1, durationMs: 1, inputTokens: 19_000, outputTokens: 500, timestamp: 4 });
    },
  });
  return { rt, release: () => release() };
}

describe("status line while working", () => {
  it("shows a verb, elapsed time and token count", async () => {
    const { rt, release } = shellRuntime(1);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(600);

    const f = h.frame();
    expect(f).toMatch(new RegExp(`(${ACTIVITY_VERBS.join("|")})`));
    expect(f).toContain("19.5k tok");
    release();
    await h.wait(500);
  });

  it("hangs a tip under the status line", async () => {
    const { rt, release } = shellRuntime(1);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(600);
    expect(h.frame()).toContain("Tip:");
    release();
    await h.wait(500);
  });

  it("drops the verb and tip once idle", async () => {
    const { rt, release } = shellRuntime(1);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(400);
    release();
    await h.wait(900);
    expect(h.frame()).not.toContain("Tip:");
    expect(h.frame()).toContain("idle");
  });
});

describe("roll-up", () => {
  it("summarises a run of shell commands", async () => {
    const { rt, release } = shellRuntime(3);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("build and test");
    await h.press(keys.enter);
    await h.wait(500);
    release();
    await h.wait(900);
    expect(h.output()).toContain("Ran 3 shell commands");
  });

  it("does not summarise a single call", async () => {
    const { rt, release } = shellRuntime(1);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("one thing");
    await h.press(keys.enter);
    await h.wait(500);
    release();
    await h.wait(900);
    expect(h.output()).not.toMatch(/Ran \d+ shell command/);
  });

  it("still shows each individual tool card", async () => {
    // The roll-up is a summary, not a replacement — the detail must survive.
    const { rt, release } = shellRuntime(3);
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(500);
    release();
    await h.wait(900);
    const out = h.output();
    expect(out).toContain("cmd 0");
    expect(out).toContain("cmd 2");
  });

  it("does not roll up tools that are not repetitive", async () => {
    const { rt, release } = shellRuntime(3, "write_file");
    h = await mountApp({ runtime: rt, columns: 110 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(500);
    release();
    await h.wait(900);
    expect(h.output()).not.toMatch(/Ran \d+/);
  });
});
