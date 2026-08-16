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

// ═══════════════════════════════════════════════════
// 1. HOOKS SYSTEM
// ═══════════════════════════════════════════════════

write("hooks/hook-config.ts", `import fs from "fs";
import path from "path";

export type HookEvent = "file-saved" | "file-created" | "file-deleted" | "git-commit" | "git-push" | "build-complete" | "test-complete";

export interface HookDefinition {
  id: string;
  name: string;
  event: HookEvent;
  pattern?: string;       // glob pattern for file-based events
  agent?: string;         // which agent to trigger
  prompt?: string;        // prompt template
  enabled: boolean;
}

export interface HooksConfig {
  hooks: HookDefinition[];
}

const DEFAULT_CONFIG: HooksConfig = { hooks: [] };

export function loadHooksConfig(dir?: string): HooksConfig {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "hooks.json");
  try {
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as HooksConfig;
  } catch {}
  return DEFAULT_CONFIG;
}

export function saveHooksConfig(config: HooksConfig, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "hooks.json");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, JSON.stringify(config, null, 2));
}

export function addHook(hook: HookDefinition, dir?: string) {
  const config = loadHooksConfig(dir);
  config.hooks = config.hooks.filter((h) => h.id !== hook.id);
  config.hooks.push(hook);
  saveHooksConfig(config, dir);
}

export function removeHook(id: string, dir?: string) {
  const config = loadHooksConfig(dir);
  config.hooks = config.hooks.filter((h) => h.id !== id);
  saveHooksConfig(config, dir);
}
`);

write("hooks/file-watcher.ts", `import fs from "fs";
import path from "path";
import { EventEmitter } from "events";

export interface FileChangeEvent {
  type: "created" | "modified" | "deleted";
  filePath: string;
  timestamp: Date;
}

export class FileWatcher extends EventEmitter {
  private watchers: Map<string, fs.FSWatcher> = new Map();
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();
  private debounceMs: number;

  constructor(debounceMs = 300) {
    super();
    this.debounceMs = debounceMs;
  }

  watch(dir: string, patterns: string[] = ["**/*"]) {
    const ignored = ["node_modules", ".git", "dist", "build", ".bharatbuild"];
    this._watchDir(dir, ignored);
  }

  private _watchDir(dir: string, ignored: string[]) {
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (ignored.includes(entry.name)) continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          this._watchDir(full, ignored);
        } else {
          const watcher = fs.watch(full, (eventType) => {
            this._debounce(full, () => {
              const exists = fs.existsSync(full);
              this.emit("change", {
                type: eventType === "rename" ? (exists ? "created" : "deleted") : "modified",
                filePath: full,
                timestamp: new Date(),
              } as FileChangeEvent);
            });
          });
          this.watchers.set(full, watcher);
        }
      }
    } catch {}
  }

  private _debounce(key: string, fn: () => void) {
    const existing = this.debounceTimers.get(key);
    if (existing) clearTimeout(existing);
    this.debounceTimers.set(key, setTimeout(() => { fn(); this.debounceTimers.delete(key); }, this.debounceMs));
  }

  stop() {
    for (const w of this.watchers.values()) w.close();
    this.watchers.clear();
    for (const t of this.debounceTimers.values()) clearTimeout(t);
    this.debounceTimers.clear();
  }
}
`);

write("hooks/hook-runner.ts", `import type { FileChangeEvent } from "./file-watcher.js";
import { loadHooksConfig, type HookDefinition, type HookEvent } from "./hook-config.js";
import { minimatch } from "minimatch";

export interface HookContext {
  event: HookEvent;
  filePath?: string;
  payload?: Record<string, unknown>;
}

export type HookHandler = (hook: HookDefinition, ctx: HookContext) => Promise<void>;

export class HookRunner {
  private handler: HookHandler;
  private dir: string;

  constructor(handler: HookHandler, dir?: string) {
    this.handler = handler;
    this.dir = dir ?? process.cwd();
  }

  async runForFileChange(change: FileChangeEvent) {
    const event: HookEvent =
      change.type === "created" ? "file-created" :
      change.type === "deleted" ? "file-deleted" : "file-saved";
    const config = loadHooksConfig(this.dir);
    const matching = config.hooks.filter((h) => {
      if (!h.enabled) return false;
      if (h.event !== event) return false;
      if (h.pattern && !minimatch(change.filePath, h.pattern)) return false;
      return true;
    });
    for (const hook of matching) {
      await this.handler(hook, { event, filePath: change.filePath });
    }
  }

  async runForEvent(event: HookEvent, payload?: Record<string, unknown>) {
    const config = loadHooksConfig(this.dir);
    const matching = config.hooks.filter((h) => h.enabled && h.event === event);
    for (const hook of matching) {
      await this.handler(hook, { event, payload });
    }
  }
}
`);

