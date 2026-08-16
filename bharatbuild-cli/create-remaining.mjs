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

// ── tools/git extras ──────────────────────────────────────────
write("tools/git/branch.ts", `import { executeCommand } from "../shell/index.js";
export async function createBranch(name: string, cwd?: string) {
  return { success: !(await executeCommand({ command: \`git checkout -b \${name}\`, working_dir: cwd })).isError };
}
export async function listBranches(cwd?: string): Promise<string[]> {
  const r = await executeCommand({ command: "git branch --format=%(refname:short)", working_dir: cwd });
  return r.isError ? [] : r.content.split("\\n").filter(Boolean);
}
export async function switchBranch(name: string, cwd?: string) {
  return { success: !(await executeCommand({ command: \`git checkout \${name}\`, working_dir: cwd })).isError };
}
`);

// ── tools/filesystem extras ───────────────────────────────────
write("tools/filesystem/delete-file.ts", `import fs from "fs";
import path from "path";
export async function deleteFile(input: { path: string; recursive?: boolean }): Promise<{ content: string; isError: boolean }> {
  const p = path.resolve(input.path);
  try {
    const stat = fs.statSync(p);
    if (stat.isDirectory()) {
      if (!input.recursive) return { content: \`"\${input.path}" is a directory. Use recursive:true.\`, isError: true };
      fs.rmSync(p, { recursive: true, force: true });
      return { content: \`Deleted directory: \${input.path}\`, isError: false };
    }
    fs.unlinkSync(p);
    return { content: \`Deleted: \${input.path}\`, isError: false };
  } catch (err) {
    return { content: \`Error: \${err instanceof Error ? err.message : err}\`, isError: true };
  }
}
`);

write("tools/filesystem/apply-patch.ts", `import fs from "fs";
import path from "path";
export async function applyPatch(input: { file_path: string; old_string: string; new_string: string }): Promise<{ content: string; isError: boolean }> {
  const p = path.resolve(input.file_path);
  try {
    if (!fs.existsSync(p)) return { content: \`File not found: \${input.file_path}\`, isError: true };
    const c = fs.readFileSync(p, "utf8");
    if (!c.includes(input.old_string)) return { content: \`String not found in \${input.file_path}\`, isError: true };
    fs.writeFileSync(p, c.replace(input.old_string, input.new_string), "utf8");
    return { content: \`Patched \${input.file_path}\`, isError: false };
  } catch (err) {
    return { content: \`Error: \${err instanceof Error ? err.message : err}\`, isError: true };
  }
}
`);

// ── project/ ──────────────────────────────────────────────────
write("project/project-config.ts", `import fs from "fs";
import path from "path";
export interface ProjectConfig { name: string; description?: string; mode: string; model: string; apiUrl: string; createdAt: string; }
export function loadProjectConfig(dir?: string): ProjectConfig | null {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild.json");
  try { if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as ProjectConfig; } catch {}
  return null;
}
export function saveProjectConfig(config: ProjectConfig, dir?: string) {
  fs.writeFileSync(path.join(dir ?? process.cwd(), ".bharatbuild.json"), JSON.stringify(config, null, 2));
}
`);

write("project/project-rules.ts", `import fs from "fs";
import path from "path";
export function loadProjectRules(dir?: string): string {
  const files = [".bharatbuild/rules.md", "CLAUDE.md", ".cursorrules"];
  for (const f of files) {
    const full = path.join(dir ?? process.cwd(), f);
    try { if (fs.existsSync(full)) return fs.readFileSync(full, "utf8"); } catch {}
  }
  return "";
}
`);

write("project/project-state.ts", `import fs from "fs";
import path from "path";
export interface ProjectState { lastTask?: string; lastModel?: string; sessionId?: string; updatedAt: string; }
export function loadState(dir?: string): ProjectState | null {
  try {
    const f = path.join(dir ?? process.cwd(), ".bharatbuild/state.json");
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as ProjectState;
  } catch {}
  return null;
}
export function saveState(state: Partial<ProjectState>, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild/state.json");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const existing = loadState(dir) ?? { updatedAt: "" };
  fs.writeFileSync(f, JSON.stringify({ ...existing, ...state, updatedAt: new Date().toISOString() }, null, 2));
}
`);

write("project/init-project.ts", `export { initCommand } from "../commands/init.js";
`);

