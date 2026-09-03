/**
 * Unified diffs for file-mutating tools.
 *
 * write_file / apply_patch / delete_file used to report only "Written 8195
 * chars to 'index.html'", so neither the user nor the model could see what
 * actually changed. Standard unified format is used because it serves both:
 * the UI parses the hunk headers to number and colour the lines, and the model
 * already understands it without any custom convention.
 *
 * Output is bounded — a tool result is fed back into the context on every
 * turn, so an unbounded diff of a large file would crowd out the conversation.
 */

import { displayPath } from "../../infra/display-path.js";

const DEFAULT_CONTEXT = 3;
const MAX_DIFF_LINES = 80;
/** Above this, computing an LCS is not worth it and the diff is unreadable. */
const MAX_LCS_LINES = 3000;

export interface DiffOptions {
  contextLines?: number;
  maxLines?: number;
}

type Op = { kind: "eq" | "del" | "add"; line: string };

/**
 * Longest-common-subsequence line diff.
 *
 * Trims the shared head and tail first, which is what makes this affordable on
 * real edits: changing one line in a 500-line file reduces to a 1x1 matrix.
 */
function diffLines(a: string[], b: string[]): Op[] {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head++;

  let tail = 0;
  while (
    tail < a.length - head &&
    tail < b.length - head &&
    a[a.length - 1 - tail] === b[b.length - 1 - tail]
  ) tail++;

  const midA = a.slice(head, a.length - tail);
  const midB = b.slice(head, b.length - tail);

  const ops: Op[] = [];
  for (let i = 0; i < head; i++) ops.push({ kind: "eq", line: a[i]! });

  if (midA.length > MAX_LCS_LINES || midB.length > MAX_LCS_LINES) {
    // Too large to align meaningfully; report as a wholesale replacement.
    for (const l of midA) ops.push({ kind: "del", line: l });
    for (const l of midB) ops.push({ kind: "add", line: l });
  } else {
    const n = midA.length;
    const m = midB.length;
    const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        lcs[i]![j] = midA[i] === midB[j]
          ? lcs[i + 1]![j + 1]! + 1
          : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!);
      }
    }
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
      if (midA[i] === midB[j]) { ops.push({ kind: "eq", line: midA[i]! }); i++; j++; }
      else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) { ops.push({ kind: "del", line: midA[i]! }); i++; }
      else { ops.push({ kind: "add", line: midB[j]! }); j++; }
    }
    while (i < n) { ops.push({ kind: "del", line: midA[i]! }); i++; }
    while (j < m) { ops.push({ kind: "add", line: midB[j]! }); j++; }
  }

  for (let k = b.length - tail; k < b.length; k++) ops.push({ kind: "eq", line: b[k]! });
  return ops;
}

export interface DiffSummary {
  added: number;
  removed: number;
  /** Unified diff text, or "" when nothing changed. */
  patch: string;
}

/** Split preserving the author's line count; a trailing newline is not a line. */
function toLines(text: string): string[] {
  if (text === "") return [];
  return text.replace(/\r\n/g, "\n").replace(/\n$/, "").split("\n");
}

export function buildUnifiedDiff(
  oldText: string,
  newText: string,
  filePath: string,
  opts: DiffOptions = {},
): DiffSummary {
  const contextLines = opts.contextLines ?? DEFAULT_CONTEXT;
  const maxLines = opts.maxLines ?? MAX_DIFF_LINES;

  const a = toLines(oldText);
  const b = toLines(newText);
  const ops = diffLines(a, b);

  const added = ops.filter((o) => o.kind === "add").length;
  const removed = ops.filter((o) => o.kind === "del").length;
  if (added === 0 && removed === 0) return { added: 0, removed: 0, patch: "" };

  // Keep only regions near a change, plus `contextLines` either side.
  const keep = new Array(ops.length).fill(false);
  ops.forEach((op, i) => {
    if (op.kind === "eq") return;
    for (let k = Math.max(0, i - contextLines); k <= Math.min(ops.length - 1, i + contextLines); k++) {
      keep[k] = true;
    }
  });

  const out: string[] = [`--- a/${filePath}`, `+++ b/${filePath}`];
  let oldLine = 1;
  let newLine = 1;
  let i = 0;
  let emitted = 0;
  let truncated = false;

  while (i < ops.length) {
    if (!keep[i]) {
      if (ops[i]!.kind !== "add") oldLine++;
      if (ops[i]!.kind !== "del") newLine++;
      i++;
      continue;
    }

    // Measure the hunk before writing its header — the header needs the counts.
    const startOld = oldLine;
    const startNew = newLine;
    const hunk: string[] = [];
    let oldCount = 0;
    let newCount = 0;

    while (i < ops.length && keep[i]) {
      const op = ops[i]!;
      if (op.kind === "eq") { hunk.push(` ${op.line}`); oldCount++; newCount++; oldLine++; newLine++; }
      else if (op.kind === "del") { hunk.push(`-${op.line}`); oldCount++; oldLine++; }
      else { hunk.push(`+${op.line}`); newCount++; newLine++; }
      i++;
    }

    const header = `@@ -${startOld},${oldCount} +${startNew},${newCount} @@`;
    const room = maxLines - emitted;

    if (hunk.length > room) {
      // Emit as much of the hunk as fits rather than discarding it.
      //
      // This dropped the whole hunk when it exceeded the budget. A newly
      // created file is a single hunk, so any file over maxLines produced a
      // patch with a header, a footer and no content whatsoever — the UI then
      // failed to recognise it as a diff and fell back to plain text. Creating
      // a 90-line file showed "Added 90 lines" and nothing else.
      //
      // The header keeps the true counts so the line numbering still parses;
      // it describes the hunk, not how much of it survived truncation.
      if (room > 0) {
        out.push(header, ...hunk.slice(0, room));
        emitted += room;
      }
      truncated = true;
      break;
    }

    out.push(header, ...hunk);
    emitted += hunk.length;
  }

  if (truncated) out.push(`... diff truncated (${added} added, ${removed} removed in total)`);
  return { added, removed, patch: out.join("\n") };
}

/** `Update(path)` + `Added N lines, removed M lines` + the diff body. */
export function renderFileChange(
  verb: "Create" | "Update" | "Delete",
  filePath: string,
  summary: DiffSummary,
): string {
  // Relative to the working directory: the absolute form is mostly noise, and
  // this line is read by a person, not resolved by a tool.
  const parts: string[] = [`${verb}(${displayPath(filePath)})`];

  if (verb === "Delete") {
    parts.push(`Removed ${summary.removed} line${summary.removed === 1 ? "" : "s"}`);
  } else if (summary.added === 0 && summary.removed === 0) {
    parts.push("No changes");
  } else {
    const bits: string[] = [];
    if (summary.added) bits.push(`Added ${summary.added} line${summary.added === 1 ? "" : "s"}`);
    if (summary.removed) bits.push(`removed ${summary.removed} line${summary.removed === 1 ? "" : "s"}`);
    parts.push(bits.join(", "));
  }

  if (summary.patch) parts.push("", summary.patch);
  return parts.join("\n");
}