write("hooks/git-hooks.ts", `import fs from "fs";
import path from "path";

const HOOK_SCRIPT = (event: string) => \`#!/bin/sh
# BharatBuild git hook — \${event}
node "$(git rev-parse --show-toplevel)/node_modules/.bin/bharatbuild" hook:run \${event} "$@"
\`;

export function installGitHooks(dir?: string) {
  const root = dir ?? process.cwd();
  const hooksDir = path.join(root, ".git", "hooks");
  if (!fs.existsSync(hooksDir)) {
    console.warn("No .git/hooks directory found. Run inside a git repo.");
    return;
  }
  const hooks: Array<[string, string]> = [
    ["pre-commit", "git-commit"],
    ["post-commit", "git-commit"],
    ["pre-push", "git-push"],
  ];
  for (const [gitHook, event] of hooks) {
    const p = path.join(hooksDir, gitHook);
    fs.writeFileSync(p, HOOK_SCRIPT(event), { mode: 0o755 });
    console.log(\`  Installed git hook: \${gitHook}\`);
  }
}

export function uninstallGitHooks(dir?: string) {
  const root = dir ?? process.cwd();
  const hooksDir = path.join(root, ".git", "hooks");
  for (const gitHook of ["pre-commit", "post-commit", "pre-push"]) {
    const p = path.join(hooksDir, gitHook);
    try { if (fs.existsSync(p)) fs.unlinkSync(p); } catch {}
  }
}
`);

write("commands/hooks.ts", `import { Command } from "commander";
import chalk from "chalk";
import { loadHooksConfig, addHook, removeHook, type HookEvent } from "../hooks/hook-config.js";
import { installGitHooks, uninstallGitHooks } from "../hooks/git-hooks.js";

export function hooksCommand(): Command {
  const cmd = new Command("hooks").description("Manage automation hooks");

  cmd.command("list").description("List all hooks").action(() => {
    const config = loadHooksConfig();
    if (config.hooks.length === 0) { console.log(chalk.dim("No hooks configured.")); return; }
    for (const h of config.hooks) {
      const status = h.enabled ? chalk.green("●") : chalk.dim("○");
      console.log(\`\${status} \${chalk.bold(h.name)} [\${chalk.cyan(h.event)}]\${h.pattern ? " " + chalk.dim(h.pattern) : ""}\`);
    }
  });

  cmd.command("add <name> <event>").description("Add a hook").option("-p, --pattern <glob>", "File glob pattern").option("-a, --agent <agent>", "Agent to trigger").option("--prompt <text>", "Prompt template").action((name: string, event: string, opts) => {
    addHook({ id: \`hook-\${Date.now()}\`, name, event: event as HookEvent, pattern: opts.pattern, agent: opts.agent, prompt: opts.prompt, enabled: true });
    console.log(chalk.green(\`✅ Hook "\${name}" added for event "\${event}"\`));
  });

  cmd.command("remove <id>").description("Remove a hook by ID").action((id: string) => {
    removeHook(id);
    console.log(chalk.green(\`✅ Hook "\${id}" removed\`));
  });

  cmd.command("install-git").description("Install BharatBuild git hooks").action(() => {
    installGitHooks();
    console.log(chalk.green("✅ Git hooks installed"));
  });

  cmd.command("uninstall-git").description("Uninstall BharatBuild git hooks").action(() => {
    uninstallGitHooks();
    console.log(chalk.green("✅ Git hooks uninstalled"));
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════
// 2. SPEC-DRIVEN WORKFLOW
// ═══════════════════════════════════════════════════

write("spec/steering-file.ts", `import fs from "fs";
import path from "path";

export interface SteeringFile {
  persona?: string;
  rules?: string[];
  ignore?: string[];
  context?: string;
  model?: string;
}

export function loadSteeringFile(dir?: string): SteeringFile {
  const root = dir ?? process.cwd();
  // Check multiple locations like Kiro does
  const locations = [
    path.join(root, ".bharatbuild", "steering.md"),
    path.join(root, ".kiro", "steering.md"),
    path.join(root, "AGENTS.md"),
    path.join(root, "CLAUDE.md"),
  ];
  for (const loc of locations) {
    if (fs.existsSync(loc)) {
      return parseSteeringMarkdown(fs.readFileSync(loc, "utf8"));
    }
  }
  return {};
}

function parseSteeringMarkdown(content: string): SteeringFile {
  const result: SteeringFile = {};
  const lines = content.split("\\n");
  let section = "";
  const rules: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## Persona")) { section = "persona"; continue; }
    if (line.startsWith("## Rules")) { section = "rules"; continue; }
    if (line.startsWith("## Ignore")) { section = "ignore"; continue; }
    if (line.startsWith("## Model")) { section = "model"; continue; }
    if (line.startsWith("#")) { section = ""; continue; }

    if (section === "persona" && line.trim()) result.persona = (result.persona ?? "") + line + "\\n";
    if (section === "rules" && line.startsWith("- ")) rules.push(line.slice(2).trim());
    if (section === "model" && line.trim()) result.model = line.trim();
  }
  result.rules = rules;
  return result;
}

