/**
 * Markdown tables.
 *
 * The renderer handled headings, rules, lists and quotes, but not tables — so a
 * model answering with one produced raw pipes and dashes:
 *
 *   | Component | Status | Have |
 *   |-----------|--------|------|
 *   | Java      | Ready  | 17   |
 *
 * which is harder to read than the plain sentences it replaced. Models reach
 * for tables constantly when comparing things, so this is not a rare case.
 */

export interface ParsedTable {
  header: string[];
  align: Array<"left" | "right" | "center">;
  rows: string[][];
  /** Lines consumed, so the caller can skip past the block. */
  lineCount: number;
}

/** A row of cells, tolerating the optional leading and trailing pipes. */
function splitRow(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

/** `|---|:--:|---:|` — the line that makes a pipe row a table. */
function isSeparator(line: string): boolean {
  const s = line.trim();
  if (!s.includes("-") || !s.includes("|")) return false;
  return splitRow(s).every((c) => /^:?-{1,}:?$/.test(c.replace(/\s/g, "")));
}

function alignmentOf(cell: string): "left" | "right" | "center" {
  const s = cell.trim();
  if (s.startsWith(":") && s.endsWith(":")) return "center";
  if (s.endsWith(":")) return "right";
  return "left";
}

/**
 * Parse a table starting at `lines[start]`, or null when there isn't one.
 *
 * A header row alone is not a table — the separator is what distinguishes a
 * table from prose that happens to contain a pipe.
 */
export function parseTable(lines: string[], start: number): ParsedTable | null {
  const headerLine = lines[start];
  const sepLine = lines[start + 1];
  if (!headerLine || !sepLine) return null;
  if (!headerLine.includes("|")) return null;
  if (!isSeparator(sepLine)) return null;

  const header = splitRow(headerLine);
  const align = splitRow(sepLine).map(alignmentOf);

  const rows: string[][] = [];
  let i = start + 2;
  for (; i < lines.length; i++) {
    const line = lines[i]!;
    if (!line.includes("|") || !line.trim()) break;
    const cells = splitRow(line);
    // Pad or trim to the header width: a ragged row should not shift the
    // columns of every row after it.
    while (cells.length < header.length) cells.push("");
    rows.push(cells.slice(0, header.length));
  }

  return { header, align, rows, lineCount: i - start };
}

/**
 * The cell as it will actually be drawn.
 *
 * Width has to be measured against the rendered form, not the source: `**ok**`
 * draws as `ok`, and `[docs](http://x)` draws as `docs (http://x)`. Measuring
 * the source would pad every styled cell wrong, in opposite directions.
 */
function stripMarkers(cell: string): string {
  return cell
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => (label === url ? label : `${label} (${url})`))
    .replace(/\*\*|~~|`|\*/g, "");
}

/**
 * Characters that occupy two terminal columns.
 *
 * Status columns are full of `✅` and `⚠️`, which are one JS character each but
 * two columns wide — counting by `.length` padded them one short and every
 * column after them stepped left by one on those rows.
 */
const WIDE = /[\u{1100}-\u{115F}\u{2E80}-\u{A4CF}\u{AC00}-\u{D7A3}\u{F900}-\u{FAFF}\u{FE30}-\u{FE6F}\u{FF00}-\u{FF60}\u{FFE0}-\u{FFE6}\u{1F300}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{27BF}]/u;

/** Display width: inline markers cost nothing, wide glyphs cost two. */
function visibleWidth(cell: string): number {
  let width = 0;
  for (const ch of stripMarkers(cell)) {
    // A combining mark or a variation selector rides on the previous glyph.
    if (/[\u{FE00}-\u{FE0F}\u{200D}\u{0300}-\u{036F}]/u.test(ch)) continue;
    width += WIDE.test(ch) ? 2 : 1;
  }
  return width;
}

function pad(cell: string, width: number, align: "left" | "right" | "center"): string {
  const visible = visibleWidth(cell);
  const slack = Math.max(0, width - visible);
  if (align === "right") return " ".repeat(slack) + cell;
  if (align === "center") {
    const left = Math.floor(slack / 2);
    return " ".repeat(left) + cell + " ".repeat(slack - left);
  }
  return cell + " ".repeat(slack);
}

export interface TableLayout {
  /** Column widths after fitting to the terminal. */
  widths: number[];
  /** Header cells, padded. */
  header: string[];
  /** The `───┬───` rule under the header. */
  rule: string;
  /** Body rows, padded. */
  rows: string[][];
}

/**
 * Lay a table out for a terminal `maxWidth` columns wide.
 *
 * Columns are sized to their content, then the widest ones are trimmed until
 * the whole thing fits — narrowing every column equally would waste space on a
 * "Status" column of short words to protect one long description.
 */
export function layoutTable(table: ParsedTable, maxWidth: number): TableLayout {
  const cols = table.header.length;
  const widths = table.header.map((h, c) =>
    Math.max(visibleWidth(h), ...table.rows.map((r) => visibleWidth(r[c] ?? ""))),
  );

  // ` │ ` between each pair of columns. The table itself is drawn flush left.
  const overhead = (cols - 1) * 3;
  let total = widths.reduce((a, b) => a + b, 0) + overhead;

  while (total > maxWidth) {
    const widest = widths.indexOf(Math.max(...widths));
    if (widths[widest]! <= 6) break;   // below this a column says nothing
    widths[widest]! -= 1;
    total -= 1;
  }

  // Truncation drops the inline markers first: slicing `**bold text**` mid-cell
  // leaves an unclosed `**` that the renderer then prints literally, and the
  // count of stray characters throws the padding off as well.
  const clip = (cell: string, width: number) => {
    if (visibleWidth(cell) <= width) return cell;
    const plain = [...stripMarkers(cell)];
    let out = "";
    let used = 0;
    for (const ch of plain) {
      const cost = WIDE.test(ch) ? 2 : 1;
      if (used + cost > width - 1) break;
      out += ch;
      used += cost;
    }
    return `${out}…`;
  };

  return {
    widths,
    header: table.header.map((h, c) => pad(clip(h, widths[c]!), widths[c]!, table.align[c] ?? "left")),
    rule: widths.map((w) => "─".repeat(w)).join("─┼─"),
    rows: table.rows.map((r) =>
      r.map((cell, c) => pad(clip(cell, widths[c]!), widths[c]!, table.align[c] ?? "left")),
    ),
  };
}
