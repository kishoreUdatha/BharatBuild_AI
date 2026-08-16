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

// ═══════════════════════════════════════════════════════════════
// 1. INFRASTRUCTURE: Logging, Proxy, KiroIgnore, Compaction
// ═══════════════════════════════════════════════════════════════

write("infra/logger.ts", `import fs from "fs";
import path from "path";
import os from "os";

export type LogLevel = "error" | "warn" | "info" | "debug" | "trace";
const LEVELS: Record<LogLevel, number> = { error:0, warn:1, info:2, debug:3, trace:4 };

function getLogPath(): string {
  const custom = process.env["BHARATBUILD_CHAT_LOG_FILE"];
  if (custom) return custom;
  const base = process.platform === "win32"
    ? path.join(process.env["TEMP"] ?? os.tmpdir(), "bharatbuild-log")
    : process.platform === "darwin"
    ? path.join(process.env["TMPDIR"] ?? os.tmpdir(), "bharatbuild-log")
    : path.join(process.env["XDG_RUNTIME_DIR"] ?? "/tmp", "bharatbuild-log");
  return path.join(base, "bharatbuild-chat.log");
}

function getLevel(): LogLevel {
  return (process.env["BHARATBUILD_LOG_LEVEL"] as LogLevel) ?? "error";
}

class Logger {
  private logPath = getLogPath();
  private level = getLevel();
  private noColor = !!process.env["BHARATBUILD_LOG_NO_COLOR"];

  private write(level: LogLevel, msg: string, meta?: unknown) {
    if (LEVELS[level] > LEVELS[this.level]) return;
    const line = JSON.stringify({ ts: new Date().toISOString(), level, msg, ...(meta ? { meta } : {}) });
    try { fs.mkdirSync(path.dirname(this.logPath), { recursive: true }); fs.appendFileSync(this.logPath, line + "\\n"); } catch {}
  }

  error(msg: string, meta?: unknown) { this.write("error", msg, meta); }
  warn(msg: string, meta?: unknown) { this.write("warn", msg, meta); }
  info(msg: string, meta?: unknown) { this.write("info", msg, meta); }
  debug(msg: string, meta?: unknown) { this.write("debug", msg, meta); }
  trace(msg: string, meta?: unknown) { this.write("trace", msg, meta); }
  getLogPath() { return this.logPath; }
}

export const logger = new Logger();
`);

write("infra/proxy.ts", `import https from "https";
import http from "http";

export function getProxyConfig(): { httpProxy?: string; httpsProxy?: string; noProxy?: string } {
  return {
    httpProxy: process.env["HTTP_PROXY"] ?? process.env["http_proxy"],
    httpsProxy: process.env["HTTPS_PROXY"] ?? process.env["https_proxy"],
    noProxy: process.env["NO_PROXY"] ?? process.env["no_proxy"],
  };
}

export function isProxyRequired(url: string): boolean {
  const { noProxy } = getProxyConfig();
  if (!noProxy) return true;
  const hostname = new URL(url).hostname;
  return !noProxy.split(",").some((pat) => hostname === pat.trim() || hostname.endsWith("." + pat.trim()));
}

export function applyProxyToFetch(): void {
  const { httpsProxy } = getProxyConfig();
  if (!httpsProxy) return;
  process.env["HTTPS_PROXY"] = httpsProxy;
  process.env["HTTP_PROXY"] = process.env["HTTP_PROXY"] ?? httpsProxy;
}
`);

write("infra/kiroignore.ts", `import fs from "fs";
import path from "path";
import { minimatch } from "minimatch";

export function loadKiroIgnore(dir?: string): string[] {
  const root = dir ?? process.cwd();
  const files = [".bharatbuildignore", ".kiroignore", ".gitignore"];
  const patterns: string[] = ["node_modules/**", "dist/**", ".git/**", "*.log"];
  for (const f of files) {
    const full = path.join(root, f);
    try {
      if (fs.existsSync(full)) {
        const lines = fs.readFileSync(full, "utf8").split("\\n")
          .map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
        patterns.push(...lines);
      }
    } catch {}
  }
  return [...new Set(patterns)];
}

export function isIgnored(filePath: string, patterns: string[]): boolean {
  const rel = path.relative(process.cwd(), filePath).replace(/\\\\/g, "/");
  return patterns.some((pat) => minimatch(rel, pat, { dot: true }));
}
`);

write("infra/compaction.ts", `export interface Message { role: "user" | "assistant"; content: string; }

export function compactMessages(messages: Message[], maxTokens = 80000): Message[] {
  const estimate = (m: Message) => Math.ceil(m.content.length / 4);
  let total = messages.reduce((s, m) => s + estimate(m), 0);
  if (total <= maxTokens) return messages;

  // Keep first system message + last N messages that fit
  const result: Message[] = [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]!;
    const t = estimate(m);
    if (total - t >= maxTokens && i > 0) { total -= t; continue; }
    result.unshift(m);
  }
  if (result.length < messages.length) {
    result.unshift({ role: "assistant", content: "[Earlier conversation compacted to fit context window]" });
  }
  return result;
}

export function shouldCompact(messages: Message[], threshold = 0.8, maxTokens = 100000): boolean {
  const total = messages.reduce((s, m) => s + Math.ceil(m.content.length / 4), 0);
  return total > maxTokens * threshold;
}
`);