// ── tasks/ ────────────────────────────────────────────────────
write("tasks/task-state.ts", `export type TaskStatus = "pending" | "in_progress" | "done" | "failed";
export interface TaskState { id: string; title: string; status: TaskStatus; createdAt: string; updatedAt: string; error?: string; }
const tasks = new Map<string, TaskState>();
export function createTask(title: string): TaskState {
  const t: TaskState = { id: \`task-\${Date.now()}\`, title, status: "pending", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
  tasks.set(t.id, t); return t;
}
export function updateTask(id: string, u: Partial<TaskState>) {
  const t = tasks.get(id); if (t) tasks.set(id, { ...t, ...u, updatedAt: new Date().toISOString() });
}
export function getTask(id: string) { return tasks.get(id); }
export function listTasks(): TaskState[] { return Array.from(tasks.values()); }
`);

write("tasks/task-loader.ts", `import fs from "fs";
import path from "path";
export interface TaskDefinition { id: string; title: string; description: string; acceptanceCriteria?: string[]; }
export function loadTaskFile(filePath: string): TaskDefinition | null {
  try {
    const c = fs.readFileSync(filePath, "utf8");
    return {
      id: path.basename(filePath, path.extname(filePath)),
      title: c.match(/^#\\s+(.+)$/m)?.[1]?.trim() ?? path.basename(filePath),
      description: c,
      acceptanceCriteria: c.match(/^##\\s+Acceptance/m) ? c.split("\\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2)) : undefined,
    };
  } catch { return null; }
}
export function loadTasksDir(dir: string): TaskDefinition[] {
  const td = path.join(dir, ".bharatbuild", "tasks");
  if (!fs.existsSync(td)) return [];
  return fs.readdirSync(td).filter((f) => f.endsWith(".md")).map((f) => loadTaskFile(path.join(td, f))).filter(Boolean) as TaskDefinition[];
}
`);

write("tasks/story-loader.ts", `import fs from "fs";
import path from "path";
export interface Story { id: string; title: string; description: string; }
export function loadStory(filePath: string): Story | null {
  try {
    const c = fs.readFileSync(filePath, "utf8");
    return { id: path.basename(filePath, ".md"), title: c.split("\\n")[0]?.replace(/^#\\s*/, "") ?? "Untitled", description: c };
  } catch { return null; }
}
`);

write("tasks/acceptance-criteria.ts", `export interface Criterion { description: string; met: boolean; }
export function parseCriteria(markdown: string): Criterion[] {
  return markdown.split("\\n").filter((l) => l.trim().startsWith("- ")).map((l) => ({ description: l.replace(/^-\\s*/, "").trim(), met: false }));
}
export function checkCriteria(criteria: Criterion[], testOutput: string): Criterion[] {
  return criteria.map((c) => ({ ...c, met: testOutput.toLowerCase().includes(c.description.toLowerCase().split(" ").slice(0, 3).join(" ")) }));
}
`);

// ── ui/ extras ────────────────────────────────────────────────
write("ui/terminal.ts", `import chalk from "chalk";
import readline from "readline";
export function printSuccess(msg: string) { console.log(chalk.green(\`\\n✅ \${msg}\\n\`)); }
export function printError(msg: string) { console.log(chalk.red(\`\\n❌ \${msg}\\n\`)); }
export function printWarning(msg: string) { console.log(chalk.yellow(\`\\n⚠  \${msg}\\n\`)); }
export function printInfo(msg: string) { console.log(chalk.cyan(\`\\n💡 \${msg}\\n\`)); }
export function printDivider(label?: string) {
  const w = process.stdout.columns ?? 80;
  if (label) { const p = Math.max(0, (w - label.length - 2) / 2); console.log(chalk.dim("─".repeat(p) + " " + label + " " + "─".repeat(p))); }
  else console.log(chalk.dim("─".repeat(w)));
}
export async function confirm(q: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((r) => rl.question(chalk.cyan(\`\${q} [y/N]: \`), (a) => { rl.close(); r(a.trim().toLowerCase() === "y"); }));
}
`);

write("ui/progress.ts", `import chalk from "chalk";
export class ProgressBar {
  private cur = 0;
  constructor(private total: number, private label = "") {}
  update(n: number, label?: string) {
    this.cur = n; if (label) this.label = label;
    const pct = Math.round((n / this.total) * 100);
    const f = Math.round((n / this.total) * 30);
    process.stdout.write(\`\\r  \${chalk.green("█".repeat(f))}\${chalk.dim("░".repeat(30 - f))} \${pct}% \${chalk.dim(this.label)}   \`);
    if (n >= this.total) process.stdout.write("\\n");
  }
  done(msg?: string) { this.update(this.total, msg ?? "done"); }
}
`);

