/**
 * Unified-diff renderer.
 *
 * File edits were reported as a one-line byte count, so a change was invisible.
 * This renders the diff the way a reviewer expects: a line-number gutter, a
 * +/- marker, the whole row tinted, and the code itself syntax-highlighted.
 *
 * Line numbers come from the `@@ -a,b +c,d @@` hunk headers, so they are the
 * real numbers in the file rather than an index into the diff.
 */

import React from "react";
import { Box, Text, useStdout } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { TokenLine, useHighlightedBlock, detectLanguage, type Language } from "./syntax.js";

export interface DiffRow {
  kind: "add" | "del" | "ctx" | "meta";
  text: string;
  /** Line number in the new file (adds/context) or old file (deletes). */
  lineNo?: number;
}

export interface ParsedDiff {
  filePath?: string;
  rows: DiffRow[];
}

const HUNK = /^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@/;

/** True when a tool result carries a unified diff we should render richly. */
export function looksLikeDiff(text: string): boolean {
  return /^---\s+a\//m.test(text) && /^\+\+\+\s+b\//m.test(text) && /^@@\s+-\d+/m.test(text);
}

export function parseDiff(text: string): ParsedDiff {
  const rows: DiffRow[] = [];
  let filePath: string | undefined;
  let oldNo = 0;
  let newNo = 0;

  for (const raw of text.split("\n")) {
    const plus = raw.match(/^\+\+\+\s+b\/(.*)$/);
    if (plus) { filePath = plus[1]!.trim(); continue; }
    if (/^---\s+a\//.test(raw)) continue;

    const hunk = raw.match(HUNK);
    if (hunk) {
      oldNo = parseInt(hunk[1]!, 10);
      newNo = parseInt(hunk[3]!, 10);
      rows.push({ kind: "meta", text: raw });
      continue;
    }

    if (raw.startsWith("+")) { rows.push({ kind: "add", text: raw.slice(1), lineNo: newNo++ }); continue; }
    if (raw.startsWith("-")) { rows.push({ kind: "del", text: raw.slice(1), lineNo: oldNo++ }); continue; }
    if (raw.startsWith(" ")) { rows.push({ kind: "ctx", text: raw.slice(1), lineNo: newNo }); oldNo++; newNo++; continue; }
    if (raw.trim()) rows.push({ kind: "meta", text: raw });
  }

  return { filePath, rows };
}

/**
 * Cut or pad a token run to exactly `width` visible columns.
 *
 * Padding is what makes the row tint read as a continuous band: a background
 * only covers the cells a span actually occupies, so without this the colour
 * stopped at the last character of the code and the rest of the row stayed the
 * terminal's own background. Truncating keeps one diff line on one screen row,
 * so a long line cannot wrap and leave an untinted remainder behind it.
 */
function fitTokens(tokens: HlTokenLike[], width: number): HlTokenLike[] {
  const out: HlTokenLike[] = [];
  let used = 0;
  for (const tok of tokens) {
    if (used >= width) break;
    const room = width - used;
    const text = tok.text.length > room ? tok.text.slice(0, room) : tok.text;
    out.push({ ...tok, text });
    used += text.length;
  }
  if (used < width) out.push({ text: " ".repeat(width - used) });
  return out;
}

interface HlTokenLike { text: string; color?: string }

export function DiffView({
  patch,
  maxRows = 40,
  indent = 0,
}: {
  patch: string;
  maxRows?: number;
  /** Columns already consumed to the left, so the row can fill the rest. */
  indent?: number;
}): React.ReactElement {
  const { stdout } = useStdout();
  const t = getInkTheme();
  const g = getGlyphs();
  const { filePath, rows } = parseDiff(patch);
  const lang: Language = detectLanguage(filePath);

  // A newly created file is every line an addition, so tinting each row turns
  // the whole block into a solid green wall — the colour stops distinguishing
  // anything, because there is nothing here that is not new. The + markers and
  // the line numbers already say it is a creation, so the code is left to read
  // as code, syntax highlighting and all.
  const codeLines = rows.filter((r) => r.kind !== "meta");
  const isNewFile =
    codeLines.length > 0 && codeLines.every((r) => r.kind === "add");

  const shown = rows.slice(0, maxRows);
  // Tokenize the visible block in one pass so multi-line constructs resolve;
  // Shiki needs neighbouring lines to know a template literal is still open.
  const codeRows = shown.filter((r) => r.kind !== "meta");
  const tokenLines = useHighlightedBlock(codeRows.map((r) => r.text), lang);
  const tokensFor = new Map(codeRows.map((r, i) => [r, tokenLines[i] ?? [{ text: r.text }]]));
  const hidden = rows.length - shown.length;
  const width = Math.max(
    3,
    ...shown.map((r) => (r.lineNo === undefined ? 0 : String(r.lineNo).length)),
  );

  // Everything left of the code: gutter number, a space, marker, a space.
  const leftCols = width + 1 + 2;
  const codeWidth = Math.max(20, (stdout?.columns ?? 80) - indent - leftCols - 1);

  return (
    <Box flexDirection="column">
      {shown.map((row, i) => {
        if (row.kind === "meta") {
          // Hunk headers add noise once the gutter carries real line numbers.
          return null;
        }
        const marker = row.kind === "add" ? "+" : row.kind === "del" ? "-" : " ";
        const bg = isNewFile
          ? undefined
          : row.kind === "add" ? t.diffAddBg
          : row.kind === "del" ? t.diffRemoveBg
          : undefined;
        const num = row.lineNo === undefined ? "" : String(row.lineNo);

        return (
          <Box key={i}>
            <Text color={t.gutter} dimColor>
              {num.padStart(width)}{" "}
            </Text>
            <Text
              color={row.kind === "add" ? t.diffAdd : row.kind === "del" ? t.diffRemove : t.muted}
              backgroundColor={bg || undefined}
              bold={row.kind !== "ctx"}
            >
              {marker}{" "}
            </Text>
            <TokenLine
              tokens={
                bg
                  ? fitTokens(tokensFor.get(row) ?? [{ text: row.text }], codeWidth)
                  : (tokensFor.get(row) ?? [{ text: row.text }])
              }
              backgroundColor={bg || undefined}
            />
          </Box>
        );
      })}
      {hidden > 0 && (
        <Text color={t.muted} dimColor>
          {" ".repeat(width + 1)}{g.ellipsis} +{hidden} more diff lines (ctrl+o to expand)
        </Text>
      )}
    </Box>
  );
}