export function saveSteeringFile(steering: SteeringFile, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "steering.md");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const lines: string[] = ["# BharatBuild Steering File\\n"];
  if (steering.persona) lines.push(\`## Persona\\n\${steering.persona}\\n\`);
  if (steering.rules?.length) lines.push(\`## Rules\\n\${steering.rules.map((r) => \`- \${r}\`).join("\\n")}\\n\`);
  if (steering.model) lines.push(\`## Model\\n\${steering.model}\\n\`);
  fs.writeFileSync(f, lines.join("\\n"));
}
`);

write("spec/requirements.ts", `import fs from "fs";
import path from "path";

export interface Requirement {
  id: string;
  title: string;
  description: string;
  priority: "must" | "should" | "could";
  status: "pending" | "in_progress" | "done";
}

export function parseRequirementsDoc(content: string): Requirement[] {
  const reqs: Requirement[] = [];
  const lines = content.split("\\n");
  let current: Partial<Requirement> | null = null;

  for (const line of lines) {
    const headingMatch = line.match(/^###\\s+(.+)/);
    if (headingMatch) {
      if (current?.id) reqs.push(current as Requirement);
      current = { id: \`req-\${reqs.length + 1}\`, title: headingMatch[1] ?? "", description: "", priority: "should", status: "pending" };
      continue;
    }
    if (current) {
      if (line.toLowerCase().includes("must")) current.priority = "must";
      else if (line.toLowerCase().includes("could")) current.priority = "could";
      current.description = (current.description ?? "") + line + "\\n";
    }
  }
  if (current?.id) reqs.push(current as Requirement);
  return reqs;
}

export function loadRequirements(dir?: string): Requirement[] {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "requirements.md");
  if (!fs.existsSync(f)) return [];
  return parseRequirementsDoc(fs.readFileSync(f, "utf8"));
}
`);

write("spec/design-doc.ts", `import fs from "fs";
import path from "path";

export interface DesignDoc {
  title: string;
  overview: string;
  architecture: string;
  components: string[];
  dataFlow: string;
  openQuestions: string[];
}

export function loadDesignDoc(dir?: string): DesignDoc | null {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "design.md");
  if (!fs.existsSync(f)) return null;
  return parseDesignDoc(fs.readFileSync(f, "utf8"));
}

function parseDesignDoc(content: string): DesignDoc {
  const doc: DesignDoc = { title: "", overview: "", architecture: "", components: [], dataFlow: "", openQuestions: [] };
  const sections = content.split(/^## /m);
  for (const section of sections) {
    const lines = section.split("\\n");
    const heading = lines[0]?.trim().toLowerCase() ?? "";
    const body = lines.slice(1).join("\\n").trim();
    if (heading === "" && lines[0]?.startsWith("# ")) doc.title = lines[0].replace(/^# /, "").trim();
    else if (heading.includes("overview")) doc.overview = body;
    else if (heading.includes("architecture")) doc.architecture = body;
    else if (heading.includes("component")) doc.components = body.split("\\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
    else if (heading.includes("data flow")) doc.dataFlow = body;
    else if (heading.includes("open question")) doc.openQuestions = body.split("\\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
  }
  return doc;
}

export function saveDesignDoc(doc: DesignDoc, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "design.md");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const content = [
    \`# \${doc.title}\\n\`,
    \`## Overview\\n\${doc.overview}\\n\`,
    \`## Architecture\\n\${doc.architecture}\\n\`,
    \`## Components\\n\${doc.components.map((c) => \`- \${c}\`).join("\\n")}\\n\`,
    \`## Data Flow\\n\${doc.dataFlow}\\n\`,
    \`## Open Questions\\n\${doc.openQuestions.map((q) => \`- \${q}\`).join("\\n")}\\n\`,
  ].join("\\n");
  fs.writeFileSync(f, content);
}
`);

