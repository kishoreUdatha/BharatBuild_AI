import chalk from "chalk";

export type ThemeName = "dark" | "light" | "safe";
type ChalkFn = typeof chalk;

export interface Theme {
  name: ThemeName;
  user: ChalkFn;
  assistant: ChalkFn;
  tool: ChalkFn;
  toolSuccess: ChalkFn;
  toolError: ChalkFn;
  dim: ChalkFn;
  heading: ChalkFn;
  code: ChalkFn;
  statusBar: ChalkFn;
  prompt: ChalkFn;
  success: ChalkFn;
  error: ChalkFn;
  warning: ChalkFn;
  info: ChalkFn;
}

const dark: Theme = {
  name: "dark",
  user: chalk.bold.green,
  assistant: chalk.bold.cyan,
  tool: chalk.yellow,
  toolSuccess: chalk.green,
  toolError: chalk.red,
  dim: chalk.dim,
  heading: chalk.bold.white,
  code: chalk.magenta,
  statusBar: chalk.bgBlack.white,
  prompt: chalk.bold.green,
  success: chalk.green,
  error: chalk.red,
  warning: chalk.yellow,
  info: chalk.cyan,
};

const light: Theme = {
  name: "light",
  user: chalk.bold.blue,
  assistant: chalk.bold.magenta,
  tool: chalk.hex("#a05c00"),
  toolSuccess: chalk.hex("#006600"),
  toolError: chalk.hex("#aa0000"),
  dim: chalk.dim,
  heading: chalk.bold.black,
  code: chalk.hex("#6600aa"),
  statusBar: chalk.bgWhite.black,
  prompt: chalk.bold.blue,
  success: chalk.hex("#006600"),
  error: chalk.hex("#aa0000"),
  warning: chalk.hex("#a05c00"),
  info: chalk.hex("#0066aa"),
};

const safe: Theme = {
  name: "safe",
  user: chalk.bold,
  assistant: chalk.bold,
  tool: chalk.italic,
  toolSuccess: chalk.bold,
  toolError: chalk.bold,
  dim: chalk.dim,
  heading: chalk.bold,
  code: chalk.italic,
  statusBar: chalk.bold,
  prompt: chalk.bold,
  success: chalk.bold,
  error: chalk.bold,
  warning: chalk.bold,
  info: chalk.italic,
};

const themes: Record<ThemeName, Theme> = { dark, light, safe };
let currentTheme: Theme = dark;

export function setTheme(name: ThemeName): void {
  currentTheme = themes[name] ?? dark;
}

export function autoDetectTheme(): void {
  if (process.env["NO_COLOR"]) { currentTheme = safe; return; }
  const bg = process.env["COLORFGBG"];
  if (bg) {
    const parts = bg.split(";");
    const bgCode = parseInt(parts[parts.length - 1] ?? "0");
    currentTheme = bgCode < 8 ? dark : light;
  }
}

export function getTheme(): Theme { return currentTheme; }