write("infra/cloud-sessions.ts", `import fs from "fs";
import path from "path";
import os from "os";

export interface CloudSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Array<{ role: string; content: string }>;
  directory: string;
}

function getSessionsDir(): string {
  const home = process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild");
  return path.join(home, "sessions");
}

export function saveCloudSession(session: CloudSession): void {
  const dir = getSessionsDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, \`\${session.id}.json\`), JSON.stringify(session, null, 2));
}

export function loadCloudSession(id: string): CloudSession | null {
  try {
    const f = path.join(getSessionsDir(), \`\${id}.json\`);
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as CloudSession;
  } catch {}
  return null;
}

export function listCloudSessions(directory?: string): CloudSession[] {
  const dir = getSessionsDir();
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as CloudSession; } catch { return null; } })
    .filter(Boolean)
    .filter((s) => !directory || (s as CloudSession).directory === directory)
    .sort((a, b) => new Date((b as CloudSession).updatedAt).getTime() - new Date((a as CloudSession).updatedAt).getTime()) as CloudSession[];
}

export function deleteCloudSession(id: string): boolean {
  try { fs.unlinkSync(path.join(getSessionsDir(), \`\${id}.json\`)); return true; } catch { return false; }
}
`);

// ═══════════════════════════════════════════════════════════════
// 2. ADVANCED AGENT TOOLS
// ═══════════════════════════════════════════════════════════════

write("tools/agent/goal.ts", `export interface GoalState {
  id: string;
  description: string;
  acceptanceCriteria: string[];
  iteration: number;
  maxIterations: number;
  status: "running" | "complete" | "failed";
  verificationResults: Array<{ iteration: number; passed: boolean; notes: string }>;
}

const goals = new Map<string, GoalState>();

export function createGoal(description: string, criteria: string[], maxIterations = 5): GoalState {
  const g: GoalState = {
    id: \`goal-\${Date.now()}\`, description, acceptanceCriteria: criteria,
    iteration: 0, maxIterations, status: "running", verificationResults: [],
  };
  goals.set(g.id, g); return g;
}

export function updateGoal(id: string, update: Partial<GoalState>): GoalState | null {
  const g = goals.get(id); if (!g) return null;
  Object.assign(g, update); return g;
}

export function verifyGoal(id: string, passed: boolean, notes: string): GoalState | null {
  const g = goals.get(id); if (!g) return null;
  g.verificationResults.push({ iteration: g.iteration, passed, notes });
  g.iteration++;
  if (passed) g.status = "complete";
  else if (g.iteration >= g.maxIterations) g.status = "failed";
  return g;
}

export function getGoal(id: string) { return goals.get(id); }
`);

write("tools/agent/knowledge.ts", `import fs from "fs";
import path from "path";
import os from "os";

export interface KnowledgeEntry {
  id: string;
  name: string;
  content: string;
  tags: string[];
  createdAt: string;
  filePath?: string;
}

function getKnowledgeDir(): string {
  return path.join(process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"), "knowledge");
}

export function addKnowledge(name: string, content: string, tags: string[] = [], filePath?: string): KnowledgeEntry {
  const dir = getKnowledgeDir();
  fs.mkdirSync(dir, { recursive: true });
  const entry: KnowledgeEntry = { id: \`kb-\${Date.now()}\`, name, content, tags, createdAt: new Date().toISOString(), filePath };
  fs.writeFileSync(path.join(dir, \`\${entry.id}.json\`), JSON.stringify(entry, null, 2));
  return entry;
}

export function searchKnowledge(query: string): KnowledgeEntry[] {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return [];
  const q = query.toLowerCase();
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => {
    try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as KnowledgeEntry; } catch { return null; }
  }).filter(Boolean).filter((e) => {
    const entry = e as KnowledgeEntry;
    return entry.name.toLowerCase().includes(q) || entry.content.toLowerCase().includes(q) || entry.tags.some((t) => t.includes(q));
  }) as KnowledgeEntry[];
}

export function listKnowledge(): KnowledgeEntry[] {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => {
    try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as KnowledgeEntry; } catch { return null; }
  }).filter(Boolean) as KnowledgeEntry[];
}

export function removeKnowledge(id: string): boolean {
  try { fs.unlinkSync(path.join(getKnowledgeDir(), \`\${id}.json\`)); return true; } catch { return false; }
}
`);

write("tools/agent/todo.ts", `export interface TodoItem { id: string; description: string; completed: boolean; createdAt: string; }
export interface TodoList { id: string; title: string; items: TodoItem[]; createdAt: string; }

const lists = new Map<string, TodoList>();

export function createTodoList(title: string): TodoList {
  const list: TodoList = { id: \`todo-\${Date.now()}\`, title, items: [], createdAt: new Date().toISOString() };
  lists.set(list.id, list); return list;
}

export function addTodoItem(listId: string, description: string): TodoItem | null {
  const list = lists.get(listId); if (!list) return null;
  const item: TodoItem = { id: \`item-\${Date.now()}\`, description, completed: false, createdAt: new Date().toISOString() };
  list.items.push(item); return item;
}

export function completeTodoItem(listId: string, itemId: string): boolean {
  const list = lists.get(listId); if (!list) return false;
  const item = list.items.find((i) => i.id === itemId); if (!item) return false;
  item.completed = true; return true;
}

export function getTodoList(listId: string) { return lists.get(listId); }
export function getAllLists() { return Array.from(lists.values()); }
`);

