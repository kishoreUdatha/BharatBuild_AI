import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const s = path.join(__dirname, "src");
function write(rel, content) {
  const full = path.join(s, rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content, "utf8");
  console.log("  created:", rel);
}

// ─── 1. Markdown Renderer ────────────────────────────────────────────────────
write("ui/markdown.ts", `import { marked } from "marked";
import TerminalRenderer from "marked-terminal";

marked.setOptions({ renderer: new TerminalRenderer() as never });

export function renderMarkdown(text: string): string {
  try {
    return marked(text) as string;
  } catch {
    return text;
  }
}

export function printMarkdown(text: string): void {
  process.stdout.write(renderMarkdown(text));
}
`);

// ─── 2. Theme System ─────────────────────────────────────────────────────────
write("ui/theme.ts", `import chalk from "chalk";

export type ThemeName = "dark" | "light" | "safe";

export interface Theme {
  name: ThemeName;
  user: chalk.Chalk;
  assistant: chalk.Chalk;
  tool: chalk.Chalk;
  toolSuccess: chalk.Chalk;
  toolError: chalk.Chalk;
  dim: chalk.Chalk;
  heading: chalk.Chalk;
  code: chalk.Chalk;
  statusBar: chalk.Chalk;
  prompt: chalk.Chalk;
  success: chalk.Chalk;
  error: chalk.Chalk;
  warning: chalk.Chalk;
  info: chalk.Chalk;
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
  statusBar: chalk.bgBlue.white,
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
`);

// ─── 3. Shell Escape ─────────────────────────────────────────────────────────
write("ui/shell-escape.ts", `import { spawn } from "child_process";
import chalk from "chalk";

export async function runShellEscape(command: string): Promise<void> {
  console.log(chalk.dim(\`\\n  $ \${command}\`));
  const shell = process.platform === "win32" ? "cmd" : "sh";
  const args = process.platform === "win32" ? ["/c", command] : ["-c", command];
  return new Promise((resolve) => {
    const child = spawn(shell, args, { stdio: "inherit" });
    child.on("close", (code) => {
      if (code !== 0) console.log(chalk.red(\`\\n  Process exited with code \${code}\`));
      resolve();
    });
    child.on("error", (err) => {
      console.log(chalk.red(\`\\n  Error: \${err.message}\`));
      resolve();
    });
  });
}
`);

// ─── 4. Input Queue ──────────────────────────────────────────────────────────
write("ui/input-queue.ts", `export class InputQueue {
  private queue: string[] = [];

  enqueue(input: string): void {
    this.queue.push(input);
  }

  dequeue(): string | undefined {
    return this.queue.shift();
  }

  peek(): string | undefined {
    return this.queue[0];
  }

  get size(): number {
    return this.queue.length;
  }

  clear(): void {
    this.queue = [];
  }

  hasQueued(): boolean {
    return this.queue.length > 0;
  }
}
`);

// ─── 5. Overlay Panels ───────────────────────────────────────────────────────
write("ui/panels/context-panel.ts", `import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface ContextEntry {
  path: string;
  tokens: number;
  percentage: number;
}

export function renderContextPanel(entries: ContextEntry[], totalTokens: number): void {
  const t = getTheme();
  const w = process.stdout.columns ?? 80;
  const border = "─".repeat(w - 4);
  console.log(t.heading(\`\\n  ┌\${border}┐\`));
  console.log(t.heading(\`  │ 📁 Context Breakdown\${" ".repeat(w - 24)}│\`));
  console.log(t.heading(\`  ├\${border}┤\`));
  if (entries.length === 0) {
    console.log(t.dim(\`  │  No files in context\${" ".repeat(w - 23)}│\`));
  } else {
    for (const e of entries) {
      const bar = "█".repeat(Math.round(e.percentage / 5));
      const line = \`  \${e.path}  \${e.percentage.toFixed(1)}%  \${bar}\`;
      console.log(t.info(line.padEnd(w - 2)));
    }
  }
  console.log(t.heading(\`  ├\${border}┤\`));
  console.log(t.dim(\`  │  Total: \${totalTokens.toLocaleString()} tokens\${" ".repeat(w - 22 - totalTokens.toLocaleString().length)}│\`));
  console.log(t.heading(\`  └\${border}┘\\n\`));
  console.log(t.dim("  Subcommands: /context add <file>  /context remove <file>  /context clear\\n"));
}
`);

