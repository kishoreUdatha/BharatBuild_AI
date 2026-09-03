/**
 * Shiki-backed syntax highlighting.
 *
 * Shiki is the VS Code highlighting engine: real TextMate grammars produce
 * scopes, a VS Code theme maps those scopes to colours. That is why it gets
 * cases a keyword list cannot — `const s = "import from"` tokenises as one
 * string, so `import` inside it is not painted as a keyword.
 *
 * Two constraints shape this module:
 *
 *  1. Ink renders synchronously; Shiki's setup and grammar loading are async.
 *     So `highlightSync` never waits — it returns what is already loaded and
 *     schedules anything missing, and subscribers re-render when it arrives.
 *
 *  2. Committed output goes through <Static> and is never repainted. A diff
 *     printed before the grammar loaded would keep its fallback colours for
 *     the rest of the session, so `warmUp()` runs at mount.
 */

import type { Language } from "./syntax.js";
import { getInkThemeName } from "./theme.js";

export interface HlToken {
  text: string;
  /** Hex from the theme, or undefined for default foreground. */
  color?: string;
}

/** Loaded up front: the languages an agent session actually touches. */
const WARM_LANGS = ["typescript", "tsx", "python", "json", "shellscript"];

type Highlighter = {
  codeToTokens: (code: string, opts: { lang: string; theme: string }) => { tokens: Array<Array<{ content: string; color?: string }>> };
  loadLanguage: (lang: string) => Promise<void>;
  getLoadedLanguages: () => string[];
};

let highlighter: Highlighter | null = null;
let initStarted = false;
let disabled = false;
const pending = new Set<string>();
const listeners = new Set<() => void>();

function notify(): void {
  for (const fn of listeners) fn();
}

/**
 * Re-render hook for when grammars finish loading.
 *
 * Level-triggered, not edge-triggered. `notify()` fires once at the moment the
 * highlighter is ready; a component whose effect runs after that moment would
 * never hear about it and would keep its fallback colours forever. Setup
 * finishes in ~50ms, which is exactly the window a mount lands in, so this was
 * not a rare race — it was the normal case.
 */
export function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  // Re-check membership: a component that unmounts before the microtask runs
  // must not be called, or React gets a setState on an unmounted component.
  if (highlighter) queueMicrotask(() => { if (listeners.has(fn)) fn(); });
  return () => listeners.delete(fn);
}

function themeName(): string {
  return getInkThemeName() === "light" ? "github-light" : "github-dark";
}

/** Highlighting is pure decoration — a failure must never break the session. */
async function init(): Promise<void> {
  if (initStarted) return;
  initStarted = true;
  try {
    const { createHighlighter } = await import("shiki");
    highlighter = (await createHighlighter({
      themes: ["github-dark", "github-light"],
      langs: WARM_LANGS,
    })) as unknown as Highlighter;
    notify();
  } catch {
    disabled = true;
  }
}

/** Load grammars ahead of first use so <Static> output is not stuck on the fallback. */
export function warmUp(): void {
  if (getInkThemeName() === "safe") { disabled = true; return; }
  void init();
}

function ensureLanguage(lang: string): void {
  if (!highlighter || pending.has(lang)) return;
  if (highlighter.getLoadedLanguages().includes(lang)) return;
  pending.add(lang);
  void highlighter
    .loadLanguage(lang)
    .then(notify)
    .catch(() => { /* unknown grammar — the fallback covers it */ })
    .finally(() => pending.delete(lang));
}

/**
 * Tokenize whole lines together, not one at a time: a template literal or a
 * block comment spanning lines only resolves with its neighbours present.
 *
 * Returns null when Shiki cannot serve this yet, so the caller falls back.
 */
export function highlightSync(lines: string[], lang: Language): HlToken[][] | null {
  if (disabled || !lang || lang === "plain") return null;
  const shikiLang = lang;

  if (!highlighter) { void init(); return null; }
  if (!highlighter.getLoadedLanguages().includes(shikiLang)) {
    ensureLanguage(shikiLang);
    return null;
  }

  try {
    const { tokens } = highlighter.codeToTokens(lines.join("\n"), {
      lang: shikiLang,
      theme: themeName(),
    });
    // A trailing newline can yield an extra row; align to the input.
    return lines.map((_, i) => (tokens[i] ?? []).map((t) => ({ text: t.content, color: t.color })));
  } catch {
    return null;
  }
}

/** Test seam. */
export function resetHighlighter(): void {
  highlighter = null;
  initStarted = false;
  disabled = false;
  pending.clear();
  listeners.clear();
}

export function isReady(): boolean {
  return highlighter !== null;
}
