/**
 * The prompt used to be replaced by the word "waiting…" for the whole turn, so
 * on a long run the keyboard was dead for minutes. Both reference CLIs keep the
 * input live and buffer what you type. These tests pin that behaviour.
 */
import { describe, it, expect, afterEach } from "vitest";
import { mountApp, makeRuntime, keys, type Harness } from "../helpers/ink-harness.js";

let h: Harness | undefined;
afterEach(() => { h?.unmount(); h = undefined; });

/** A runtime whose turn only finishes when the test releases it. */
function gatedRuntime() {
  let release!: () => void;
  const gate = new Promise<void>((r) => { release = r; });
  const rt = makeRuntime({
    async run(input: string) {
      rt.calls.push(input);
      await rt.events.emit({ type: "status", message: "working", phase: "coding", timestamp: 1 });
      await gate;
      await rt.events.emit({ type: "text", content: `done:${input}`, delta: true, timestamp: 2 });
      await rt.events.emit({
        type: "complete", totalTokens: 10, turns: 1, durationMs: 1,
        inputTokens: 5, outputTokens: 5, timestamp: 3,
      });
    },
  });
  return { rt, release: () => release() };
}

describe("input stays usable during a turn", () => {
  it("does not replace the prompt with 'waiting…'", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);

    expect(h.frame()).not.toContain("waiting…");
    release();
    await h.wait(600);
  });

  it("accepts typing while the agent is working", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);

    await h.type("typed while busy");
    expect(h.frame()).toContain("typed while busy");
    release();
    await h.wait(600);
  });
});

describe("queueing", () => {
  it("buffers a submission instead of starting a second turn", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);

    await h.type("second");
    await h.press(keys.enter);
    await h.wait(300);

    // Still only the first turn running.
    expect(rt.calls).toEqual(["first"]);
    release();
    await h.wait(900);
  });

  it("shows the queued count and the pending text", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);
    await h.type("queued message");
    await h.press(keys.enter);
    await h.wait(300);

    const f = h.frame();
    expect(f).toContain("1 queued");
    expect(f).toContain("queued message");
    release();
    await h.wait(900);
  });

  it("sends the queued message once the turn ends", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);
    await h.type("second");
    await h.press(keys.enter);
    await h.wait(300);

    release();
    await h.wait(1200);
    expect(rt.calls).toEqual(["first", "second"]);
  });

  it("clears the queue indicator after draining", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(400);
    await h.type("second");
    await h.press(keys.enter);
    await h.wait(300);
    release();
    await h.wait(1500);
    expect(h.frame()).not.toContain("queued");
  });

  it("keeps queued order across several messages", async () => {
    // Regression: draining routed back through the queue guard, which could
    // re-queue the message instead of sending it.
    const rt = makeRuntime({
      async run(input: string) {
        rt.calls.push(input);
        await rt.events.emit({ type: "text", content: "ok", delta: true, timestamp: 1 });
        await new Promise((r) => setTimeout(r, 120));
        await rt.events.emit({
          type: "complete", totalTokens: 1, turns: 1, durationMs: 1,
          inputTokens: 1, outputTokens: 0, timestamp: 2,
        });
      },
    });
    h = await mountApp({ runtime: rt });
    for (const p of ["one", "two", "three"]) {
      await h.type(p);
      await h.press(keys.enter);
      await h.wait(60);
    }
    await h.wait(2500);
    expect(rt.calls).toEqual(["one", "two", "three"]);
  });
});

describe("interrupting", () => {
  it("advertises esc while working", async () => {
    const { rt, release } = gatedRuntime();
    h = await mountApp({ runtime: rt });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(400);
    expect(h.frame()).toContain("esc to interrupt");
    release();
    await h.wait(600);
  });

  it("does not advertise esc when idle", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    expect(h.frame()).not.toContain("esc to interrupt");
  });

  it("cancels the turn on esc", async () => {
    const { rt, release } = gatedRuntime();
    let cancelled = false;
    rt.cancel = () => { cancelled = true; };
    h = await mountApp({ runtime: rt });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(400);

    await h.press(keys.esc);
    await h.wait(300);
    expect(cancelled).toBe(true);
    expect(h.output()).toContain("Interrupted");
    release();
    await h.wait(400);
  });

  it("esc dismisses the palette rather than interrupting when it is open", async () => {
    const { rt, release } = gatedRuntime();
    let cancelled = false;
    rt.cancel = () => { cancelled = true; };
    h = await mountApp({ runtime: rt });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(400);

    await h.type("/");            // palette opens mid-turn
    await h.press(keys.esc);      // should close it, not kill the turn
    await h.wait(300);
    expect(cancelled).toBe(false);
    release();
    await h.wait(600);
  });
});

describe("status bar fits its terminal", () => {
  // With the interrupt hint and queue count both present the row overflowed at
  // 100 columns and words ran together ("developerauto", "queuedctx").
  it.each([80, 100, 130])("keeps words separated at %i columns", async (columns) => {
    const rt = makeRuntime({
      async run() {
        await rt.events.emit({ type: "status", message: "w", phase: "coding", timestamp: 1 });
        await new Promise((r) => setTimeout(r, 900));
      },
    });
    h = await mountApp({ runtime: rt, columns, rows: 24 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(300);
    await h.type("queued one");
    await h.press(keys.enter);
    await h.wait(300);

    const bar = h.frame().split("\n").find((l) => l.includes("BharatBuild")) ?? "";
    expect(bar, bar).not.toMatch(/developerauto|queuedctx|toks|interrupt\d/);
    expect(bar.length).toBeLessThanOrEqual(columns + 1);
    await h.wait(800);
  });
});