write("tools/agent/delegate.ts", `import { EventEmitter } from "events";

export interface DelegatedTask {
  id: string;
  task: string;
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

export class DelegateManager extends EventEmitter {
  private tasks = new Map<string, DelegatedTask>();

  delegate(task: string, handler: (task: string) => Promise<string>): DelegatedTask {
    const t: DelegatedTask = { id: \`delegate-\${Date.now()}\`, task, status: "pending" };
    this.tasks.set(t.id, t);
    t.status = "running"; t.startedAt = new Date().toISOString();
    handler(task).then((result) => {
      t.status = "complete"; t.result = result; t.completedAt = new Date().toISOString();
      this.emit("complete", t);
    }).catch((err: Error) => {
      t.status = "failed"; t.error = err.message; t.completedAt = new Date().toISOString();
      this.emit("failed", t);
    });
    return t;
  }

  getTask(id: string) { return this.tasks.get(id); }
  listTasks() { return Array.from(this.tasks.values()); }
  getStatus(id: string) { return this.tasks.get(id)?.status ?? "not found"; }
}

export const delegateManager = new DelegateManager();
`);

write("tools/agent/subagent.ts", `import { EventEmitter } from "events";

export interface SubagentConfig {
  id: string;
  task: string;
  agent?: string;
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
  error?: string;
  startMs?: number;
  durationMs?: number;
}

export class SubagentManager extends EventEmitter {
  private agents = new Map<string, SubagentConfig>();

  spawn(task: string, agentName?: string, handler?: (task: string) => Promise<string>): SubagentConfig {
    const cfg: SubagentConfig = { id: \`subagent-\${Date.now()}\`, task, agent: agentName ?? "default", status: "pending" };
    this.agents.set(cfg.id, cfg);
    this.emit("spawned", cfg);
    if (handler) {
      cfg.status = "running"; cfg.startMs = Date.now();
      handler(task).then((result) => {
        cfg.status = "complete"; cfg.result = result; cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
        this.emit("complete", cfg);
      }).catch((err: Error) => {
        cfg.status = "failed"; cfg.error = err.message; cfg.durationMs = Date.now() - (cfg.startMs ?? 0);
        this.emit("failed", cfg);
      });
    }
    return cfg;
  }

  listAgents() { return Array.from(this.agents.values()); }
  getAgent(id: string) { return this.agents.get(id); }

  renderCrewMonitor(): string {
    const agents = this.listAgents();
    if (agents.length === 0) return "  No active subagents.";
    return agents.map((a) => {
      const icon = a.status === "running" ? "⠋" : a.status === "complete" ? "✓" : a.status === "failed" ? "✗" : "○";
      const dur = a.durationMs ? \` (\${a.durationMs}ms)\` : "";
      return \`  \${icon} [\${a.agent}] \${a.task.slice(0, 50)}\${dur}\`;
    }).join("\\n");
  }
}

export const subagentManager = new SubagentManager();
`);

write("tools/agent/session-tool.ts", `import { loadConfig, saveConfig, type CLIConfig } from "../../config/config.js";

export interface SessionOverride { key: keyof CLIConfig; value: unknown; original: unknown; }
const overrides: SessionOverride[] = [];

export function sessionSet(key: keyof CLIConfig, value: unknown): SessionOverride {
  const config = loadConfig();
  const original = config[key];
  (config as Record<string, unknown>)[key] = value;
  saveConfig(config);
  const override = { key, value, original };
  overrides.push(override);
  return override;
}

export function sessionGet(key: keyof CLIConfig): unknown {
  return loadConfig()[key];
}

export function sessionList(): SessionOverride[] { return overrides; }

export function sessionReset(key?: keyof CLIConfig): void {
  const config = loadConfig();
  if (key) {
    const o = overrides.find((ov) => ov.key === key);
    if (o) { (config as Record<string, unknown>)[key] = o.original; saveConfig(config); }
  } else {
    for (const o of overrides) { (config as Record<string, unknown>)[o.key] = o.original; }
    saveConfig(config); overrides.length = 0;
  }
}
`);

write("tools/agent/thinking.ts", `export interface ThinkingBlock { id: string; reasoning: string; conclusion: string; durationMs: number; }
const blocks: ThinkingBlock[] = [];

export function recordThinking(reasoning: string, conclusion: string, durationMs: number): ThinkingBlock {
  const block: ThinkingBlock = { id: \`think-\${Date.now()}\`, reasoning, conclusion, durationMs };
  blocks.push(block); return block;
}

export function getThinkingBlocks(): ThinkingBlock[] { return blocks; }
export function clearThinking(): void { blocks.length = 0; }
`);

write("tools/agent/guide.ts", `import type { ModelClient } from "../../runtime/agent-loop.js";

const GUIDE_SYSTEM = \`You are the BharatBuild CLI guide agent. You know everything about the CLI:
- All commands: chat, ask, build, test, fix, review, task, plan, spec, hooks, model, init, login, logout
- All slash commands: /help, /context, /tools, /mcp, /model, /agent, /plan, /effort, /editor, /theme, /chat, /rewind, /spawn, /transcript, /clear, /compact, /paste, /copy, /goal, /guide, /knowledge, /hooks, /settings, /exit
- Features: spec-driven workflow, steering files, hooks, MCP, permissions, quality gates, multi-model support
- Key bindings, TUI features, themes, and configuration
Answer clearly and concisely. You can create steering files, agent configs, and hook configs when asked.\`;

export async function* runGuideAgent(input: string, model: ModelClient): AsyncIterable<string> {
  for await (const chunk of model.complete({
    model: "claude-3-5-haiku-20241022",
    system: GUIDE_SYSTEM,
    messages: [{ role: "user", content: input }],
    tools: [],
    maxTokens: 1500,
  })) {
    if (chunk.type === "text_delta" && chunk.text) yield chunk.text;
  }
}
`);

