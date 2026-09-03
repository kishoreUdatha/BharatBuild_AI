/**
 * Semantic colour tokens for the ink TUI.
 *
 * Components used to hardcode ink colour names ("blueBright", "cyanBright",
 * "gray"), so `/theme` changed nothing on screen and the palette drifted
 * between the status bar, the palette and the tool cards.
 *
 * Token names follow the shape kiro-cli uses in its own TUI bundle — a
 * `primary`/`accent` pair plus muted//state colours — so the two read as the
 * same family of interface.
 *
 * Values are ink colour names (or hex). Terminals resolve the 16 base names
 * from the user's own colour scheme, which is why the default theme prefers
 * them: it inherits whatever the user already themed their terminal to.
 */

export type InkThemeName = "dark" | "light" | "safe";

export interface InkTheme {
  /** Branding, headings, the active command. */
  primary: string;
  /** Secondary highlight — tool names, links. */
  accent: string;
  /** Body text. */
  text: string;
  /** De-emphasised text: timestamps, descriptions, hints. */
  muted: string;
  /** The user's own messages. */
  user: string;
  /** Model output. */
  assistant: string;
  success: string;
  warning: string;
  error: string;
  /** Border colour for the two framed regions. */
  border: string;
  /** Added / removed lines in a diff. */
  diffAdd: string;
  diffRemove: string;
  diffMeta: string;
  /** Row backgrounds behind a diff line — the whole row, not just the sign. */
  diffAddBg: string;
  diffRemoveBg: string;
  /** Line-number gutter. */
  gutter: string;
  /** Syntax highlighting inside code and diffs. */
  syntaxKeyword: string;
  syntaxString: string;
  syntaxComment: string;
  syntaxNumber: string;
}

const DARK: InkTheme = {
  primary: "blueBright",
  accent: "cyan",
  // whiteBright (ANSI 97), not white (ANSI 37). Terminal palettes render 37 as
  // a light grey — Campbell maps it to #CCCCCC — so body text came out dull
  // next to the coloured markers. 97 is the pure white the reference CLIs use.
  // Kept as a named colour rather than #ffffff so it still follows the user's
  // palette and degrades sensibly on 16-colour terminals.
  text: "whiteBright",
  muted: "gray",
  user: "green",
  assistant: "cyan",
  success: "green",
  warning: "yellow",
  error: "red",
  border: "gray",
  diffAdd: "greenBright",
  diffRemove: "redBright",
  diffMeta: "cyanBright",
  diffAddBg: "#0b2f14",
  diffRemoveBg: "#3d1114",
  gutter: "gray",
  syntaxKeyword: "magenta",
  syntaxString: "green",
  syntaxComment: "gray",
  syntaxNumber: "yellow",
};

const LIGHT: InkTheme = {
  ...DARK,
  primary: "blue",
  accent: "magenta",
  text: "black",
  muted: "gray",
  assistant: "blue",
  diffAdd: "green",
  diffRemove: "red",
  diffMeta: "blue",
  diffAddBg: "#d6f5dd",
  diffRemoveBg: "#ffd7d5",
  gutter: "gray",
  syntaxKeyword: "magenta",
  syntaxString: "green",
  syntaxComment: "gray",
  syntaxNumber: "yellow",
};

/** No colour pairs that fail on monochrome or low-contrast terminals. */
const SAFE: InkTheme = {
  // Same reasoning as DARK: 37 reads as grey. This theme has no colour to
  // fall back on, so dull body text is all the reader would get.
  primary: "whiteBright",
  accent: "whiteBright",
  text: "whiteBright",
  muted: "gray",
  user: "whiteBright",
  assistant: "whiteBright",
  success: "whiteBright",
  warning: "whiteBright",
  error: "whiteBright",
  border: "gray",
  diffAdd: "whiteBright",
  diffRemove: "gray",
  diffMeta: "gray",
  diffAddBg: "",
  diffRemoveBg: "",
  gutter: "gray",
  syntaxKeyword: "white",
  syntaxString: "white",
  syntaxComment: "gray",
  syntaxNumber: "white",
};

const THEMES: Record<InkThemeName, InkTheme> = { dark: DARK, light: LIGHT, safe: SAFE };

let active: InkTheme = DARK;
let activeName: InkThemeName = "dark";

export function setInkTheme(name: InkThemeName): void {
  active = THEMES[name] ?? DARK;
  activeName = THEMES[name] ? name : "dark";
}

export function getInkTheme(): InkTheme {
  return active;
}

export function getInkThemeName(): InkThemeName {
  return activeName;
}

export function inkThemeNames(): InkThemeName[] {
  return Object.keys(THEMES) as InkThemeName[];
}

/**
 * NO_COLOR is a cross-tool convention; honouring it avoids emitting escape
 * codes into logs and CI output.
 */
export function autoDetectInkTheme(): void {
  if (process.env["NO_COLOR"]) return setInkTheme("safe");
  const term = (process.env["COLORFGBG"] ?? "").split(";").pop();
  if (term && Number(term) >= 9) return setInkTheme("light");
  setInkTheme("dark");
}
