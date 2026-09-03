/**
 * Minimal markdown rendering for assistant replies.
 *
 * Models answer in markdown, and it was being printed literally — a reply came
 * out as `## 📦 **Files Created:**` and `- **Hero Section** — Eye-catching`,
 * asterisks and hashes and all. This turns the handful of constructs that
 * actually show up in chat into ink styling.
 *
 * Deliberately not a full markdown implementation: fenced code blocks are
 * handled by the caller, and anything unrecognised is passed through as plain
 * text rather than mangled.
 */

import React from "react";
import { Box, Text, useStdout } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { parseTable, layoutTable, type ParsedTable } from "./md-table.js";

/**
 * Split a line into styled spans.
 *
 * Order matters: `**` before `*` so bold is not eaten by the emphasis rule,
 * and links before either, since a label may itself contain them.
 */
const INLINE = /(\[[^\]\n]+\]\([^)\s]+\)|\*\*[^*]+\*\*|~~[^~]+~~|`[^`]+`|\*[^*\s][^*]*\*)/g;

function inlineSpans(line: string, keyPrefix: string): React.ReactNode[] {
  const t = getInkTheme();
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  INLINE.lastIndex = 0;
  while ((m = INLINE.exec(line)) !== null) {
    if (m.index > last) out.push(line.slice(last, m.index));
    const tok = m[0];
    const key = `${keyPrefix}-${i++}`;

    const link = tok.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
    if (link) {
      const [, label, url] = link;
      // Both halves. A terminal cannot click the label, so hiding the URL
      // would lose it entirely; printing the raw markdown showed it twice.
      out.push(
        <Text key={key}>
          <Text color={t.accent} underline>{label}</Text>
          {label === url ? "" : <Text color={t.muted} dimColor> ({url})</Text>}
        </Text>,
      );
    } else if (tok.startsWith("**")) {
      out.push(<Text key={key} bold>{tok.slice(2, -2)}</Text>);
    } else if (tok.startsWith("~~")) {
      out.push(<Text key={key} strikethrough dimColor>{tok.slice(2, -2)}</Text>);
    } else if (tok.startsWith("`")) {
      out.push(<Text key={key} color={t.accent}>{tok.slice(1, -1)}</Text>);
    } else {
      out.push(<Text key={key} italic>{tok.slice(1, -1)}</Text>);
    }
    last = m.index + tok.length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out.length > 0 ? out : [line];
}

function Line({ raw, index }: { raw: string; index: number }): React.ReactElement {
  const t = getInkTheme();
  const { stdout } = useStdout();
  const key = `l${index}`;

  // Ink collapses an empty <Text>, so blank lines vanished and every section
  // ran into the next. A single space keeps the row.
  if (raw.trim() === "") return <Text> </Text>;

  // Headings — rendered as emphasis, not as literal hashes.
  const heading = raw.match(/^(#{1,6})\s+(.*)$/);
  if (heading) {
    const level = heading[1]!.length;
    return (
      <Text color={level <= 2 ? t.primary : t.text} bold>
        {inlineSpans(heading[2]!, key)}
      </Text>
    );
  }

  // Horizontal rule. Spans the text column rather than a fixed 24 characters,
  // which looked like a stray dash next to full-width paragraphs.
  if (/^\s*([-*_])\1{2,}\s*$/.test(raw)) {
    const width = Math.max(8, Math.min(72, (stdout?.columns ?? 80) - 6));
    return <Text color={t.muted} dimColor>{getGlyphs().rule.repeat(width)}</Text>;
  }

  // Bullets: keep the author's indentation, swap the marker for a real bullet.
  const bullet = raw.match(/^(\s*)[-*+]\s+(.*)$/);
  if (bullet) {
    // `- [ ] item` is a checklist, not a bullet holding literal brackets.
    const task = bullet[2]!.match(/^\[([ xX])\]\s+(.*)$/);
    return (
      <Text color={t.text}>
        {bullet[1]}
        <Text color={t.muted}>{task ? "" : getGlyphs().bullet}</Text>
        {task ? (
          <>
            <Text color={task[1] === " " ? t.muted : t.success}>
              {getGlyphs().task(task[1] !== " ")}{" "}
            </Text>
            {inlineSpans(task[2]!, key)}
          </>
        ) : (
          inlineSpans(bullet[2]!, key)
        )}
      </Text>
    );
  }

  // Numbered list — leave the number, style the content.
  const numbered = raw.match(/^(\s*)(\d+[.)])\s+(.*)$/);
  if (numbered) {
    return (
      <Text color={t.text}>
        {numbered[1]}
        <Text color={t.muted}>{numbered[2]} </Text>
        {inlineSpans(numbered[3]!, key)}
      </Text>
    );
  }

  // Blockquote
  const quote = raw.match(/^\s*>\s?(.*)$/);
  if (quote) {
    return (
      <Text color={t.muted}>
        {getGlyphs().quote}
        {inlineSpans(quote[1]!, key)}
      </Text>
    );
  }

  // Body text, explicitly coloured. Without this it inherited the terminal's
  // default foreground rather than the theme's, so a reply rendered in
  // whatever grey the profile happened to use while everything around it —
  // headings, tool output, the status line — was themed.
  return <Text color={t.text}>{inlineSpans(raw, key)}</Text>;
}

/**
 * A markdown table, drawn with columns instead of printed as pipes.
 *
 * Header in the primary colour with a rule under it, body rows in body text —
 * the same weighting the rest of the renderer gives a heading over its prose.
 */
function Table({ table, keyPrefix }: { table: ParsedTable; keyPrefix: string }): React.ReactElement {
  const t = getInkTheme();
  const { stdout } = useStdout();
  // Two columns of margin, matching the indent the message body already has.
  const layout = layoutTable(table, Math.max(40, (stdout?.columns ?? 80) - 4));

  return (
    <Box flexDirection="column">
      {/* Flush left, so the table's first column lines up with the prose
          above and below it rather than sitting one column in. */}
      <Text color={t.primary} bold>
        {layout.header.join(" │ ")}
      </Text>
      <Text color={t.muted} dimColor>
        {layout.rule}
      </Text>
      {layout.rows.map((row, r) => (
        <Text key={`${keyPrefix}r${r}`}>
          {row.map((cell, c) => (
            <Text key={`${keyPrefix}r${r}c${c}`}>
              {c > 0 ? <Text color={t.muted} dimColor> │ </Text> : null}
              {/* Cells carry inline markup often enough — a bold status or a
                  `code` identifier — that stripping it would lose meaning. */}
              {inlineSpans(cell, `${keyPrefix}r${r}c${c}`)}
            </Text>
          ))}
        </Text>
      ))}
    </Box>
  );
}

/** Render a block of markdown prose (no fenced code — the caller strips those). */
export function Markdown({ content }: { content: string }): React.ReactElement {
  const lines = content.split("\n");

  // Tables span several lines, so this walks blocks rather than mapping lines.
  const blocks: React.ReactNode[] = [];
  for (let i = 0; i < lines.length; i++) {
    const table = parseTable(lines, i);
    if (table) {
      blocks.push(<Table key={`t${i}`} table={table} keyPrefix={`t${i}`} />);
      i += table.lineCount - 1;
      continue;
    }
    blocks.push(<Line key={i} raw={lines[i]!} index={i} />);
  }

  return <Box flexDirection="column">{blocks}</Box>;
}