// ═══════════════════════════════════════════════════════════════
// 3. MISSING CLI COMMANDS
// ═══════════════════════════════════════════════════════════════

write("commands/translate.ts", `import { Command } from "commander";
import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";

export function translateCommand(): Command {
  return new Command("translate")
    .description("Translate natural language to shell commands")
    .argument("[input...]", "Natural language description")
    .option("-n, --count <n>", "Number of suggestions (max 5)", "1")
    .action(async (input: string[], opts) => {
      const query = input.join(" ");
      if (!query) { console.log(chalk.yellow("Usage: bharatbuild translate <description>")); return; }
      const creds = loadCredentials();
      const config = loadConfig();
      const count = Math.min(parseInt(opts.count ?? "1"), 5);
      const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);
      console.log(chalk.dim(\`\\n  Translating: "\${query}"...\\n\`));
      const prompt = \`Translate this natural language description to \${count} shell command(s).
Description: "\${query}"
Rules: Output ONLY the shell command(s), one per line. No explanation. No markdown. Just the command.\`;
      let result = "";
      for await (const chunk of model.complete({ model: config.model ?? "claude-3-5-haiku-20241022", system: "You are a shell command expert.", messages: [{ role: "user", content: prompt }], tools: [], maxTokens: 200 })) {
        if (chunk.type === "text_delta" && chunk.text) result += chunk.text;
      }
      const cmds = result.trim().split("\\n").filter(Boolean).slice(0, count);
      cmds.forEach((cmd, i) => { if (count > 1) console.log(chalk.dim(\`  \${i+1}.\`) + " " + chalk.cyan(cmd)); else console.log("  " + chalk.cyan(cmd)); });
      console.log();
    });
}
`);

write("commands/doctor.ts", `import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { loadCredentials } from "../auth/credentials.js";

interface Check { name: string; passed: boolean; message: string; fix?: string; }

async function runChecks(): Promise<Check[]> {
  const checks: Check[] = [];
  // Node version
  const nodeVer = process.version;
  const nodeMajor = parseInt(nodeVer.slice(1));
  checks.push({ name: "Node.js version", passed: nodeMajor >= 18, message: nodeVer, fix: nodeMajor < 18 ? "Install Node.js 18+" : undefined });
  // Auth
  const creds = loadCredentials();
  checks.push({ name: "Authentication", passed: !!creds, message: creds ? \`Logged in as \${creds.name}\` : "Not logged in", fix: !creds ? "Run: bharatbuild login" : undefined });
  // Config
  const configPath = path.join(process.cwd(), ".bharatbuild.json");
  checks.push({ name: "Project config", passed: fs.existsSync(configPath), message: fs.existsSync(configPath) ? "Found .bharatbuild.json" : "No project config", fix: !fs.existsSync(configPath) ? "Run: bharatbuild init" : undefined });
  // Git
  try { execSync("git --version", { stdio: "pipe" }); checks.push({ name: "Git", passed: true, message: execSync("git --version", { encoding: "utf8" }).trim() }); } catch { checks.push({ name: "Git", passed: false, message: "Git not found", fix: "Install Git" }); }
  // API key
  const hasKey = !!(process.env["ANTHROPIC_API_KEY"] ?? process.env["OPENAI_API_KEY"] ?? process.env["GEMINI_API_KEY"] ?? creds?.token);
  checks.push({ name: "API key", passed: hasKey, message: hasKey ? "API key found" : "No API key set", fix: !hasKey ? "Set ANTHROPIC_API_KEY or run: bharatbuild login" : undefined });
  return checks;
}

export function doctorCommand(): Command {
  return new Command("doctor")
    .description("Diagnose and fix common issues")
    .option("-a, --all", "Run all checks without fixes")
    .option("-s, --strict", "Error on warnings")
    .option("-f, --format <fmt>", "Output format: plain|json", "plain")
    .action(async (opts) => {
      const checks = await runChecks();
      if (opts.format === "json") { console.log(JSON.stringify(checks, null, 2)); return; }
      console.log(chalk.bold("\\n  🩺 BharatBuild Doctor\\n"));
      let allPassed = true;
      for (const c of checks) {
        const icon = c.passed ? chalk.green("✔") : chalk.red("✗");
        console.log(\`  \${icon} \${c.name.padEnd(25)} \${c.passed ? chalk.dim(c.message) : chalk.red(c.message)}\`);
        if (!c.passed) { allPassed = false; if (c.fix) console.log(chalk.yellow(\`       Fix: \${c.fix}\`)); }
      }
      console.log();
      if (allPassed) console.log(chalk.bold.green("  ✔ Everything looks good!\\n"));
      else { console.log(chalk.bold.red("  ✗ Some checks failed. Follow the fixes above.\\n")); if (opts.strict) process.exit(1); }
    });
}
`);

