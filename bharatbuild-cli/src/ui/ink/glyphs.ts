/**
 * Marker characters for the TUI.
 *
 * The Unicode set (⏺ ✓ ⎿ ▍ braille spinner) depends on the terminal font
 * having those code points. On a default Windows Terminal font they fall back
 * to tofu — ⏺ rendered as a filled box and ✓ as "/" — which made the interface
 * look broken rather than styled.
 *
 * ASCII is therefore the default: it renders identically everywhere. Set
 * BHARATBUILD_UNICODE=1 to opt into the nicer glyphs on a font that has them
 * (a Nerd Font, Cascadia Code, JetBrains Mono …).
 */

export interface GlyphSet {
  /** Gutter markers per role. */
  user: string;
  assistant: string;
  system: string;
  /** Tool call status. */
  toolOk: string;
  toolFail: string;
  /** Tool result tree: corner for the first line, pipe for the rest. */
  elbow: string;
  elbowCont: string;
  /** Streaming caret. */
  caret: string;
  /** Idle dot in the status bar. */
  idle: string;
  /** Frames for the working spinner. */
  spinner: string[];
  /** Branding mark; empty string means "no icon". */
  brand: string;
  /** Markdown list bullet and blockquote bar. */
  bullet: string;
  quote: string;
  /** Checklist marker for `- [ ]` / `- [x]`, which read as literal brackets. */
  task: (done: boolean) => string;
  /**
   * Horizontal rule. Box-drawing, not "-", in BOTH sets: a repeated
   * hyphen renders as a dashed line because of the glyph's side bearing,
   * and U+2500 is proven to render here — the palette frame always did.
   * The glyphs that actually fell back were the rarer ⏺ ✓ ⎿.
   */
  rule: string;
  /** Marker for a folded reasoning block. */
  thinking: string;
  /** Attachment marker for a pasted image. */
  clip: string;
  /** Selected-row pointer in a list of choices. */
  cursor: string;
  /** Scroll indicators in the command palette. */
  up: string;
  down: string;
  /** Truncation marker. */
  ellipsis: string;
  /** Approval prompt marker. */
  warn: string;
  /** Separator between inline items. */
  sep: string;
  /** Currency prefix for the credit figure. */
  currency: string;
}

const ASCII: GlyphSet = {
  user: ">",
  assistant: "*",
  system: "*",
  toolOk: "+",
  toolFail: "X",
  elbow: "  +- ",
  elbowCont: "  |  ",
  caret: "|",
  idle: "o",
  spinner: [".", "o", "O", "o"],
  brand: "",
  bullet: "- ",
  quote: "| ",
  task: (done: boolean) => (done ? "[x]" : "[ ]"),
  thinking: "*",
  clip: "[img]",
  cursor: ">",
  rule: "─",
  up: "^",
  down: "v",
  ellipsis: "...",
  warn: "!",
  sep: "|",
  currency: "Rs ",
};

/**
 * Claude Code's layout, drawn with glyphs that actually have font coverage.
 *
 * The previous set reached for U+23FA (⏺) and U+23BF (⎿), both from
 * Miscellaneous Technical — a block most monospace fonts cover poorly. They
 * fell back to boxes, which is why this whole set was abandoned for ASCII.
 * The conclusion drawn at the time was that the terminal could not do
 * Unicode; it could. It just did not have those two characters.
 *
 * U+25CF (●) is Geometric Shapes and U+2514 (└) is Box Drawing — the same
 * block as the ╭─╮╰ borders that were rendering correctly all along.
 */
const UNICODE: GlyphSet = {
  user: ">",
  assistant: "●",
  system: "●",
  // Claude Code marks success and failure by colour, not by a different
  // shape, so the column stays aligned whatever the outcome.
  toolOk: "●",
  toolFail: "●",
  elbow: "  └─ ",
  elbowCont: "     ",
  caret: "▏",
  idle: "●",
  // Braille spinners need a font with the Braille block; a rotating bar
  // needs only box drawing, which this terminal is known to have.
  spinner: ["|", "/", "-", "\\"],
  brand: "⚡ ",
  bullet: "• ",
  quote: "│ ",
  task: (done: boolean) => (done ? "☑" : "☐"),
  thinking: "✻",
  clip: "▣",
  cursor: "❯",
  rule: "─",
  up: "↑",
  down: "↓",
  ellipsis: "…",
  warn: "⚠",
  sep: "·",
  currency: "₹",
};

/**
 * claude-code's own glyphs, exactly.
 *
 * U+23FA (⏺) and U+23BF (⎿) are Miscellaneous Technical, a block many
 * monospace fonts cover poorly — on this machine they rendered as tofu boxes,
 * which is what made the interface look broken and got the whole Unicode set
 * abandoned once already. They are offered rather than imposed: switch with
 * /glyphs, and switch back the same way if the boxes come back.
 */
const CLAUDE: GlyphSet = {
  ...UNICODE,
  assistant: "⏺",
  system: "⏺",
  toolOk: "⏺",
  toolFail: "⏺",
  elbow: "  ⎿  ",
  elbowCont: "     ",
};

/**
 * Whether to draw the Unicode layout.
 *
 * This sniffed for WT_SESSION / TERM_PROGRAM / MSYSTEM, which are set by
 * Windows Terminal, VS Code and Git Bash but not by a plain PowerShell
 * window — so PowerShell users got the ASCII fallback on a terminal that
 * renders Unicode perfectly well. It also passed in the developer's Git Bash
 * shell, which is exactly why it looked fine while being broken.
 *
 * The sniffing was never justified: the UI already draws ╭─╮│╰ borders
 * unconditionally (ink's borderStyle="round" has no ASCII form), and those
 * have always rendered. A terminal that draws Box Drawing will draw U+25CF
 * and U+2514 too — they are no rarer. So the default is Unicode, and ASCII
 * is what you opt into when a terminal genuinely cannot manage it.
 */
function terminalSupportsUnicode(): boolean {
  const forced = process.env["BHARATBUILD_UNICODE"];
  if (forced === "1") return true;
  if (forced === "0") return false;

  // A POSIX locale that explicitly is not UTF-8 is the one case worth
  // honouring; anything else, including an unset locale, gets Unicode.
  const locale = [process.env["LC_ALL"], process.env["LC_CTYPE"], process.env["LANG"]]
    .filter(Boolean)
    .join(" ");
  if (locale && !/utf-?8/i.test(locale)) return false;

  return true;
}
function initialSet(): GlyphSet {
  const forced = process.env["BHARATBUILD_GLYPHS"];
  if (forced === "claude") return CLAUDE;
  if (forced === "ascii") return ASCII;
  if (forced === "unicode") return UNICODE;
  return terminalSupportsUnicode() ? UNICODE : ASCII;
}
let active: GlyphSet = initialSet();

export function getGlyphs(): GlyphSet {
  return active;
}

/** Exposed for tests and for a future `/settings glyphs` toggle. */
export type GlyphMode = "ascii" | "unicode" | "claude";

export function setGlyphs(mode: GlyphMode): void {
  active = mode === "claude" ? CLAUDE : mode === "unicode" ? UNICODE : ASCII;
}

/** Every mode, for /glyphs to list. */
export function glyphModes(): GlyphMode[] {
  return ["unicode", "claude", "ascii"];
}

export function getGlyphMode(): GlyphMode {
  if (active === CLAUDE) return "claude";
  return active === UNICODE ? "unicode" : "ascii";
}