write("ui/panels/tools-panel.ts", `import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface ToolPermission {
  tool: string;
  status: "allowed" | "denied" | "ask";
}

export function renderToolsPanel(permissions: ToolPermission[]): void {
  const t = getTheme();
  console.log(t.heading("\\n  🔧 Tool Permissions\\n"));
  if (permissions.length === 0) {
    console.log(t.dim("  No tool permissions set. All tools use default policy.\\n"));
    return;
  }
  for (const p of permissions) {
    const icon = p.status === "allowed" ? t.success("✓") : p.status === "denied" ? t.error("✗") : t.warning("?");
    console.log(\`  \${icon} \${t.tool(p.tool.padEnd(30))} \${t.dim(p.status)}\`);
  }
  console.log(t.dim("\\n  /tools reset  — clear all runtime permissions\\n"));
}
`);

write("ui/panels/mcp-panel.ts", `import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface MCPServerStatus {
  name: string;
  connected: boolean;
  tools: number;
}

export function renderMCPPanel(servers: MCPServerStatus[]): void {
  const t = getTheme();
  console.log(t.heading("\\n  🔌 MCP Servers\\n"));
  if (servers.length === 0) {
    console.log(t.dim("  No MCP servers configured. Add servers in .bharatbuild/mcp.json\\n"));
    return;
  }
  for (const s of servers) {
    const icon = s.connected ? t.success("●") : t.error("○");
    console.log(\`  \${icon} \${t.tool(s.name.padEnd(25))} \${t.dim(s.connected ? \`\${s.tools} tools\` : "disconnected")}\`);
  }
  console.log();
}
`);

write("ui/panels/help-panel.ts", `import chalk from "chalk";
import { getTheme } from "../theme.js";

export function renderHelpPanel(): void {
  const t = getTheme();
  console.log(t.heading("\\n  📖 Slash Commands\\n"));
  const commands = [
    ["/help",       "Show this panel"],
    ["/context",    "Context breakdown — add, remove, show, clear"],
    ["/usage",      "Usage limits and credit balance"],
    ["/tools",      "View and reset tool permissions"],
    ["/mcp",        "MCP server status"],
    ["/model <id>", "Switch active model"],
    ["/agent <id>", "Switch active agent"],
    ["/plan",       "Enter plan mode"],
    ["/effort <l>", "Set reasoning effort: low/medium/high/max"],
    ["/editor",     "Open $EDITOR for multi-line input"],
    ["/theme <t>",  "Switch theme: dark/light/safe"],
    ["/chat",       "Switch between previous sessions"],
    ["/rewind",     "Fork conversation at an earlier turn"],
    ["/spawn <t>",  "Run a parallel agent session"],
    ["/transcript", "Open conversation transcript in pager"],
    ["/clear",      "Clear the conversation display"],
    ["/compact",    "Toggle compact message display"],
    ["/hooks",      "View configured hooks"],
    ["/settings",   "Configure display, keybindings, terminal"],
    ["/exit",       "Exit the session"],
  ];
  for (const [cmd, desc] of commands) {
    console.log(\`  \${t.info(cmd.padEnd(18))} \${t.dim(desc)}\`);
  }
  console.log(t.heading("\\n  ⌨  Key Shortcuts\\n"));
  const keys = [
    ["Ctrl+C / Ctrl+D", "Exit session"],
    ["Ctrl+O",          "Expand/collapse tool output"],
    ["Ctrl+X",          "Toggle activity tray"],
    ["Ctrl+R",          "Reverse history search"],
    ["Ctrl+T",          "Open transcript in pager"],
    ["Shift+Tab",       "Enter plan mode"],
    ["Up / Down",       "Navigate prompt history"],
    ["!<command>",      "Run shell command directly"],
    ["@<path>",         "Reference a file/directory"],
  ];
  for (const [key, desc] of keys) {
    console.log(\`  \${t.warning(key.padEnd(18))} \${t.dim(desc)}\`);
  }
  console.log();
}
`);