write("commands/update.ts", `import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import readline from "readline";

export function updateCommand(): Command {
  return new Command("update")
    .description("Update BharatBuild CLI to the latest version")
    .option("-y, --non-interactive", "Skip confirmation")
    .action(async (opts) => {
      console.log(chalk.bold("\\n  🔄 BharatBuild CLI Updater\\n"));
      let confirm = opts.nonInteractive;
      if (!confirm) {
        const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
        confirm = await new Promise((r) => rl.question(chalk.cyan("  Update to latest version? [y/N]: "), (a) => { rl.close(); r(a.trim().toLowerCase() === "y"); }));
      }
      if (!confirm) { console.log(chalk.dim("  Update cancelled.\\n")); return; }
      console.log(chalk.dim("  Updating..."));
      try {
        execSync("npm install -g @bharatbuild/cli@latest", { stdio: "inherit" });
        console.log(chalk.bold.green("\\n  ✅ Updated successfully!\\n"));
      } catch {
        console.log(chalk.yellow("\\n  ⚠  Could not auto-update. Run manually: npm install -g @bharatbuild/cli@latest\\n"));
      }
    });
}
`);

write("commands/whoami.ts", `import { Command } from "commander";
import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";

export function whoamiCommand(): Command {
  return new Command("whoami")
    .description("Show current user and auth status")
    .option("-f, --format <fmt>", "Output format: plain|json", "plain")
    .action((opts) => {
      const creds = loadCredentials();
      if (!creds) {
        console.log(chalk.yellow("\\n  Not logged in. Run: bharatbuild login\\n"));
        if (opts.format === "json") console.log(JSON.stringify({ loggedIn: false }));
        return;
      }
      if (opts.format === "json") { console.log(JSON.stringify({ loggedIn: true, name: creds.name, email: creds.email, tier: creds.tier })); return; }
      console.log(chalk.bold("\\n  👤 Current User\\n"));
      console.log(\`  \${chalk.bold("Name:")}    \${creds.name}\`);
      console.log(\`  \${chalk.bold("Email:")}   \${creds.email ?? "N/A"}\`);
      console.log(\`  \${chalk.bold("Plan:")}    \${chalk.cyan(creds.tier ?? "free")}\`);
      console.log(\`  \${chalk.bold("Token:")}   \${creds.token ? chalk.green(creds.token.slice(0, 8) + "…") : "N/A"}\`);
      console.log();
    });
}
`);

write("commands/settings.ts", `import { Command } from "commander";
import chalk from "chalk";
import { loadConfig, saveConfig } from "../config/config.js";
import { openEditor } from "../ui/editor.js";

export function settingsCommand(): Command {
  const cmd = new Command("settings").description("Manage BharatBuild CLI settings");

  cmd.command("list").option("--all", "Show all available settings").option("-f, --format <fmt>", "Output format", "plain").action((opts) => {
    const config = loadConfig();
    if (opts.format === "json") { console.log(JSON.stringify(config, null, 2)); return; }
    console.log(chalk.bold("\\n  ⚙  Settings\\n"));
    for (const [k, v] of Object.entries(config)) {
      console.log(\`  \${chalk.cyan(k.padEnd(25))} \${chalk.dim(JSON.stringify(v))}\`);
    }
    console.log();
  });

  cmd.command("open").description("Open settings in editor").action(async () => {
    const { default: p } = await import("path");
    const { default: os } = await import("os");
    const f = p.join(process.env["BHARATBUILD_HOME"] ?? p.join(os.homedir(), ".bharatbuild"), "settings.json");
    await openEditor(JSON.stringify(loadConfig(), null, 2));
    console.log(chalk.green("\\n  ✅ Settings saved\\n"));
  });

  // Get or set a key
  cmd.argument("[key]", "Setting key").argument("[value]", "Setting value")
    .option("-d, --delete", "Delete a setting")
    .option("-f, --format <fmt>", "Output format", "plain")
    .action((key?: string, value?: string, opts?) => {
      if (!key) { cmd.help(); return; }
      const config = loadConfig();
      if (opts?.delete) { delete (config as Record<string,unknown>)[key]; saveConfig(config); console.log(chalk.green(\`  ✓ Deleted: \${key}\`)); return; }
      if (value === undefined) {
        const v = (config as Record<string,unknown>)[key];
        if (opts?.format === "json") console.log(JSON.stringify({ [key]: v }));
        else console.log(\`  \${key}: \${chalk.cyan(JSON.stringify(v))}\`);
        return;
      }
      let parsed: unknown = value;
      try { parsed = JSON.parse(value); } catch {}
      (config as Record<string,unknown>)[key] = parsed;
      saveConfig(config);
      console.log(chalk.green(\`  ✓ Set \${key} = \${JSON.stringify(parsed)}\`));
    });

  return cmd;
}
`);

write("commands/diagnostic.ts", `import { Command } from "commander";
import chalk from "chalk";
import os from "os";
import { execSync } from "child_process";
import { logger } from "../infra/logger.js";
import pkg from "../../package.json" assert { type: "json" };

export function diagnosticCommand(): Command {
  return new Command("diagnostic")
    .description("Run diagnostic tests and generate system report")
    .option("-f, --format <fmt>", "Output format: plain|json", "plain")
    .option("--force", "Generate limited diagnostics without running app")
    .action((opts) => {
      const info = {
        version: pkg.version,
        platform: process.platform,
        arch: process.arch,
        nodeVersion: process.version,
        cwd: process.cwd(),
        logPath: logger.getLogPath(),
        memory: \`\${(os.totalmem() / 1024 / 1024 / 1024).toFixed(2)} GB\`,
        freeMemory: \`\${(os.freemem() / 1024 / 1024 / 1024).toFixed(2)} GB\`,
        cpus: os.cpus().length,
        shell: process.env["SHELL"] ?? process.env["COMSPEC"] ?? "unknown",
        term: process.env["TERM"] ?? "unknown",
        bharatbuildHome: process.env["BHARATBUILD_HOME"] ?? "~/.bharatbuild",
        proxyHttp: process.env["HTTP_PROXY"] ?? "not set",
        proxyHttps: process.env["HTTPS_PROXY"] ?? "not set",
      };
      if (opts.format === "json") { console.log(JSON.stringify(info, null, 2)); return; }
      console.log(chalk.bold("\\n  🔍 BharatBuild Diagnostic Report\\n"));
      for (const [k, v] of Object.entries(info)) {
        console.log(\`  \${chalk.cyan(k.padEnd(22))} \${chalk.dim(String(v))}\`);
      }
      console.log();
    });
}
`);

