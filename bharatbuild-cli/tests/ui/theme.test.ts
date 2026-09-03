import { describe, it, expect, afterEach } from "vitest";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  setInkTheme,
  getInkTheme,
  getInkThemeName,
  inkThemeNames,
  type InkTheme,
} from "../../src/ui/ink/theme.js";

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../src/ui/ink");

afterEach(() => setInkTheme("dark"));

describe("theme registry", () => {
  it("ships the three advertised themes", () => {
    expect(inkThemeNames().sort()).toEqual(["dark", "light", "safe"]);
  });

  it("switches the active theme", () => {
    setInkTheme("light");
    expect(getInkThemeName()).toBe("light");
    setInkTheme("safe");
    expect(getInkThemeName()).toBe("safe");
  });

  it("falls back to dark for an unknown name", () => {
    setInkTheme("neon" as never);
    expect(getInkThemeName()).toBe("dark");
  });

  it("defines every token in every theme", () => {
    const tokens: (keyof InkTheme)[] = [
      "primary", "accent", "text", "muted", "user", "assistant",
      "success", "warning", "error", "border", "diffAdd", "diffRemove", "diffMeta",
    ];
    for (const name of inkThemeNames()) {
      setInkTheme(name);
      const theme = getInkTheme();
      for (const token of tokens) {
        expect(theme[token], `${name}.${token}`).toBeTruthy();
      }
    }
  });

  it("keeps the safe theme free of colour hues", () => {
    // For monochrome / low-contrast terminals. This listed the exact strings
    // ["white", "gray", ""], so it failed when `white` became `whiteBright` —
    // a change that does not violate the rule at all, since bright white is
    // not a hue. Assert the rule instead: no red/green/blue/cyan/magenta/
    // yellow anywhere. An empty string stays legal; it means "no tint", which
    // is what a low-contrast terminal wants for diff row backgrounds.
    setInkTheme("safe");
    const HUE = /red|green|blue|cyan|magenta|yellow/i;
    for (const [token, value] of Object.entries(getInkTheme())) {
      expect(HUE.test(String(value)), `safe.${token} = "${String(value)}"`).toBe(false);
    }
  });

  it("gives the safe theme real contrast between body and muted text", () => {
    // The point of the theme is legibility without colour, so the two greys
    // must not collapse into each other.
    setInkTheme("safe");
    const t = getInkTheme();
    expect(t.text).not.toBe(t.muted);
  });
});

describe("chrome matches kiro-cli's density", () => {
  const files = fs.readdirSync(SRC).filter((f) => f.endsWith(".tsx"));
  const source = files.map((f) => fs.readFileSync(path.join(SRC, f), "utf8")).join("\n");

  it("frames exactly the six regions that should be framed", () => {
    // The rule, rather than the number: a frame marks something that is not
    // transcript. That is the welcome panel, the input prompt, fenced code,
    // and the three modal dialogs — the approval prompt, the rewind picker and
    // the ask_user question — each of which interrupts and holds the keyboard
    // until it is answered.
    //
    // Tool cards, the command palette and the hint line stay unframed, so the
    // conversation reads as terminal output rather than a stack of dialogs.
    // A seventh frame means something transcript-shaped grew a box.
    const borders = source.match(/borderStyle=/g) ?? [];
    expect(borders).toHaveLength(6);
  });

  it("frames the input prompt", () => {
    const input = fs.readFileSync(path.join(SRC, "InputPrompt.tsx"), "utf8");
    expect(input).toContain('borderStyle="round"');
  });

  it("leaves the command palette unframed", () => {
    const overlay = fs.readFileSync(path.join(SRC, "SlashOverlay.tsx"), "utf8");
    expect(overlay).not.toContain("borderStyle");
  });

  it("uses only round borders", () => {
    const styles = source.match(/borderStyle="(\w+)"/g) ?? [];
    for (const s of styles) expect(s).toBe('borderStyle="round"');
  });

  it("routes component colours through the theme rather than hardcoding", () => {
    // A representative check: the status bar must not pin its own palette.
    const statusBar = fs.readFileSync(path.join(SRC, "StatusBar.tsx"), "utf8");
    expect(statusBar).toContain("getInkTheme");
    expect(statusBar).not.toMatch(/color="(blueBright|yellowBright|greenBright)"/);
  });
});