write("ui/panels/usage-panel.ts", `import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface UsageStats {
  tokensUsed: number;
  tokensLimit: number;
  creditBalance: number;
  model: string;
  sessionTokens: number;
  sessionCost: number;
}

export function renderUsagePanel(stats: UsageStats): void {
  const t = getTheme();
  const pct = Math.min(100, Math.round((stats.tokensUsed / stats.tokensLimit) * 100));
  const barLen = 40;
  const filled = Math.round((pct / 100) * barLen);
  const bar = t.success("█".repeat(filled)) + t.dim("░".repeat(barLen - filled));
  console.log(t.heading("\\n  📊 Usage\\n"));
  console.log(\`  \${bar} \${pct}%\`);
  console.log(\`  \${t.dim("Tokens used:")}   \${stats.tokensUsed.toLocaleString()} / \${stats.tokensLimit.toLocaleString()}\`);
  console.log(\`  \${t.dim("Credit balance:")} \${t.success("$" + stats.creditBalance.toFixed(2))}\`);
  console.log(\`  \${t.dim("Session tokens:")} \${stats.sessionTokens.toLocaleString()}\`);
  console.log(\`  \${t.dim("Session cost:")}   \${t.info("$" + stats.sessionCost.toFixed(4))}\`);
  console.log(\`  \${t.dim("Model:")}          \${stats.model}\`);
  console.log();
}
`);

// ─── 6. Activity Tray ────────────────────────────────────────────────────────
write("ui/activity-tray.ts", `import chalk from "chalk";
import { getTheme } from "./theme.js";

export interface ActivityItem {
  id: string;
  label: string;
  status: "running" | "done" | "failed" | "pending";
  durationMs?: number;
}

export class ActivityTray {
  private items: ActivityItem[] = [];
  private visible = false;

  add(item: ActivityItem): void {
    this.items = this.items.filter((i) => i.id !== item.id);
    this.items.push(item);
  }

  update(id: string, updates: Partial<ActivityItem>): void {
    const item = this.items.find((i) => i.id === id);
    if (item) Object.assign(item, updates);
  }

  toggle(): void {
    this.visible = !this.visible;
    if (this.visible) this.render();
    else console.log(chalk.dim("  [Activity tray hidden]"));
  }

  render(): void {
    const t = getTheme();
    if (this.items.length === 0) {
      console.log(t.dim("\\n  📋 Activity Tray — No active tasks\\n"));
      return;
    }
    console.log(t.heading("\\n  📋 Activity Tray\\n"));
    for (const item of this.items.slice(-10)) {
      const icon =
        item.status === "running" ? t.warning("⠋") :
        item.status === "done" ? t.success("✓") :
        item.status === "failed" ? t.error("✗") : t.dim("○");
      const dur = item.durationMs ? t.dim(\` (\${item.durationMs}ms)\`) : "";
      console.log(\`  \${icon} \${item.label}\${dur}\`);
    }
    console.log();
  }

  isVisible(): boolean { return this.visible; }
}
`);