write("commands/issue.ts", `import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";

export function issueCommand(): Command {
  return new Command("issue")
    .description("Create a GitHub issue or feedback report")
    .argument("[description...]", "Issue description")
    .option("-f, --force", "Force issue creation")
    .action((description: string[]) => {
      const desc = description.join(" ");
      const title = encodeURIComponent(desc || "Bug report / Feature request");
      const url = \`https://github.com/bharatbuild-ai/bharatbuild-cli/issues/new?title=\${title}&template=bug_report.yml\`;
      console.log(chalk.bold("\\n  🐛 Opening GitHub issue...\\n"));
      console.log(chalk.dim(\`  URL: \${url}\\n\`));
      try {
        const open = process.platform === "win32" ? "start" : process.platform === "darwin" ? "open" : "xdg-open";
        execSync(\`\${open} "\${url}"\`, { stdio: "ignore" });
      } catch {
        console.log(chalk.yellow(\`  Could not open browser. Visit: \${url}\\n\`));
      }
    });
}
`);

write("commands/version.ts", `import { Command } from "commander";
import chalk from "chalk";
import pkg from "../../package.json" assert { type: "json" };

const CHANGELOG: Record<string, string> = {
  "1.0.0": \`## v1.0.0
- Initial release
- Multi-model support: Anthropic, OpenAI, Gemini, Ollama, Bedrock
- Full TUI with themes, panels, markdown rendering
- Spec-driven workflow: requirements, design docs, steering files
- Hooks system: file watcher, git hooks
- MCP support, permissions, quality gates
- 5 user modes: Student, Developer, Founder, College, API Partner\`,
};

export function versionCommand(): Command {
  return new Command("version")
    .description("Show version and changelog")
    .option("--changelog [version]", "Show changelog")
    .action((opts) => {
      console.log(chalk.bold(\`\\n  BharatBuild CLI v\${pkg.version}\\n\`));
      if (opts.changelog) {
        const ver = typeof opts.changelog === "string" ? opts.changelog : pkg.version;
        if (ver === "all") {
          for (const [v, notes] of Object.entries(CHANGELOG)) console.log(notes + "\\n");
        } else {
          console.log(CHANGELOG[ver] ?? \`No changelog for v\${ver}\`);
        }
        console.log();
      }
    });
}
`);

// ═══════════════════════════════════════════════════════════════
// 4. MCP CLI SUBCOMMANDS
// ═══════════════════════════════════════════════════════════════

