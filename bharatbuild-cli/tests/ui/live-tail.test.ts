/**
 * The whole in-flight reply was rendered in the live region, so it grew with
 * the answer. Ink erases a frame by moving the cursor up by that frame's
 * height; once the region nears the viewport the erase stops reaching, the
 * terminal scrolls, and a stale copy is left behind. A real session ended with
 * its closing message on screen twice, the second copy truncated with a border
 * character embedded in it.
 */
import { describe, it, expect } from "vitest";
import { liveTail, LIVE_TAIL_LINES } from "../../src/ui/ink/live-tail.js";

const lines = (n: number) => Array.from({ length: n }, (_, i) => `line${i + 1}`).join("\n");

describe("bounding the live region", () => {
  it("leaves a short reply untouched", () => {
    expect(liveTail("one\ntwo\nthree")).toBe("one\ntwo\nthree");
  });

  it("caps a long reply at the configured height", () => {
    const out = liveTail(lines(200));
    // +1 for the "N earlier lines" marker.
    expect(out.split("\n")).toHaveLength(LIVE_TAIL_LINES + 1);
  });

  it("keeps the end, which is where new text arrives", () => {
    const out = liveTail(lines(200));
    expect(out).toContain("line200");
    expect(out).not.toContain("line1\n");
  });

  it("says how much is hidden rather than silently truncating", () => {
    // 200 lines with a 7-line window leaves 193 hidden. This said 188, from when
    // the cap was 12 — the number has to follow LIVE_TAIL_LINES, not be pinned.
    expect(liveTail(lines(200))).toMatch(new RegExp(`${200 - LIVE_TAIL_LINES} earlier lines`));
  });

  it("uses the singular for exactly one hidden line", () => {
    expect(liveTail(lines(LIVE_TAIL_LINES + 1))).toMatch(/1 earlier line\b/);
  });

  it("stays well under a normal viewport", () => {
    // The whole point: the erase must always reach the top of the region.
    expect(LIVE_TAIL_LINES).toBeLessThan(20);
  });

  it("handles an empty reply", () => {
    expect(liveTail("")).toBe("");
  });
});