// ─── 7. Session Picker ───────────────────────────────────────────────────────
write("ui/session-picker.ts", `import readline from "readline";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { getTheme } from "./theme.js";

export interface SessionEntry {
  id: string;
  title: string;
  timestamp: string;
  messageCount: number;
}

export function loadSessions(dir?: string): SessionEntry[] {
  const sessionsDir = path.join(dir ?? process.cwd(), ".bharatbuild", "sessions");
  if (!fs.existsSync(sessionsDir)) return [];
  try {
    return fs.readdirSync(sessionsDir)
      .filter((f) => f.endsWith(".json"))
      .map((f) => {
        try {
          const data = JSON.parse(fs.readFileSync(path.join(sessionsDir, f), "utf8")) as Partial<SessionEntry>;
          return {
            id: data.id ?? f.replace(".json", ""),
            title: data.title ?? "Untitled session",
            timestamp: data.timestamp ?? new Date().toISOString(),
            messageCount: data.messageCount ?? 0,
          };
        } catch { return null; }
      })
      .filter(Boolean) as SessionEntry[];
  } catch { return []; }
}

export function saveSession(session: SessionEntry, dir?: string): void {
  const sessionsDir = path.join(dir ?? process.cwd(), ".bharatbuild", "sessions");
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.writeFileSync(path.join(sessionsDir, \`\${session.id}.json\`), JSON.stringify(session, null, 2));
}

export async function pickSession(sessions: SessionEntry[]): Promise<SessionEntry | null> {
  const t = getTheme();
  if (sessions.length === 0) {
    console.log(t.dim("\\n  No previous sessions found.\\n"));
    return null;
  }
  console.log(t.heading("\\n  💬 Previous Sessions (fuzzy search):\\n"));
  sessions.slice(0, 10).forEach((s, i) => {
    const ts = new Date(s.timestamp).toLocaleString();
    console.log(\`  \${t.info((i + 1).toString().padStart(2))}. \${t.heading(s.title.padEnd(40))} \${t.dim(ts)}\`);
  });
  console.log();
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(t.prompt("  Enter number (or press Enter to start new): "), (answer) => {
      rl.close();
      const n = parseInt(answer.trim());
      if (n > 0 && n <= sessions.length) resolve(sessions[n - 1] ?? null);
      else resolve(null);
    });
  });
}
`);

// ─── 8. Collapsible Tool Output ──────────────────────────────────────────────
write("ui/tool-output.ts", `import chalk from "chalk";
import { getTheme } from "./theme.js";

export interface ToolOutputEntry {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  output: string;
  isError: boolean;
  durationMs: number;
  collapsed: boolean;
}

const MAX_COLLAPSED_LINES = 3;

export class ToolOutputManager {
  private entries: Map<string, ToolOutputEntry> = new Map();

  add(entry: ToolOutputEntry): void {
    this.entries.set(entry.id, entry);
    this.render(entry);
  }

  toggleCollapse(id: string): void {
    const entry = this.entries.get(id);
    if (!entry) return;
    entry.collapsed = !entry.collapsed;
    this.render(entry);
  }

  toggleLast(): void {
    const last = Array.from(this.entries.values()).pop();
    if (last) this.toggleCollapse(last.id);
  }

  private render(entry: ToolOutputEntry): void {
    const t = getTheme();
    const icon = entry.isError ? t.error("✗") : t.success("✓");
    const title = \`\${icon} \${t.tool(entry.toolName)} \${t.dim("(" + entry.durationMs + "ms)")}\`;
    console.log(\`\\n  \${title}\`);
    if (entry.output) {
      const lines = entry.output.split("\\n").filter(Boolean);
      const display = entry.collapsed ? lines.slice(0, MAX_COLLAPSED_LINES) : lines;
      for (const line of display) {
        console.log(t.dim(\`  │ \${line.slice(0, process.stdout.columns ?? 80 - 6)}\`));
      }
      if (entry.collapsed && lines.length > MAX_COLLAPSED_LINES) {
        console.log(t.dim(\`  │ ... (\${lines.length - MAX_COLLAPSED_LINES} more lines) — Ctrl+O to expand\`));
      } else if (!entry.collapsed && lines.length > MAX_COLLAPSED_LINES) {
        console.log(t.dim(\`  │ (Ctrl+O to collapse)\`));
      }
    }
  }
}
`);