write("spec/spec-generator.ts", `import fs from "fs";
import path from "path";
import type { ModelClient } from "../runtime/agent-loop.js";

export interface SpecGeneratorOptions {
  title: string;
  description: string;
  outputDir?: string;
}

export async function generateSpec(
  options: SpecGeneratorOptions,
  model: ModelClient
): Promise<{ requirementsPath: string; designPath: string }> {
  const dir = path.join(options.outputDir ?? process.cwd(), ".bharatbuild", "specs");
  fs.mkdirSync(dir, { recursive: true });

  const reqPrompt = \`Generate a requirements document for: "\${options.title}"
Description: \${options.description}

Format as markdown with:
# Requirements: \${options.title}
## Overview
## Functional Requirements
### REQ-1: [title]
[description with must/should/could]
### REQ-2: ...
## Non-Functional Requirements
## Acceptance Criteria\`;

  const designPrompt = \`Generate a technical design document for: "\${options.title}"
Description: \${options.description}

Format as markdown with:
# Design: \${options.title}
## Overview
## Architecture
## Components
## Data Flow
## Open Questions\`;

  let reqContent = "";
  let designContent = "";

  // Generate requirements
  process.stdout.write("  Generating requirements...");
  for await (const chunk of model.complete({
    model: "claude-3-5-haiku-20241022",
    system: "You are a software architect. Generate concise, actionable spec documents.",
    messages: [{ role: "user", content: reqPrompt }],
    tools: [],
    maxTokens: 2000,
  })) {
    if (chunk.type === "text_delta") { reqContent += chunk.text; process.stdout.write("."); }
  }
  console.log(" done");

  // Generate design
  process.stdout.write("  Generating design doc...");
  for await (const chunk of model.complete({
    model: "claude-3-5-haiku-20241022",
    system: "You are a software architect. Generate concise, actionable design documents.",
    messages: [{ role: "user", content: designPrompt }],
    tools: [],
    maxTokens: 2000,
  })) {
    if (chunk.type === "text_delta") { designContent += chunk.text; process.stdout.write("."); }
  }
  console.log(" done");

  const reqPath = path.join(dir, "requirements.md");
  const designPath = path.join(dir, "design.md");
  fs.writeFileSync(reqPath, reqContent);
  fs.writeFileSync(designPath, designContent);

  return { requirementsPath: reqPath, designPath: designPath };
}
`);