write("ui/diff-view.ts", `import chalk from "chalk";
export function renderDiff(diff: string) {
  for (const l of diff.split("\\n")) {
    if (l.startsWith("+++") || l.startsWith("---")) console.log(chalk.bold(l));
    else if (l.startsWith("@@")) console.log(chalk.cyan(l));
    else if (l.startsWith("+")) console.log(chalk.green(l));
    else if (l.startsWith("-")) console.log(chalk.red(l));
    else console.log(chalk.dim(l));
  }
}
`);

write("ui/chat-view.ts", `import chalk from "chalk";
export function renderUserMessage(msg: string) { console.log(chalk.bold.cyan("\\n  You: ") + msg); }
export function renderAssistantChunk(chunk: string) { process.stdout.write(chunk); }
export function renderAssistantDone() { console.log("\\n"); }
export function renderToolCall(toolName: string, input: Record<string, unknown>) {
  const p = JSON.stringify(input).slice(0, 80);
  console.log(chalk.dim(\`\\n  🔧 \${chalk.yellow(toolName)}(\${p}\${p.length >= 80 ? "…" : ""})\`));
}
export function renderToolResult(toolName: string, isError: boolean, durationMs: number) {
  if (isError) console.log(chalk.red(\`  ✗ \${toolName} (\${durationMs}ms)\`));
  else console.log(chalk.dim(\`  ✓ \${toolName} (\${durationMs}ms)\`));
}
`);

write("ui/build-view.ts", `import chalk from "chalk";
export function renderBuildStart(cmd: string) { console.log(chalk.bold(\`\\n🔨 Running: \${chalk.cyan(cmd)}\\n\`)); }
export function renderBuildResult(passed: boolean, errors: string[]) {
  if (passed) console.log(chalk.bold.green("\\n✅ Build passed!\\n"));
  else {
    console.log(chalk.bold.red(\`\\n❌ Build failed — \${errors.length} error(s)\\n\`));
    errors.slice(0, 5).forEach((e) => console.log(chalk.red(\`  • \${e}\`)));
    console.log();
  }
}
`);

write("ui/test-view.ts", `import chalk from "chalk";
export function renderTestResult(passed: number, failed: number, total: number, duration: number) {
  console.log(\`\\n  \${failed === 0 ? chalk.bold.green("✅ All tests passed") : chalk.bold.red(\`❌ \${failed} test(s) failed\`)}\`);
  console.log(\`  \${chalk.green(passed + " passed")}, \${failed > 0 ? chalk.red(failed + " failed") : chalk.dim("0 failed")}, \${total} total, \${duration.toFixed(2)}s\\n\`);
}
`);

write("ui/approval-view.ts", `import chalk from "chalk";
export function renderApprovalRequest(toolName: string, input: Record<string, unknown>, riskLevel: "low" | "medium" | "high") {
  const c = riskLevel === "high" ? chalk.red : riskLevel === "medium" ? chalk.yellow : chalk.green;
  console.log(c(\`\\n⚠  Permission Required [\${riskLevel.toUpperCase()} RISK]\`));
  console.log(chalk.bold(\`   Tool: \${toolName}\`));
  console.log(chalk.dim(\`   Input: \${JSON.stringify(input).slice(0, 200)}\`));
}
`);

// ── api/ extras ───────────────────────────────────────────────
write("api/types.ts", `export interface ProjectDTO { id: string; name: string; description?: string; status: string; tech_stack?: string; created_at: string; }
export interface UserDTO { id: string; email: string; name: string; full_name?: string; tier: string; subscription_plan?: string; token_balance?: number; tokens_remaining?: number; }
export interface APIKeyDTO { id: string; name: string; key_prefix: string; created_at: string; last_used?: string; is_active: boolean; }
`);

write("api/auth-client.ts", `import { BharatBuildClient } from "./client.js";
import type { UserDTO } from "./types.js";
export class AuthClient {
  constructor(private c: BharatBuildClient) {}
  async me() { return this.c.get<UserDTO>("/api/v1/auth/me"); }
  async login(email: string, password: string) { return this.c.post<{ access_token: string; user?: UserDTO }>("/api/v1/auth/login", { email, password }); }
  async register(name: string, email: string, password: string) { return this.c.post<{ access_token: string; user?: UserDTO }>("/api/v1/auth/register", { full_name: name, email, password }); }
}
`);

write("api/project-client.ts", `import { BharatBuildClient } from "./client.js";
import type { ProjectDTO } from "./types.js";
export class ProjectClient {
  constructor(private c: BharatBuildClient) {}
  async list(limit = 20) {
    const d = await this.c.get<{ projects?: ProjectDTO[]; items?: ProjectDTO[] }>(\`/api/v1/projects?limit=\${limit}\`);
    return (d.projects ?? d.items ?? (Array.isArray(d) ? d : [])) as ProjectDTO[];
  }
  async get(id: string) { return this.c.get<ProjectDTO>(\`/api/v1/projects/\${id}\`); }
  async create(p: { name: string; description?: string; tech_stack?: string }) { return this.c.post<ProjectDTO>("/api/v1/projects", p); }
  async delete(id: string) { await this.c.delete(\`/api/v1/projects/\${id}\`); }
}
`);