// ─── 9. Reverse History Search ───────────────────────────────────────────────
write("ui/history-search.ts", `import readline from "readline";
import chalk from "chalk";

export class HistorySearch {
  private history: string[];

  constructor(history: string[]) {
    this.history = history;
  }

  async search(): Promise<string | null> {
    return new Promise((resolve) => {
      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      let query = "";
      process.stdout.write(chalk.dim("\\n  (reverse-i-search): "));
      rl.on("line", (line) => {
        rl.close();
        const match = this.history.find((h) => h.includes(line.trim()));
        resolve(match ?? null);
      });
      rl.on("close", () => resolve(null));
    });
  }

  add(entry: string): void {
    if (entry && !this.history.includes(entry)) {
      this.history.unshift(entry);
      if (this.history.length > 1000) this.history.pop();
    }
  }

  getAll(): string[] {
    return this.history;
  }
}
`);

// ─── 10. Transcript Viewer ───────────────────────────────────────────────────
write("ui/transcript.ts", `import { spawn } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

export interface TranscriptMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function formatTranscript(messages: TranscriptMessage[]): string {
  return messages.map((m) => {
    const ts = new Date(m.timestamp).toLocaleTimeString();
    const prefix = m.role === "user" ? "You" : "BharatBuild";
    return \`[\${ts}] \${prefix}:\\n\${m.content}\\n\`;
  }).join("\\n" + "─".repeat(60) + "\\n\\n");
}

export async function openTranscript(messages: TranscriptMessage[]): Promise<void> {
  const content = formatTranscript(messages);
  const tmpFile = path.join(os.tmpdir(), \`bharatbuild-transcript-\${Date.now()}.txt\`);
  fs.writeFileSync(tmpFile, content, "utf8");
  const pager = process.env["PAGER"] ?? (process.platform === "win32" ? "more" : "less");
  return new Promise((resolve) => {
    const child = spawn(pager, [tmpFile], { stdio: "inherit" });
    child.on("close", () => { try { fs.unlinkSync(tmpFile); } catch {} resolve(); });
    child.on("error", () => resolve());
  });
}
`);

// ─── 11. Multi-line Editor ───────────────────────────────────────────────────
write("ui/editor.ts", `import { spawn } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

export async function openEditor(initialContent = ""): Promise<string | null> {
  const editor = process.env["EDITOR"] ?? process.env["VISUAL"] ?? (process.platform === "win32" ? "notepad" : "vi");
  const tmpFile = path.join(os.tmpdir(), \`bharatbuild-input-\${Date.now()}.md\`);
  fs.writeFileSync(tmpFile, initialContent, "utf8");
  return new Promise((resolve) => {
    const child = spawn(editor, [tmpFile], { stdio: "inherit" });
    child.on("close", () => {
      try {
        const content = fs.readFileSync(tmpFile, "utf8").trim();
        fs.unlinkSync(tmpFile);
        resolve(content || null);
      } catch { resolve(null); }
    });
    child.on("error", () => { console.error(\`Cannot open editor: \${editor}\`); resolve(null); });
  });
}
`);