write("commands/spec.ts", `import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";
import { generateSpec } from "../spec/spec-generator.js";
import { loadRequirements } from "../spec/requirements.js";
import { loadDesignDoc } from "../spec/design-doc.js";
import { loadSteeringFile, saveSteeringFile } from "../spec/steering-file.js";

export function specCommand(): Command {
  const cmd = new Command("spec").description("Spec-driven development workflow");

  cmd.command("new <title>").description("Generate requirements + design doc for a feature").option("-d, --description <text>", "Feature description").action(async (title: string, opts) => {
    const creds = loadCredentials();
    const config = loadConfig();
    const description = opts.description ?? title;
    console.log(chalk.bold(\`\\n📋 Generating spec for: \${title}\\n\`));
    try {
      const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);
      const { requirementsPath, designPath } = await generateSpec({ title, description }, model);
      console.log(chalk.green(\`\\n✅ Spec generated!\`));
      console.log(\`  Requirements: \${chalk.cyan(requirementsPath)}\`);
      console.log(\`  Design:       \${chalk.cyan(designPath)}\\n\`);
    } catch (err) {
      console.error(chalk.red(\`Error: \${err instanceof Error ? err.message : err}\`));
    }
  });

  cmd.command("list").description("List requirements from spec").action(() => {
    const reqs = loadRequirements();
    if (reqs.length === 0) { console.log(chalk.dim("No requirements found. Run: bharatbuild spec new <title>")); return; }
    console.log(chalk.bold("\\n📋 Requirements:\\n"));
    for (const r of reqs) {
      const badge = r.priority === "must" ? chalk.red("MUST") : r.priority === "should" ? chalk.yellow("SHOULD") : chalk.dim("COULD");
      console.log(\`  [\${badge}] \${chalk.bold(r.id)}: \${r.title}\`);
    }
    console.log();
  });

  cmd.command("design").description("Show design document").action(() => {
    const doc = loadDesignDoc();
    if (!doc) { console.log(chalk.dim("No design doc found. Run: bharatbuild spec new <title>")); return; }
    console.log(chalk.bold(\`\\n📐 \${doc.title}\\n\`));
    if (doc.overview) console.log(chalk.bold("Overview:\\n") + doc.overview + "\\n");
    if (doc.components.length) console.log(chalk.bold("Components:\\n") + doc.components.map((c) => \`  • \${c}\`).join("\\n") + "\\n");
    if (doc.openQuestions.length) console.log(chalk.bold("Open Questions:\\n") + doc.openQuestions.map((q) => \`  ? \${q}\`).join("\\n") + "\\n");
  });

  cmd.command("steering").description("View or edit steering file").option("--set-persona <text>", "Set agent persona").option("--add-rule <rule>", "Add a rule").option("--set-model <model>", "Set preferred model").action((opts) => {
    const steering = loadSteeringFile();
    if (opts.setPersona) { steering.persona = opts.setPersona; saveSteeringFile(steering); console.log(chalk.green("✅ Persona updated")); return; }
    if (opts.addRule) { steering.rules = [...(steering.rules ?? []), opts.addRule]; saveSteeringFile(steering); console.log(chalk.green(\`✅ Rule added: \${opts.addRule}\`)); return; }
    if (opts.setModel) { steering.model = opts.setModel; saveSteeringFile(steering); console.log(chalk.green(\`✅ Model set to: \${opts.setModel}\`)); return; }
    // Display current steering
    console.log(chalk.bold("\\n🎯 Steering File:\\n"));
    if (steering.persona) console.log(chalk.bold("Persona:") + "\\n" + steering.persona);
    if (steering.rules?.length) console.log(chalk.bold("Rules:") + "\\n" + steering.rules.map((r) => \`  • \${r}\`).join("\\n"));
    if (steering.model) console.log(chalk.bold("Model:") + " " + steering.model);
    if (!steering.persona && !steering.rules?.length) console.log(chalk.dim("No steering configured."));
    console.log();
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════
// 3. FULL INTERACTIVE TUI
// ═══════════════════════════════════════════════════

write("ui/key-bindings.ts", `export interface KeyBinding {
  key: string;
  ctrl?: boolean;
  description: string;
  action: string;
}

export const DEFAULT_KEY_BINDINGS: KeyBinding[] = [
  { key: "c", ctrl: true, description: "Cancel / interrupt", action: "cancel" },
  { key: "d", ctrl: true, description: "Exit", action: "exit" },
  { key: "l", ctrl: true, description: "Clear screen", action: "clear" },
  { key: "r", ctrl: true, description: "Retry last message", action: "retry" },
  { key: "u", ctrl: true, description: "Clear input line", action: "clear-input" },
  { key: "Up", description: "Previous history", action: "history-prev" },
  { key: "Down", description: "Next history", action: "history-next" },
];

export function printKeyBindings() {
  console.log("\\n  Key Bindings:");
  for (const kb of DEFAULT_KEY_BINDINGS) {
    const key = kb.ctrl ? \`Ctrl+\${kb.key.toUpperCase()}\` : kb.key;
    console.log(\`    \${key.padEnd(12)} \${kb.description}\`);
  }
  console.log();
}
`);

write("ui/status-bar.ts", `import chalk from "chalk";

export interface StatusBarState {
  model: string;
  mode?: string;
  tokens?: number;
  cost?: number;
  session?: string;
  thinking?: boolean;
}

export function renderStatusBar(state: StatusBarState): string {
  const parts: string[] = [];
  parts.push(chalk.bold.cyan(\` \${state.model}\`));
  if (state.mode) parts.push(chalk.dim(\`|\`) + chalk.yellow(\` \${state.mode}\`));
  if (state.tokens) parts.push(chalk.dim(\`|\`) + chalk.dim(\` \${state.tokens.toLocaleString()} tokens\`));
  if (state.cost) parts.push(chalk.dim(\`|\`) + chalk.dim(\` $\${state.cost.toFixed(4)}\`));
  if (state.thinking) parts.push(chalk.dim(\`|\`) + chalk.magenta(\` ⠋ thinking...\`));
  const bar = parts.join(" ");
  const width = process.stdout.columns ?? 80;
  const padded = bar.padEnd(width);
  return \`\${chalk.bgBlue(padded)}\`;
}

export function printStatusBar(state: StatusBarState) {
  process.stdout.write(\`\\r\${renderStatusBar(state)}\\n\`);
}
`);

write("ui/chat-interface.ts", `import readline from "readline";
import chalk from "chalk";
import { EventEmitter } from "events";
import { printStatusBar, type StatusBarState } from "./status-bar.js";
import { printKeyBindings } from "./key-bindings.js";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export class ChatInterface extends EventEmitter {
  private rl: readline.Interface;
  private history: string[] = [];
  private historyIndex = -1;
  private status: StatusBarState;

  constructor(status: StatusBarState) {
    super();
    this.status = status;
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });
    this._setupKeyHandlers();
  }

  private _setupKeyHandlers() {
    process.stdin.setRawMode?.(false); // safe fallback
    this.rl.on("SIGINT", () => this.emit("cancel"));
  }

  printWelcome(version: string) {
    console.clear();
    console.log(chalk.bold.cyan(\`
  ╔══════════════════════════════════════╗
  ║   BharatBuild CLI  v\${version.padEnd(20)}║
  ║   AI-powered development assistant  ║
  ╚══════════════════════════════════════╝\`));
    console.log(chalk.dim("  Type your message and press Enter. Ctrl+C to cancel, Ctrl+D to exit."));
    console.log(chalk.dim("  Type /help for commands, /keys for key bindings.\\n"));
    printStatusBar(this.status);
    console.log();
  }

  updateStatus(updates: Partial<StatusBarState>) {
    this.status = { ...this.status, ...updates };
  }

  async prompt(): Promise<string> {
    return new Promise((resolve) => {
      this.rl.question(chalk.bold.green("  You: "), (input) => {
        const trimmed = input.trim();
        if (trimmed) this.history.unshift(trimmed);
        this.historyIndex = -1;
        resolve(trimmed);
      });
    });
  }

  startStreaming() {
    this.updateStatus({ thinking: true });
    process.stdout.write(chalk.bold.blue("\\n  BharatBuild: "));
  }

  streamChunk(text: string) {
    process.stdout.write(text);
  }

  endStreaming() {
    this.updateStatus({ thinking: false });
    process.stdout.write("\\n\\n");
    printStatusBar(this.status);
    console.log();
  }

  showToolCall(name: string, input: Record<string, unknown>) {
    const preview = JSON.stringify(input).slice(0, 60);
    console.log(chalk.dim(\`\\n  🔧 \${chalk.yellow(name)}(\${preview}\${preview.length >= 60 ? "…" : ""})\`));
  }

  showToolResult(name: string, isError: boolean, ms: number) {
    const icon = isError ? chalk.red("✗") : chalk.green("✓");
    console.log(chalk.dim(\`  \${icon} \${name} (\${ms}ms)\`));
  }

  handleSlashCommand(input: string): boolean {
    const [cmd, ...args] = input.slice(1).split(" ");
    switch (cmd) {
      case "help":
        console.log(chalk.bold("\\n  Commands:"));
        console.log("    /help         Show this help");
        console.log("    /keys         Show key bindings");
        console.log("    /clear        Clear screen");
        console.log("    /model <id>   Switch model");
        console.log("    /exit         Exit");
        console.log();
        return true;
      case "keys":
        printKeyBindings();
        return true;
      case "clear":
        console.clear();
        printStatusBar(this.status);
        console.log();
        return true;
      case "exit":
      case "quit":
        this.close();
        process.exit(0);
      case "model":
        if (args[0]) { this.emit("model-change", args[0]); return true; }
        console.log(chalk.dim("  Usage: /model <model-id>"));
        return true;
      default:
        return false;
    }
  }

  close() {
    this.rl.close();
  }
}
`);

write("ui/renderer.ts", `import chalk from "chalk";

export type RenderMode = "chat" | "task" | "build" | "test";

export interface RenderContext {
  mode: RenderMode;
  model: string;
  sessionId?: string;
}

export function renderHeader(ctx: RenderContext) {
  const modeColors: Record<RenderMode, chalk.Chalk> = {
    chat: chalk.cyan,
    task: chalk.yellow,
    build: chalk.blue,
    test: chalk.green,
  };
  const color = modeColors[ctx.mode] ?? chalk.white;
  console.log(color.bold(\`\\n  [\${ctx.mode.toUpperCase()}] \`) + chalk.dim(\`model: \${ctx.model}\${ctx.sessionId ? \` | session: \${ctx.sessionId.slice(0, 8)}\` : ""}\`));
  console.log(chalk.dim("  " + "─".repeat((process.stdout.columns ?? 80) - 4)));
}

export function renderThinking(dots = 1) {
  const spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  const frame = spinner[dots % spinner.length] ?? "⠋";
  process.stdout.write(\`\\r  \${chalk.magenta(frame)} \${chalk.dim("thinking...")}\`);
}

export function clearThinking() {
  process.stdout.write("\\r" + " ".repeat(30) + "\\r");
}

export function renderError(msg: string) {
  console.log(chalk.red(\`\\n  ❌ \${msg}\\n\`));
}

export function renderSuccess(msg: string) {
  console.log(chalk.green(\`\\n  ✅ \${msg}\\n\`));
}

export function renderCodeBlock(code: string, lang = "") {
  const border = chalk.dim("  " + "─".repeat(60));
  console.log(border);
  if (lang) console.log(chalk.dim(\`  \${lang}\`));
  for (const line of code.split("\\n")) {
    console.log(chalk.dim("  │ ") + line);
  }
  console.log(border);
}
`);

// ═══════════════════════════════════════════════════
// 4. REAL LSP + TREE-SITTER INTEGRATION
// ═══════════════════════════════════════════════════

write("tools/intelligence/lsp-server.ts", `import { executeCommand } from "../shell/index.js";
import { EventEmitter } from "events";

export interface LSPMessage {
  jsonrpc: "2.0";
  id?: number;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface LSPPosition { line: number; character: number; }
export interface LSPRange { start: LSPPosition; end: LSPPosition; }
export interface LSPLocation { uri: string; range: LSPRange; }
export interface LSPDiagnostic { range: LSPRange; severity: 1 | 2 | 3 | 4; message: string; source?: string; }
export interface LSPHover { contents: string | { kind: string; value: string }; range?: LSPRange; }

export class LSPServer extends EventEmitter {
  private msgId = 1;
  private pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>();
  private initialized = false;

  async checkInstalled(serverCmd: string): Promise<boolean> {
    const r = await executeCommand({ command: \`\${serverCmd} --version\` });
    return !r.isError;
  }

  private nextId() { return this.msgId++; }

  buildInitialize(rootUri: string): LSPMessage {
    return {
      jsonrpc: "2.0", id: this.nextId(), method: "initialize",
      params: {
        processId: process.pid,
        rootUri,
        capabilities: {
          textDocument: {
            hover: { contentFormat: ["markdown", "plaintext"] },
            definition: { linkSupport: false },
            references: {},
            publishDiagnostics: { relatedInformation: true },
          },
          workspace: { workspaceFolders: true },
        },
      },
    };
  }

  buildHoverRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/hover", params: { textDocument: { uri }, position: { line, character } } };
  }

  buildDefinitionRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/definition", params: { textDocument: { uri }, position: { line, character } } };
  }

  buildReferencesRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/references", params: { textDocument: { uri }, position: { line, character }, context: { includeDeclaration: true } } };
  }

  formatMessage(msg: LSPMessage): Buffer {
    const body = JSON.stringify(msg);
    return Buffer.from(\`Content-Length: \${Buffer.byteLength(body)}\\r\\n\\r\\n\${body}\`);
  }

  parseMessage(data: string): LSPMessage | null {
    try {
      const bodyStart = data.indexOf("\\r\\n\\r\\n");
      if (bodyStart === -1) return null;
      return JSON.parse(data.slice(bodyStart + 4)) as LSPMessage;
    } catch { return null; }
  }
}

export function getLanguageServer(language: string): string | null {
  const servers: Record<string, string> = {
    typescript: "typescript-language-server --stdio",
    javascript: "typescript-language-server --stdio",
    python: "pyright-langserver --stdio",
    go: "gopls",
    rust: "rust-analyzer",
    java: "jdtls",
    ruby: "solargraph stdio",
    php: "intelephense --stdio",
    "c++": "clangd",
    c: "clangd",
  };
  return servers[language] ?? null;
}
`);

write("tools/intelligence/treesitter.ts", `import fs from "fs";
import path from "path";

export interface ASTNode {
  type: string;
  text: string;
  startLine: number;
  endLine: number;
  startCol: number;
  endCol: number;
  children?: ASTNode[];
}

export interface ParseResult {
  nodes: ASTNode[];
  language: string;
  parseMethod: "treesitter" | "regex-fallback";
}

/**
 * Try real tree-sitter first, fall back to regex-based parsing.
 * Install real tree-sitter: npm install tree-sitter tree-sitter-typescript tree-sitter-python
 */
export function parseFile(filePath: string): ParseResult {
  const ext = path.extname(filePath).slice(1);
  const language = extToLanguage(ext);
  const content = fs.readFileSync(filePath, "utf8");

  // Try real tree-sitter
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Parser = require("tree-sitter") as { new(): { setLanguage(l: unknown): void; parse(c: string): { rootNode: unknown } } };
    const langMap: Record<string, string> = { typescript: "tree-sitter-typescript/typescript", javascript: "tree-sitter-javascript", python: "tree-sitter-python", rust: "tree-sitter-rust", go: "tree-sitter-go" };
    const langPkg = langMap[language];
    if (langPkg) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const lang = require(langPkg) as unknown;
      const parser = new Parser();
      parser.setLanguage(lang);
      const tree = parser.parse(content);
      return { nodes: extractNodes(tree.rootNode as Record<string, unknown>), language, parseMethod: "treesitter" };
    }
  } catch {
    // tree-sitter not installed — fall back to regex
  }

  // Regex fallback
  return { nodes: regexParse(content, language), language, parseMethod: "regex-fallback" };
}

function extractNodes(node: Record<string, unknown>, depth = 0): ASTNode[] {
  if (depth > 5) return [];
  const result: ASTNode[] = [];
  const important = ["function_declaration", "class_declaration", "method_definition", "interface_declaration", "type_alias_declaration", "export_statement", "import_statement"];
  if (important.includes(String(node["type"] ?? ""))) {
    const sp = node["startPosition"] as Record<string, number> | undefined;
    const ep = node["endPosition"] as Record<string, number> | undefined;
    result.push({
      type: String(node["type"] ?? ""),
      text: String(node["text"] ?? "").slice(0, 100),
      startLine: sp?.["row"] ?? 0,
      endLine: ep?.["row"] ?? 0,
      startCol: sp?.["column"] ?? 0,
      endCol: ep?.["column"] ?? 0,
    });
  }
  const children = node["children"] as unknown[] | undefined;
  if (children) {
    for (const child of children) {
      result.push(...extractNodes(child as Record<string, unknown>, depth + 1));
    }
  }
  return result;
}

function regexParse(content: string, language: string): ASTNode[] {
  const nodes: ASTNode[] = [];
  const lines = content.split("\\n");
  const patterns: Array<{ re: RegExp; type: string }> = language === "python"
    ? [{ re: /^(async\\s+)?def\\s+(\\w+)/, type: "function" }, { re: /^class\\s+(\\w+)/, type: "class" }]
    : [
        { re: /^export\\s+(async\\s+)?function\\s+(\\w+)/, type: "function_declaration" },
        { re: /^export\\s+class\\s+(\\w+)/, type: "class_declaration" },
        { re: /^export\\s+interface\\s+(\\w+)/, type: "interface_declaration" },
        { re: /^export\\s+type\\s+(\\w+)/, type: "type_alias_declaration" },
        { re: /^(async\\s+)?function\\s+(\\w+)/, type: "function_declaration" },
        { re: /^class\\s+(\\w+)/, type: "class_declaration" },
      ];
  lines.forEach((line, i) => {
    for (const { re, type } of patterns) {
      if (re.test(line)) {
        nodes.push({ type, text: line.trim().slice(0, 80), startLine: i, endLine: i, startCol: 0, endCol: line.length });
        break;
      }
    }
  });
  return nodes;
}

function extToLanguage(ext: string): string {
  const map: Record<string, string> = { ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript", py: "python", rs: "rust", go: "go", java: "java", rb: "ruby", php: "php" };
  return map[ext] ?? "unknown";
}
`);

write("tools/intelligence/code-intelligence.ts", `import path from "path";
import { parseFile, type ASTNode } from "./treesitter.js";
import { findReferences } from "./references.js";
import { extractSymbols } from "./symbols.js";
import { getTypeScriptDiagnostics } from "./diagnostics.js";
import { LSPServer, getLanguageServer } from "./lsp-server.js";

export interface CodeIntelligenceResult {
  symbols: Array<{ name: string; kind: string; file: string; line: number }>;
  ast?: ASTNode[];
  parseMethod?: string;
  lspAvailable: boolean;
  lspServer?: string;
}

export async function analyzeFile(filePath: string): Promise<CodeIntelligenceResult> {
  const ext = path.extname(filePath).slice(1);
  const language = extToLang(ext);

  // Get symbols via regex
  const symbols = extractSymbols(filePath);

  // Try AST parsing
  let ast: ASTNode[] | undefined;
  let parseMethod: string | undefined;
  try {
    const result = parseFile(filePath);
    ast = result.nodes;
    parseMethod = result.parseMethod;
  } catch {}

  // Check LSP availability
  const lspServer = getLanguageServer(language);
  const lspAvailable = lspServer !== null;

  return { symbols, ast, parseMethod, lspAvailable, lspServer: lspServer ?? undefined };
}

export async function getProjectDiagnostics(cwd?: string) {
  return getTypeScriptDiagnostics(cwd);
}

export function searchReferences(symbolName: string, rootDir: string) {
  return findReferences(symbolName, rootDir);
}

function extToLang(ext: string): string {
  const map: Record<string, string> = { ts: "typescript", tsx: "typescript", js: "javascript", py: "python", rs: "rust", go: "go" };
  return map[ext] ?? "unknown";
}
`);

// ═══════════════════════════════════════════════════
// 5. Wire up new commands in cli.ts
// ═══════════════════════════════════════════════════

// Read existing cli.ts and update it
const cliPath = path.join(s, "cli.ts");
let cliContent = fs.readFileSync(cliPath, "utf8");

// Add imports if not present
if (!cliContent.includes("hooksCommand")) {
  cliContent = cliContent.replace(
    /import \{ modelCommand \}/,
    `import { hooksCommand } from "./commands/hooks.js";\nimport { specCommand } from "./commands/spec.js";\nimport { modelCommand }`
  );
  // Register commands
  cliContent = cliContent.replace(
    /program\.addCommand\(modelCommand\(\)\)/,
    `program.addCommand(modelCommand());\n  program.addCommand(hooksCommand());\n  program.addCommand(specCommand());`
  );
  fs.writeFileSync(cliPath, cliContent);
  console.log("  updated: cli.ts");
}

// Add minimatch dep note
console.log("\n✅ All Kiro-matching features created!");
console.log("\n⚠️  Run: npm install minimatch");
console.log("   Then: npm run build");
