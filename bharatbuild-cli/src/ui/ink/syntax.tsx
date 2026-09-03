/**
 * Lightweight syntax highlighting for code shown in the TUI.
 *
 * Deliberately a tokenizer rather than a parser: it has to survive a single
 * diff line torn out of context, where a real parser would fail. Comments and
 * strings win over keywords, and anything unrecognised is left alone.
 */

import React, { useEffect, useState } from "react";
import { Text } from "ink";
import { highlightSync, subscribe, type HlToken } from "./highlighter.js";
import { getInkTheme } from "./theme.js";
import { EXTENSION_LANGUAGE, fallbackFamily, type FallbackFamily } from "./languages.js";

/** A Shiki language id, or "plain" when nothing matches. */
export type Language = string;

const TS_KEYWORDS = new Set([
  "import", "export", "from", "const", "let", "var", "function", "return", "if", "else",
  "for", "while", "class", "extends", "implements", "interface", "type", "enum", "new",
  "await", "async", "try", "catch", "finally", "throw", "typeof", "instanceof", "in", "of",
  "default", "case", "switch", "break", "continue", "null", "undefined", "true", "false",
  "this", "super", "static", "public", "private", "protected", "readonly", "as", "void",
]);

const PY_KEYWORDS = new Set([
  "import", "from", "def", "class", "return", "if", "elif", "else", "for", "while",
  "try", "except", "finally", "raise", "with", "as", "in", "is", "not", "and", "or",
  "None", "True", "False", "lambda", "yield", "pass", "break", "continue", "global", "async", "await",
]);

const SHELL_KEYWORDS = new Set([
  "if", "then", "else", "fi", "for", "in", "do", "done", "while", "case", "esac",
  "function", "return", "export", "local", "echo", "cd", "npm", "node", "git", "python",
]);

/**
 * Resolve a Shiki language id from a path or a fence hint.
 *
 * This used to recognise six languages, so a Rust or Go file came back as
 * "plain" and was never highlighted at all — the lazy-loading machinery
 * existed but nothing ever asked it for those grammars.
 */
export function detectLanguage(filePath?: string, hint?: string): Language {
  const source = (hint ?? filePath ?? "").trim().toLowerCase();
  if (!source) return "plain";

  // A bare fence hint ("rust", "py") or a full path.
  const direct = EXTENSION_LANGUAGE[source];
  if (direct) return direct;

  const base = source.split(/[\/]/).pop() ?? source;
  // Extension-less names that identify a language on their own.
  const whole = EXTENSION_LANGUAGE[base];
  if (whole) return whole;

  const dot = base.lastIndexOf(".");
  if (dot === -1 || dot === base.length - 1) return "plain";
  return EXTENSION_LANGUAGE[base.slice(dot + 1)] ?? "plain";
}

function keywordsFor(family: FallbackFamily): Set<string> {
  switch (family) {
    case "ts": return TS_KEYWORDS;
    case "py": return PY_KEYWORDS;
    case "shell": return SHELL_KEYWORDS;
    default: return new Set();
  }
}

function commentPrefix(family: FallbackFamily): RegExp | null {
  switch (family) {
    case "ts": case "css": return /^\s*(\/\/|\/\*|\*)/;
    case "py": case "shell": return /^\s*#/;
    case "html": return /^\s*<!--/;
    default: return null;
  }
}

interface Span { text: string; kind: "plain" | "keyword" | "string" | "comment" | "number" | "tag" }

/** Tokenize one line. Strings and comments are matched before identifiers. */
export function tokenize(line: string, lang: Language): Span[] {
  const family = fallbackFamily(lang);
  if (family === "plain") return [{ text: line, kind: "plain" }];

  const comment = commentPrefix(family);
  if (comment && comment.test(line)) return [{ text: line, kind: "comment" }];

  const spans: Span[] = [];
  // Strings, then numbers, then bare words. HTML tags get their own class.
  const re = family === "html"
    ? /("[^"]*"|'[^']*')|(<\/?[A-Za-z][\w-]*)|(\b\d+(?:\.\d+)?\b)/g
    : /("[^"]*"|'[^']*'|`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_$][\w$]*)/g;

  const keywords = keywordsFor(family);
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = re.exec(line)) !== null) {
    if (m.index > last) spans.push({ text: line.slice(last, m.index), kind: "plain" });
    const tok = m[0];
    if (m[1] !== undefined) spans.push({ text: tok, kind: "string" });
    else if (family === "html" && m[2] !== undefined) spans.push({ text: tok, kind: "tag" });
    else if (/^\d/.test(tok)) spans.push({ text: tok, kind: "number" });
    else spans.push({ text: tok, kind: keywords.has(tok) ? "keyword" : "plain" });
    last = m.index + tok.length;
  }
  if (last < line.length) spans.push({ text: line.slice(last), kind: "plain" });
  return spans.length > 0 ? spans : [{ text: line, kind: "plain" }];
}

/**
 * Tokenize a block of lines, preferring Shiki and falling back to the local
 * tokenizer until its grammar is loaded.
 *
 * The whole block goes in together so multi-line constructs resolve; the
 * fallback works line-by-line, which is the accuracy cost of not waiting.
 */
export function useHighlightedBlock(lines: string[], lang: Language): HlToken[][] {
  const [, bump] = useState(0);
  useEffect(() => subscribe(() => bump((n) => n + 1)), []);

  const shiki = highlightSync(lines, lang);
  if (shiki) return shiki;
  return lines.map((line) => tokenize(line, lang).map((s) => ({ text: s.text, color: kindColor(s.kind) })));
}

/** Fallback colours come from the ink theme, not from a VS Code theme. */
function kindColor(kind: Span["kind"]): string | undefined {
  const t = getInkTheme();
  switch (kind) {
    case "keyword": return t.syntaxKeyword;
    case "string": return t.syntaxString;
    case "comment": return t.syntaxComment;
    case "number": return t.syntaxNumber;
    case "tag": return t.syntaxKeyword;
    default: return undefined;
  }
}

/** Render pre-tokenized spans. Used by the diff view, which tokenizes a block. */
export function TokenLine({
  tokens, backgroundColor,
}: {
  tokens: HlToken[];
  backgroundColor?: string;
}): React.ReactElement {
  return (
    <Text>
      {tokens.map((t, i) => (
        <Text key={i} color={t.color} backgroundColor={backgroundColor}>
          {t.text}
        </Text>
      ))}
    </Text>
  );
}

/**
 * Render one highlighted line.
 *
 * `backgroundColor` is applied per span rather than to a wrapping element:
 * Ink does not propagate a parent background to children, so a diff row would
 * otherwise show colour only behind the marker.
 */
export function HighlightedLine({
  line, lang, backgroundColor, dim,
}: {
  line: string;
  lang: Language;
  backgroundColor?: string;
  dim?: boolean;
}): React.ReactElement {
  const t = getInkTheme();
  const colorFor = (kind: Span["kind"]): string | undefined => {
    switch (kind) {
      case "keyword": return t.syntaxKeyword;
      case "string": return t.syntaxString;
      case "comment": return t.syntaxComment;
      case "number": return t.syntaxNumber;
      case "tag": return t.syntaxKeyword;
      default: return undefined;
    }
  };

  return (
    <Text>
      {tokenize(line, lang).map((s, i) => (
        <Text key={i} color={colorFor(s.kind)} backgroundColor={backgroundColor} dimColor={dim}>
          {s.text}
        </Text>
      ))}
    </Text>
  );
}