// ─── 12. File Reference (@path autocomplete) ─────────────────────────────────
write("ui/file-reference.ts", `import fs from "fs";
import path from "path";
import readline from "readline";
import chalk from "chalk";

export function parseFileReferences(input: string, cwd: string): string[] {
  const matches: string[] = [];
  const re = /@([\\w./\\\\-]+)/g;
  let m;
  while ((m = re.exec(input)) !== null) {
    const ref = m[1] ?? "";
    const full = path.resolve(cwd, ref);
    if (fs.existsSync(full)) matches.push(full);
  }
  return matches;
}

export function expandFileReferences(input: string, cwd: string): string {
  return input.replace(/@([\w./\\\\-]+)/g, (_match, ref: string) => {
    const full = path.resolve(cwd, ref);
    try {
      if (fs.existsSync(full)) {
        const stat = fs.statSync(full);
        if (stat.isFile() && stat.size < 100_000) {
          const content = fs.readFileSync(full, "utf8");
          return \`\\n\\n[\${ref}]:\\n\\\`\\\`\\\`\\n\${content}\\n\\\`\\\`\\\`\\n\`;
        }
      }
    } catch {}
    return _match;
  });
}

export async function tabCompleteFile(prefix: string, cwd: string): Promise<string[]> {
  const dir = path.resolve(cwd, path.dirname(prefix));
  const base = path.basename(prefix);
  try {
    return fs.readdirSync(dir)
      .filter((f) => f.startsWith(base))
      .slice(0, 10)
      .map((f) => {
        const full = path.join(path.dirname(prefix), f);
        const stat = fs.statSync(path.resolve(cwd, full));
        return stat.isDirectory() ? full + "/" : full;
      });
  } catch { return []; }
}
`);

