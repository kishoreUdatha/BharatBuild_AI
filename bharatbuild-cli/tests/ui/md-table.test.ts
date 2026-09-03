/**
 * Tables came out as raw pipes and dashes — the exact reply that prompted this
 * is the fixture below. A table is the format models reach for whenever they
 * compare things, so this was not a rare corner.
 */
import { describe, it, expect } from "vitest";
import { parseTable, layoutTable } from "../../src/ui/ink/md-table.js";

/** Verbatim from a BharatBuild reply. */
const REAL = [
  "| Component | Status | Have |",
  "|-----------|--------|------|",
  "| Java | ✅ Ready | 17.0.19 |",
  "| Gradle | ✅ Ready | 8.5 |",
  "| Android SDK | ❌ Missing | — |",
].join("\n");

const lines = (s: string) => s.split("\n");

describe("recognising a table", () => {
  it("parses the reply that prompted this", () => {
    const t = parseTable(lines(REAL), 0);
    expect(t).not.toBeNull();
    expect(t!.header).toEqual(["Component", "Status", "Have"]);
    expect(t!.rows).toHaveLength(3);
    expect(t!.lineCount).toBe(5);
  });

  it("needs the separator, not just a pipe", () => {
    // Prose mentioning `a | b` is not a table, and turning it into one would
    // mangle an ordinary sentence.
    const prose = ["The flag takes a | b | c.", "Nothing special here."];
    expect(parseTable(prose, 0)).toBeNull();
  });

  it("accepts rows without the outer pipes", () => {
    const t = parseTable(lines("a | b\n--- | ---\n1 | 2"), 0);
    expect(t!.header).toEqual(["a", "b"]);
    expect(t!.rows).toEqual([["1", "2"]]);
  });

  it("reads the alignment markers", () => {
    const t = parseTable(lines("| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |"), 0);
    expect(t!.align).toEqual(["left", "center", "right"]);
  });

  it("stops at the end of the block", () => {
    const doc = lines(`${REAL}\n\nSome prose after.`);
    expect(parseTable(doc, 0)!.lineCount).toBe(5);
  });

  it("squares up a ragged row instead of shifting the rest", () => {
    const t = parseTable(lines("| a | b | c |\n|---|---|---|\n| 1 |"), 0);
    expect(t!.rows[0]).toEqual(["1", "", ""]);
  });
});

describe("laying it out", () => {
  const layout = () => layoutTable(parseTable(lines(REAL), 0)!, 80);

  it("gives every row the same width", () => {
    const l = layout();
    const widths = [l.header, ...l.rows].map((r) => r.map((c) => c.length).join(","));
    // Each column is one width across the whole table, or nothing lines up.
    expect(new Set(l.rows.map((r) => r.length)).size).toBe(1);
    expect(widths.length).toBe(4);
  });

  it("sizes a column to its widest cell", () => {
    // "Android SDK" is longer than the "Component" header.
    expect(layout().widths[0]).toBe("Android SDK".length);
  });

  it("counts an emoji as the two columns it occupies", () => {
    // ✅ is one JS character but two terminal columns; counting by .length
    // padded the cell short and stepped every later column left on that row.
    const l = layout();
    const status = l.rows[0]![1]!;
    expect(status).toContain("✅");
    // Padded to fewer characters than the column width, because the emoji
    // already covers two of them.
    expect(status.length).toBeLessThan(l.widths[1]!);
  });

  it("right-aligns when asked", () => {
    const t = parseTable(lines("| count |\n|------:|\n| 7 |"), 0)!;
    const l = layoutTable(t, 80);
    expect(l.rows[0]![0]).toBe("    7");
  });

  it("centres when asked", () => {
    const t = parseTable(lines("| label |\n|:-----:|\n|  x  |"), 0)!;
    const l = layoutTable(t, 80);
    expect(l.rows[0]![0]).toBe("  x  ");
  });
});

describe("a table wider than the terminal", () => {
  const wide = [
    "| id | description |",
    "|----|-------------|",
    `| 1 | ${"very long text ".repeat(12)} |`,
  ].join("\n");

  it("fits within the terminal width", () => {
    const l = layoutTable(parseTable(lines(wide), 0)!, 60);
    const rowWidth = l.widths.reduce((a, b) => a + b, 0) + (l.widths.length - 1) * 3;
    expect(rowWidth).toBeLessThanOrEqual(60);
  });

  it("takes the space from the widest column, not from all of them", () => {
    // Narrowing every column equally would waste the short "id" column to
    // protect one long description.
    const l = layoutTable(parseTable(lines(wide), 0)!, 60);
    expect(l.widths[0]).toBe(2);   // "id" untouched
    expect(l.widths[1]).toBeLessThan(56);
  });

  it("marks a clipped cell rather than silently cutting it", () => {
    const l = layoutTable(parseTable(lines(wide), 0)!, 60);
    expect(l.rows[0]![1]).toContain("…");
  });

  it("never leaves half an inline marker behind", () => {
    // Slicing `**bold**` mid-cell leaves an unclosed `**` that gets printed
    // literally, and the stray characters throw the padding off too.
    const bold = ["| x |", "|---|", `| **${"a".repeat(80)}** |`].join("\n");
    const l = layoutTable(parseTable(lines(bold), 0)!, 40);
    expect(l.rows[0]![0]).not.toContain("*");
  });

  it("keeps each padded cell to its column width", () => {
    const l = layoutTable(parseTable(lines(wide), 0)!, 60);
    for (const row of l.rows) {
      row.forEach((cell, c) => {
        // Padding is by display width, so a clipped ASCII cell lands exactly.
        expect(cell.length).toBe(l.widths[c]);
      });
    }
  });
});