write("api/task-client.ts", `import { BharatBuildClient } from "./client.js";
export interface TaskDTO { id: string; title: string; status: string; description?: string; project_id?: string; }
export class TaskClient {
  constructor(private c: BharatBuildClient) {}
  async list(pid?: string) {
    const url = pid ? \`/api/v1/tasks?project_id=\${pid}\` : "/api/v1/tasks";
    const d = await this.c.get<{ items?: TaskDTO[]; tasks?: TaskDTO[] }>(url);
    return (d.items ?? d.tasks ?? (Array.isArray(d) ? d : [])) as TaskDTO[];
  }
  async get(id: string) { return this.c.get<TaskDTO>(\`/api/v1/tasks/\${id}\`); }
  async create(t: Partial<TaskDTO>) { return this.c.post<TaskDTO>("/api/v1/tasks", t); }
  async update(id: string, u: Partial<TaskDTO>) { return this.c.put<TaskDTO>(\`/api/v1/tasks/\${id}\`, u); }
}
`);

write("api/websocket-client.ts", `import { EventStream } from "../runtime/event-stream.js";
export class WebSocketClient {
  private ws: WebSocket | null = null;
  readonly events = new EventStream();
  connect(url: string, token?: string) {
    const wsUrl = token ? \`\${url}?token=\${token}\` : url;
    this.ws = new (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket(wsUrl);
    this.ws.onmessage = (e: MessageEvent) => {
      try {
        const d = JSON.parse(typeof e.data === "string" ? e.data : "") as Record<string, unknown>;
        if (d["type"]) void this.events.emit(d as Parameters<typeof this.events.emit>[0]);
      } catch {}
    };
  }
  disconnect() { this.ws?.close(); this.ws = null; }
  send(d: unknown) { this.ws?.send(JSON.stringify(d)); }
}
`);

// ── tests/ stubs ──────────────────────────────────────────────
write("../tests/runtime/agent-loop.test.ts", `import { describe, it, expect } from "vitest";
describe("agent-loop", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/runtime/agent-loop.js");
    expect(mod).toBeDefined();
  });
});
`);

write("../tests/tools/filesystem.test.ts", `import { describe, it, expect } from "vitest";
describe("filesystem tools", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/tools/filesystem/index.js");
    expect(mod).toBeDefined();
  });
});
`);

write("../tests/agents/agent-registry.test.ts", `import { describe, it, expect } from "vitest";
describe("agent-registry", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/agents/agent-registry.js");
    expect(mod).toBeDefined();
  });
});
`);

write("../tests/models/model-router.test.ts", `import { describe, it, expect } from "vitest";
describe("model-router", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/models/model-router.js");
    expect(mod).toBeDefined();
  });
});
`);

write("../tests/quality/quality-gate.test.ts", `import { describe, it, expect } from "vitest";
describe("quality-gate", () => {
  it("should be importable", async () => {
    const mod = await import("../../src/quality/quality-gate.js");
    expect(mod).toBeDefined();
  });
});
`);

write("../tests/integration/cli.test.ts", `import { describe, it, expect } from "vitest";
import { execSync } from "child_process";
describe("CLI integration", () => {
  it("should print version", () => {
    const out = execSync("node dist/cli.js --version 2>&1").toString();
    expect(out).toMatch(/\\d+\\.\\d+\\.\\d+/);
  });
});
`);

// ── scripts/ ─────────────────────────────────────────────────
write("../scripts/build.ts", `import { execSync } from "child_process";
console.log("🔨 Building bharatbuild-cli...");
execSync("npx tsc --build", { stdio: "inherit" });
console.log("✅ Build complete!");
`);

write("../scripts/package.ts", `import { execSync } from "child_process";
import fs from "fs";
console.log("📦 Packaging bharatbuild-cli...");
execSync("npm pack", { stdio: "inherit" });
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8")) as { name: string; version: string };
console.log(\`✅ Packaged: \${pkg.name}-\${pkg.version}.tgz\`);
`);

write("../scripts/release.ts", `import { execSync } from "child_process";
import fs from "fs";
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8")) as { version: string };
console.log(\`🚀 Releasing v\${pkg.version}...\`);
execSync("npm publish --access public", { stdio: "inherit" });
console.log("✅ Released!");
`);

console.log("\n✅ All remaining files created successfully!");
