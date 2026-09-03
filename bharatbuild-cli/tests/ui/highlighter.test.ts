/**
 * Shiki wiring. The hand-rolled tokenizer stays as the fallback, so these
 * cover both paths and the handover between them.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  highlightSync, subscribe, warmUp, isReady, resetHighlighter,
} from "../../src/ui/ink/highlighter.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";

/** Wait until the highlighter reports ready, or give up. */
async function ready(timeoutMs = 8000): Promise<boolean> {
  warmUp();
  const start = Date.now();
  while (!isReady() && Date.now() - start < timeoutMs) {
    await new Promise((r) => setTimeout(r, 25));
  }
  return isReady();
}

beforeEach(() => { resetHighlighter(); setInkTheme("dark"); });
afterEach(() => { resetHighlighter(); setInkTheme("dark"); });

describe("cold start", () => {
  it("returns null before the highlighter exists so the caller falls back", () => {
    expect(highlightSync(["const a = 1;"], "ts")).toBeNull();
  });

  it("never blocks — the first call is synchronous and immediate", () => {
    const t0 = Date.now();
    highlightSync(["const a = 1;"], "ts");
    expect(Date.now() - t0).toBeLessThan(50);
  });

  it("becomes ready and then serves tokens", async () => {
    expect(await ready()).toBe(true);
    const out = highlightSync(["const a = 1;"], "ts");
    expect(out).not.toBeNull();
    expect(out![0]!.some((t) => t.color)).toBe(true);
  });
});

describe("subscription is level-triggered", () => {
  it("notifies a subscriber that arrives after readiness", async () => {
    // notify() fires once when setup completes. An edge-triggered subscription
    // meant a component mounting a moment later kept fallback colours for the
    // whole session — and ~50ms setup is exactly when mounts happen.
    expect(await ready()).toBe(true);

    let fired = 0;
    subscribe(() => { fired++; });
    await new Promise((r) => setTimeout(r, 50));
    expect(fired).toBeGreaterThan(0);
  });

  it("hands back a working unsubscribe", async () => {
    expect(await ready()).toBe(true);
    let fired = 0;
    const off = subscribe(() => { fired++; });
    off();
    await new Promise((r) => setTimeout(r, 50));
    expect(fired).toBe(0);
  });
});

describe("grammar accuracy", () => {
  it("does not treat a keyword inside a string as a keyword", async () => {
    // The reason for using real grammars instead of a keyword list.
    expect(await ready()).toBe(true);
    const [line] = highlightSync(['const s = "import from";'], "ts")!;
    const kw = line!.find((t) => t.text === "const")!;
    const str = line!.find((t) => t.text.includes("import from"))!;
    expect(kw.color).toBeDefined();
    expect(str.color).toBeDefined();
    expect(str.color).not.toBe(kw.color);
    // The string is one token — "import" is not split out of it.
    expect(str.text).toContain('"import from"');
  });

  it("resolves a block comment that spans lines", async () => {
    expect(await ready()).toBe(true);
    const rows = highlightSync(["/* start", "still comment", "end */"], "ts")!;
    const colors = rows.map((r) => r[0]?.color);
    expect(colors[0]).toBe(colors[1]);
    expect(colors[1]).toBe(colors[2]);
  });

  it("aligns output rows with input lines", async () => {
    expect(await ready()).toBe(true);
    const lines = ["const a = 1;", "", "const b = 2;"];
    expect(highlightSync(lines, "ts")!).toHaveLength(lines.length);
  });
});

describe("when it should stay out of the way", () => {
  it("declines plain text", () => {
    expect(highlightSync(["just words"], "plain")).toBeNull();
  });

  it("is disabled under the safe theme", async () => {
    setInkTheme("safe");
    warmUp();
    await new Promise((r) => setTimeout(r, 100));
    expect(highlightSync(["const a = 1;"], "ts")).toBeNull();
  });

  it("serves python as well as typescript", async () => {
    expect(await ready()).toBe(true);
    const out = highlightSync(["def go(n):", "    return n * 2"], "py");
    expect(out).not.toBeNull();
    expect(out![0]!.some((t) => t.color)).toBe(true);
  });
});