write("commands/mcp.ts", `import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";

interface MCPServerDef { name: string; command: string; scope: "workspace"|"global"; env?: Record<string,string>; timeout?: number; }

function getMCPConfigPath(scope: "workspace"|"global"): string {
  if (scope === "workspace") return path.join(process.cwd(), ".bharatbuild", "mcp.json");
  const { default: os } = require("os");
  return path.join(process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"), "mcp.json");
}

function loadMCP(scope: "workspace"|"global"): MCPServerDef[] {
  try { const f = getMCPConfigPath(scope); if (fs.existsSync(f)) return (JSON.parse(fs.readFileSync(f, "utf8")) as { servers?: MCPServerDef[] }).servers ?? []; } catch {} return [];
}

function saveMCP(scope: "workspace"|"global", servers: MCPServerDef[]): void {
  const f = getMCPConfigPath(scope); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify({ servers }, null, 2));
}

export function mcpCommand(): Command {
  const cmd = new Command("mcp").description("Manage MCP servers");

  cmd.command("add").description("Add an MCP server").requiredOption("--name <name>", "Server name").requiredOption("--command <cmd>", "Launch command").option("--scope <scope>", "workspace|global", "workspace").option("--env <kv>", "key=val,key2=val2").option("--timeout <ms>", "Timeout ms").option("--force", "Overwrite existing").action((opts) => {
    const servers = loadMCP(opts.scope);
    if (servers.find((s) => s.name === opts.name) && !opts.force) { console.log(chalk.yellow(\`  ⚠  Server "\${opts.name}" already exists. Use --force to overwrite.\`)); return; }
    const env: Record<string,string> = {};
    if (opts.env) { for (const kv of opts.env.split(",")) { const [k,v] = kv.split("="); if (k) env[k] = v ?? ""; } }
    const server: MCPServerDef = { name: opts.name, command: opts.command, scope: opts.scope, ...(Object.keys(env).length ? { env } : {}), ...(opts.timeout ? { timeout: parseInt(opts.timeout) } : {}) };
    const updated = servers.filter((s) => s.name !== opts.name); updated.push(server); saveMCP(opts.scope, updated);
    console.log(chalk.green(\`  ✅ MCP server "\${opts.name}" added\`));
  });

  cmd.command("remove").description("Remove an MCP server").requiredOption("--name <name>", "Server name").option("--scope <scope>", "workspace|global", "workspace").action((opts) => {
    const servers = loadMCP(opts.scope).filter((s) => s.name !== opts.name);
    saveMCP(opts.scope, servers); console.log(chalk.green(\`  ✅ Removed "\${opts.name}"\`));
  });

  cmd.command("list [scope]").description("List MCP servers").action((scope = "workspace") => {
    const servers = loadMCP(scope as "workspace"|"global");
    if (servers.length === 0) { console.log(chalk.dim(\`  No MCP servers in \${scope} scope.\`)); return; }
    console.log(chalk.bold(\`\\n  🔌 MCP Servers [\${scope}]\\n\`));
    for (const s of servers) console.log(\`  \${chalk.cyan("●")} \${chalk.bold(s.name.padEnd(20))} \${chalk.dim(s.command)}\`);
    console.log();
  });

  cmd.command("import").description("Import MCP config from file").requiredOption("--file <path>", "Config file").option("--force", "Overwrite").argument("[scope]", "workspace|global", "workspace").action((scope, opts) => {
    try {
      const data = JSON.parse(fs.readFileSync(opts.file, "utf8")) as { servers?: MCPServerDef[] };
      const existing = opts.force ? [] : loadMCP(scope as "workspace"|"global");
      const merged = [...existing, ...(data.servers ?? []).filter((s) => !existing.find((e) => e.name === s.name))];
      saveMCP(scope as "workspace"|"global", merged);
      console.log(chalk.green(\`  ✅ Imported \${(data.servers ?? []).length} servers\`));
    } catch (err) { console.log(chalk.red(\`  ✗ \${err instanceof Error ? err.message : err}\`)); }
  });

  cmd.command("status").description("Get MCP server status").requiredOption("--name <name>", "Server name").action((opts) => {
    const ws = loadMCP("workspace"); const gl = loadMCP("global");
    const server = [...ws, ...gl].find((s) => s.name === opts.name);
    if (!server) { console.log(chalk.yellow(\`  ⚠  Server "\${opts.name}" not found\`)); return; }
    console.log(chalk.bold(\`\\n  MCP Server: \${opts.name}\\n\`));
    console.log(\`  Command: \${chalk.cyan(server.command)}\`);
    console.log(\`  Scope:   \${server.scope}\`);
    if (server.env) console.log(\`  Env:     \${JSON.stringify(server.env)}\`);
    console.log();
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════════════════
// 5. AGENT MANAGEMENT COMMAND
// ═══════════════════════════════════════════════════════════════

write("commands/agent.ts", `import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import os from "os";
import { openEditor } from "../ui/editor.js";

interface AgentConfig { name: string; description?: string; system?: string; model?: string; tools?: string[]; }

function getAgentsDir(): string {
  return path.join(process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"), "agents");
}

function getAgentPath(name: string): string { return path.join(getAgentsDir(), \`\${name}.json\`); }

function loadAgent(name: string): AgentConfig | null {
  try { const f = getAgentPath(name); if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as AgentConfig; } catch {} return null;
}

function saveAgent(agent: AgentConfig): void {
  const dir = getAgentsDir(); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(getAgentPath(agent.name), JSON.stringify(agent, null, 2));
}

export function agentCommand(): Command {
  const cmd = new Command("agent").description("Manage agent configurations");

  cmd.command("list").description("List available agents").action(() => {
    const dir = getAgentsDir();
    const builtin = ["default","planner","coder","tester","fixer","reviewer","guide"];
    console.log(chalk.bold("\\n  🤖 Built-in Agents\\n"));
    builtin.forEach((a) => console.log(\`  \${chalk.cyan("●")} \${a}\`));
    if (fs.existsSync(dir)) {
      const custom = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => f.replace(".json",""));
      if (custom.length) { console.log(chalk.bold("\\n  Custom Agents\\n")); custom.forEach((a) => console.log(\`  \${chalk.green("●")} \${a}\`)); }
    }
    console.log();
  });

  cmd.command("create <name>").description("Create a new agent config").action(async (name: string) => {
    const template = JSON.stringify({ name, description: \`\${name} agent\`, system: "You are a helpful assistant.", model: "claude-3-5-haiku-20241022", tools: ["read","write","shell"] }, null, 2);
    const content = await openEditor(template);
    if (content) { try { const agent = JSON.parse(content) as AgentConfig; saveAgent(agent); console.log(chalk.green(\`\\n  ✅ Agent "\${name}" created\\n\`)); } catch { console.log(chalk.red("  ✗ Invalid JSON")); } }
    else console.log(chalk.dim("  Cancelled."));
  });

  cmd.command("edit [name]").description("Edit an agent config").action(async (name?: string) => {
    const agentName = name ?? "default";
    const existing = loadAgent(agentName) ?? { name: agentName };
    const content = await openEditor(JSON.stringify(existing, null, 2));
    if (content) { try { saveAgent(JSON.parse(content) as AgentConfig); console.log(chalk.green(\`\\n  ✅ Agent "\${agentName}" updated\\n\`)); } catch { console.log(chalk.red("  ✗ Invalid JSON")); } }
  });

  cmd.command("validate <path>").description("Validate agent config file").action((agentPath: string) => {
    try {
      const content = JSON.parse(fs.readFileSync(agentPath, "utf8")) as AgentConfig;
      const required = ["name"]; const missing = required.filter((k) => !(k in content));
      if (missing.length) { console.log(chalk.red(\`  ✗ Missing fields: \${missing.join(", ")}\`)); return; }
      console.log(chalk.green(\`  ✅ Valid agent config: "\${content.name}"\`));
    } catch (err) { console.log(chalk.red(\`  ✗ \${err instanceof Error ? err.message : err}\`)); }
  });

  cmd.command("set-default <name>").description("Set default agent").action((name: string) => {
    const { loadConfig, saveConfig } = require("../config/config.js") as { loadConfig: () => Record<string,unknown>; saveConfig: (c: Record<string,unknown>) => void };
    const config = loadConfig(); config["defaultAgent"] = name; saveConfig(config);
    console.log(chalk.green(\`  ✅ Default agent set to "\${name}"\`));
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════════════════
// 6. HEADLESS MODE + CHAT FLAGS
// ═══════════════════════════════════════════════════════════════

write("commands/headless.ts", `import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";

export interface HeadlessOptions {
  input: string;
  trustAllTools?: boolean;
  agent?: string;
  effort?: string;
  format?: string;
}

export async function runHeadless(opts: HeadlessOptions): Promise<void> {
  const creds = loadCredentials();
  const config = loadConfig();
  const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);
  let output = "";
  for await (const chunk of model.complete({
    model: config.model ?? "claude-3-5-haiku-20241022",
    system: "You are BharatBuild CLI, an AI coding assistant. Be concise and direct.",
    messages: [{ role: "user", content: opts.input }],
    tools: [],
    maxTokens: 4096,
  })) {
    if (chunk.type === "text_delta" && chunk.text) {
      output += chunk.text;
      if (opts.format !== "json") process.stdout.write(chunk.text);
    }
  }
  if (opts.format === "json") console.log(JSON.stringify({ output, model: config.model }));
  else process.stdout.write("\\n");
}
`);

// Update chat command with all missing flags
const chatPath = path.join(s, "commands", "chat.ts");
let chatContent = fs.readFileSync(chatPath, "utf8");
if (!chatContent.includes("resume")) {
  chatContent = chatContent.replace(
    /\.description\("Start interactive chat session"\)/,
    `.description("Start interactive chat session")
    .argument("[input]", "First question to ask (non-interactive)")
    .option("--no-interactive", "Print response to stdout without interactive mode")
    .option("-r, --resume", "Resume the previous conversation")
    .option("--resume-id <id>", "Resume a specific session by ID")
    .option("--resume-picker", "Open interactive session picker")
    .option("--list-sessions", "List all saved sessions for this directory")
    .option("--list-models", "Display available models")
    .option("--delete-session <id>", "Delete a saved session by ID")
    .option("--trust-all-tools", "Allow all tools without confirmation")
    .option("--trust-tools <tools>", "Trust specific tools (comma-separated)")
    .option("--effort <level>", "Reasoning effort: low|medium|high|xhigh|max")
    .option("--agent <name>", "Specify which agent to use")
    .option("--wrap <mode>", "Line wrap: always|never|auto")`
  );
  fs.writeFileSync(chatPath, chatContent);
  console.log("  updated: commands/chat.ts");
}

// ═══════════════════════════════════════════════════════════════
// 7. WIRE NEW COMMANDS INTO CLI.TS
// ═══════════════════════════════════════════════════════════════

const cliPath = path.join(s, "cli.ts");
let cliContent = fs.readFileSync(cliPath, "utf8");

const newImports = [
  `import { translateCommand } from "./commands/translate.js";`,
  `import { doctorCommand } from "./commands/doctor.js";`,
  `import { updateCommand } from "./commands/update.js";`,
  `import { whoamiCommand } from "./commands/whoami.js";`,
  `import { settingsCommand } from "./commands/settings.js";`,
  `import { diagnosticCommand } from "./commands/diagnostic.js";`,
  `import { issueCommand } from "./commands/issue.js";`,
  `import { versionCommand } from "./commands/version.js";`,
  `import { mcpCommand } from "./commands/mcp.js";`,
  `import { agentCommand } from "./commands/agent.js";`,
].filter((imp) => !cliContent.includes(imp.split(" ")[2]));

const newRegistrations = [
  `program.addCommand(translateCommand());`,
  `program.addCommand(doctorCommand());`,
  `program.addCommand(updateCommand());`,
  `program.addCommand(whoamiCommand());`,
  `program.addCommand(settingsCommand());`,
  `program.addCommand(diagnosticCommand());`,
  `program.addCommand(issueCommand());`,
  `program.addCommand(versionCommand());`,
  `program.addCommand(mcpCommand());`,
  `program.addCommand(agentCommand());`,
].filter((reg) => !cliContent.includes(reg));

if (newImports.length > 0) {
  cliContent = cliContent.replace(
    /import \{ hooksCommand \}/,
    newImports.join("\n") + "\nimport { hooksCommand }"
  );
}
if (newRegistrations.length > 0) {
  cliContent = cliContent.replace(
    /program\.addCommand\(hooksCommand\(\)\);/,
    `program.addCommand(hooksCommand());\n  ${newRegistrations.join("\n  ")}`
  );
}
fs.writeFileSync(cliPath, cliContent);
console.log("  updated: cli.ts");

console.log("\n✅ All remaining gap files created! Running build...");