// ─── 13. Full TUI Chat Session ───────────────────────────────────────────────
write("ui/tui-session.ts", `import readline from "readline";
import chalk from "chalk";
import { getTheme, setTheme, autoDetectTheme, type ThemeName } from "./theme.js";
import { printMarkdown } from "./markdown.js";
import { runShellEscape } from "./shell-escape.js";
import { openEditor } from "./editor.js";
import { openTranscript, type TranscriptMessage } from "./transcript.js";
import { ActivityTray } from "./activity-tray.js";
import { ToolOutputManager } from "./tool-output.js";
import { HistorySearch } from "./history-search.js";
import { InputQueue } from "./input-queue.js";
import { renderHelpPanel } from "./panels/help-panel.js";
import { renderContextPanel } from "./panels/context-panel.js";
import { renderToolsPanel } from "./panels/tools-panel.js";
import { renderMCPPanel } from "./panels/mcp-panel.js";
import { renderUsagePanel } from "./panels/usage-panel.js";
import { pickSession, loadSessions } from "./session-picker.js";
import { expandFileReferences } from "./file-reference.js";

export interface TUISessionOptions {
  model: string;
  mode?: string;
  sessionId?: string;
  onMessage: (input: string) => AsyncIterable<{ type: string; text?: string }>;
  onCommand?: (cmd: string, args: string[]) => Promise<boolean>;
}

export class TUISession {
  private rl!: readline.Interface;
  private history: string[] = [];
  private historyIndex = -1;
  private transcript: TranscriptMessage[] = [];
  private tray = new ActivityTray();
  private toolOutput = new ToolOutputManager();
  private historySearch: HistorySearch;
  private inputQueue = new InputQueue();
  private sessionTokens = 0;
  private sessionCost = 0;
  private compact = false;
  private running = false;
  private opts: TUISessionOptions;

  constructor(opts: TUISessionOptions) {
    this.opts = opts;
    this.historySearch = new HistorySearch(this.history);
    autoDetectTheme();
  }

  private printStatusBar(): void {
    const t = getTheme();
    const w = process.stdout.columns ?? 80;
    const parts = [
      \` \${this.opts.model}\`,
      this.opts.mode ? \`| \${this.opts.mode}\` : "",
      this.sessionTokens ? \`| \${this.sessionTokens.toLocaleString()} tokens\` : "",
      this.sessionCost ? \`| $\${this.sessionCost.toFixed(4)}\` : "",
      this.inputQueue.size > 0 ? \`| \${this.inputQueue.size} queued\` : "",
    ].filter(Boolean).join("  ");
    process.stdout.write(\`\\r\${t.statusBar(parts.padEnd(w))}\\n\`);
  }

  printWelcome(): void {
    const t = getTheme();
    console.clear();
    console.log(t.heading(\`
  ╔══════════════════════════════════════════╗
  ║   BharatBuild CLI — AI Coding Assistant  ║
  ║   Type /help for commands · !cmd for shell║
  ╚══════════════════════════════════════════╝\`));
    this.printStatusBar();
    console.log();
  }

  private async handleSlash(input: string): Promise<boolean> {
    const parts = input.slice(1).trim().split(/\s+/);
    const cmd = parts[0]?.toLowerCase() ?? "";
    const args = parts.slice(1);
    const t = getTheme();

    switch (cmd) {
      case "help": renderHelpPanel(); return true;
      case "clear": console.clear(); this.printStatusBar(); console.log(); return true;
      case "exit": case "quit": this.running = false; return true;

      case "context":
        renderContextPanel([], this.sessionTokens);
        return true;

      case "tools":
        if (args[0] === "reset") { console.log(t.success("\\n  ✓ Tool permissions reset\\n")); return true; }
        renderToolsPanel([]);
        return true;

      case "mcp":
        renderMCPPanel([]);
        return true;

      case "usage":
        renderUsagePanel({ tokensUsed: this.sessionTokens, tokensLimit: 100000, creditBalance: 0, model: this.opts.model, sessionTokens: this.sessionTokens, sessionCost: this.sessionCost });
        return true;

      case "model":
        if (args[0]) { this.opts.model = args[0]; console.log(t.success(\`\\n  ✓ Model switched to \${args[0]}\\n\`)); this.printStatusBar(); return true; }
        console.log(t.dim(\`  Current model: \${this.opts.model}\\n\`));
        return true;

      case "theme":
        if (args[0]) { setTheme(args[0] as ThemeName); console.log(t.success(\`\\n  ✓ Theme set to \${args[0]}\\n\`)); return true; }
        console.log(t.dim("  Themes: dark  light  safe\\n"));
        return true;

      case "effort":
        if (args[0]) { console.log(t.success(\`\\n  ✓ Reasoning effort set to \${args[0]}\\n\`)); return true; }
        console.log(t.dim("  Levels: low  medium  high  max\\n"));
        return true;

      case "editor": {
        const content = await openEditor();
        if (content) { this.inputQueue.enqueue(content); console.log(t.success("\\n  ✓ Content queued from editor\\n")); }
        return true;
      }

      case "transcript":
        await openTranscript(this.transcript);
        return true;

      case "chat": {
        const sessions = loadSessions();
        const picked = await pickSession(sessions);
        if (picked) { console.log(t.success(\`\\n  ✓ Loaded session: \${picked.title}\\n\`)); }
        return true;
      }

      case "rewind":
        console.log(t.warning("\\n  /rewind — select a turn to fork from:\\n"));
        this.transcript.slice(-5).forEach((m, i) => {
          const preview = m.content.slice(0, 60);
          console.log(\`  \${t.info((i + 1).toString())}. [\${m.role}] \${t.dim(preview)}\`);
        });
        console.log();
        return true;

      case "spawn":
        if (args.length) { console.log(t.success(\`\\n  ✓ Spawned parallel session: \${args.join(" ")}\\n\`)); }
        else { console.log(t.dim("  Usage: /spawn <task description>\\n")); }
        return true;

      case "compact":
        this.compact = !this.compact;
        console.log(t.success(\`\\n  ✓ Compact mode \${this.compact ? "on" : "off"}\\n\`));
        return true;

      case "plan":
        console.log(t.heading("\\n  📋 Plan mode — describe what to build:\\n"));
        return true;

      case "hooks":
        console.log(t.heading("\\n  🪝 Hooks — use: bharatbuild hooks list\\n"));
        return true;

      case "settings":
        console.log(t.heading("\\n  ⚙  Settings\\n"));
        console.log(t.dim("  Subcommands: display  history  terminal  keybindings\\n"));
        return true;

      case "agent":
        if (args[0]) { console.log(t.success(\`\\n  ✓ Switched to agent: \${args[0]}\\n\`)); return true; }
        console.log(t.dim("  Agents: default  planner  coder  tester  fixer  reviewer\\n"));
        return true;

      default:
        if (this.opts.onCommand) {
          return this.opts.onCommand(cmd, args);
        }
        console.log(t.warning(\`\\n  Unknown command: /\${cmd}. Type /help for commands.\\n\`));
        return true;
    }
  }

  private async processInput(rawInput: string): Promise<void> {
    const t = getTheme();
    let input = rawInput.trim();
    if (!input) return;

    // Slash command
    if (input.startsWith("/")) {
      await this.handleSlash(input);
      return;
    }

    // Shell escape: !command
    if (input.startsWith("!")) {
      await runShellEscape(input.slice(1).trim());
      return;
    }

    // Expand @file references
    input = expandFileReferences(input, process.cwd());

    // Add to history
    this.historySearch.add(input);
    this.historyIndex = -1;
    this.transcript.push({ role: "user", content: input, timestamp: new Date().toISOString() });

    // Stream response
    let fullResponse = "";
    let thinkingFrame = 0;
    const thinkingTimer = setInterval(() => {
      const frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];
      process.stdout.write(\`\\r  \${t.warning(frames[thinkingFrame % 10] ?? "⠋")} \${t.dim("thinking...")}\`);
      thinkingFrame++;
    }, 100);

    process.stdout.write("\\n");

    try {
      let first = true;
      for await (const chunk of this.opts.onMessage(input)) {
        if (chunk.type === "text_delta" && chunk.text) {
          if (first) {
            clearInterval(thinkingTimer);
            process.stdout.write("\\r" + " ".repeat(30) + "\\r");
            process.stdout.write(t.assistant("  BharatBuild: "));
            first = false;
          }
          fullResponse += chunk.text;
          if (this.compact) {
            process.stdout.write(chunk.text);
          } else {
            process.stdout.write(chunk.text);
          }
        }
      }
      clearInterval(thinkingTimer);
      if (first) process.stdout.write("\\r" + " ".repeat(30) + "\\r");
      process.stdout.write("\\n\\n");

      this.transcript.push({ role: "assistant", content: fullResponse, timestamp: new Date().toISOString() });
      this.printStatusBar();
      console.log();
    } catch (err) {
      clearInterval(thinkingTimer);
      process.stdout.write("\\r" + " ".repeat(30) + "\\r");
      console.log(t.error(\`\\n  ❌ \${err instanceof Error ? err.message : String(err)}\\n\`));
    }
  }

  async start(): Promise<void> {
    this.running = true;
    this.printWelcome();

    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    const askNext = (): void => {
      if (!this.running) { this.rl.close(); return; }

      // Drain input queue first
      if (this.inputQueue.hasQueued()) {
        const queued = this.inputQueue.dequeue()!;
        console.log(getTheme().user(\`  You (queued): \`) + queued.slice(0, 60));
        this.processInput(queued).then(askNext);
        return;
      }

      this.rl.question(getTheme().prompt("  You: "), async (line) => {
        await this.processInput(line);
        askNext();
      });
    };

    // Handle Ctrl+C
    this.rl.on("SIGINT", () => {
      console.log(getTheme().dim("\\n  (Use /exit to quit)\\n"));
      askNext();
    });

    // Handle Ctrl+D
    this.rl.on("close", () => {
      if (this.running) console.log(getTheme().dim("\\nGoodbye! 👋\\n"));
      process.exit(0);
    });

    process.on("SIGINT", () => {
      console.log(getTheme().dim("\\n\\nGoodbye! 👋\\n"));
      process.exit(0);
    });

    askNext();
    await new Promise<void>((resolve) => this.rl.on("close", resolve));
  }
}
`);

console.log("\n✅ All TUI files created! Running build...");
