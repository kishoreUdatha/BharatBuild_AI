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

// ═══════════════════════════════════════════════════════════
// 1. VOICE MODE
// ═══════════════════════════════════════════════════════════

write("voice/voice-input.ts", `import { spawn, type ChildProcess } from "child_process";
import { EventEmitter } from "events";

export interface VoiceInputOptions {
  language?: string;
  silenceThresholdMs?: number;
}

export class VoiceInput extends EventEmitter {
  private proc: ChildProcess | null = null;
  private recording = false;

  /** Check if a speech-to-text engine is available */
  static async isAvailable(): Promise<boolean> {
    const { execSync } = await import("child_process");
    // Check for whisper, whisper.cpp, vosk, or sox
    const tools = ["whisper", "whisper-cli", "sox", "arecord"];
    for (const tool of tools) {
      try { execSync(\`\${tool} --version 2>/dev/null || \${tool} -h 2>/dev/null\`, { stdio: "pipe" }); return true; } catch {}
    }
    return false;
  }

  /** Start recording audio and transcribing */
  startRecording(opts: VoiceInputOptions = {}): void {
    if (this.recording) return;
    this.recording = true;
    this.emit("start");

    // Use sox to record audio on Linux/Mac, or PowerShell on Windows
    const platform = process.platform;
    if (platform === "win32") {
      this._recordWindows(opts);
    } else if (platform === "darwin") {
      this._recordMac(opts);
    } else {
      this._recordLinux(opts);
    }
  }

  private _recordWindows(opts: VoiceInputOptions) {
    // PowerShell speech recognition
    const script = \`
Add-Type -AssemblyName System.Speech;
$r = New-Object System.Speech.Recognition.SpeechRecognitionEngine;
$r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));
$r.SetInputToDefaultAudioDevice();
$result = $r.Recognize([TimeSpan]::FromSeconds(10));
if ($result) { Write-Output $result.Text } else { Write-Output "" }
\`;
    this.proc = spawn("powershell", ["-Command", script], { stdio: ["ignore", "pipe", "ignore"] });
    let output = "";
    this.proc.stdout?.on("data", (d) => { output += d.toString(); });
    this.proc.on("close", () => {
      this.recording = false;
      const text = output.trim();
      if (text) this.emit("transcription", text);
      this.emit("stop");
    });
  }

  private _recordMac(opts: VoiceInputOptions) {
    // macOS: use sox to record then whisper to transcribe
    const tmpFile = \`/tmp/bharatbuild-voice-\${Date.now()}.wav\`;
    this.proc = spawn("sox", ["-d", "-r", "16000", "-c", "1", tmpFile, "silence", "1", "0.1", "3%", "1", \`\${(opts.silenceThresholdMs ?? 2000) / 1000}\`, "3%"], { stdio: "ignore" });
    this.proc.on("close", async () => {
      this.recording = false;
      const text = await this._transcribe(tmpFile);
      try { fs.unlinkSync(tmpFile); } catch {}
      if (text) this.emit("transcription", text);
      this.emit("stop");
    });
  }

  private _recordLinux(opts: VoiceInputOptions) {
    const tmpFile = \`/tmp/bharatbuild-voice-\${Date.now()}.wav\`;
    this.proc = spawn("arecord", ["-f", "cd", "-t", "wav", "-d", "10", tmpFile], { stdio: "ignore" });
    this.proc.on("close", async () => {
      this.recording = false;
      const text = await this._transcribe(tmpFile);
      try { fs.unlinkSync(tmpFile); } catch {}
      if (text) this.emit("transcription", text);
      this.emit("stop");
    });
  }

  private async _transcribe(audioFile: string): Promise<string | null> {
    const { execSync } = await import("child_process");
    // Try whisper CLI
    try {
      const out = execSync(\`whisper "\${audioFile}" --model tiny --output_format txt --output_dir /tmp 2>/dev/null\`, { encoding: "utf8" });
      const txtFile = audioFile.replace(".wav", ".txt");
      if (fs.existsSync(txtFile)) {
        const text = fs.readFileSync(txtFile, "utf8").trim();
        try { fs.unlinkSync(txtFile); } catch {}
        return text;
      }
      return out.trim() || null;
    } catch {}
    return null;
  }

  stopRecording(): void {
    if (!this.recording) return;
    this.proc?.kill("SIGTERM");
    this.proc = null;
    this.recording = false;
    this.emit("stop");
  }

  isRecording(): boolean { return this.recording; }
}
`);

write("voice/voice-output.ts", `import { spawn } from "child_process";

export interface TTSOptions {
  voice?: string;
  rate?: number;
  pitch?: number;
}

export async function speak(text: string, opts: TTSOptions = {}): Promise<void> {
  const platform = process.platform;
  return new Promise((resolve) => {
    let child;
    if (platform === "win32") {
      // Windows SAPI
      const script = \`Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; \${opts.voice ? \`$s.SelectVoice('\${opts.voice}');\` : ""} $s.Speak('\${text.replace(/'/g, "\\'")}');\`;
      child = spawn("powershell", ["-Command", script], { stdio: "ignore" });
    } else if (platform === "darwin") {
      // macOS say
      const args = [text];
      if (opts.voice) args.push("-v", opts.voice);
      if (opts.rate) args.push("-r", String(opts.rate));
      child = spawn("say", args, { stdio: "ignore" });
    } else {
      // Linux espeak / festival
      try {
        child = spawn("espeak", [text, ...(opts.rate ? ["-s", String(opts.rate)] : [])], { stdio: "ignore" });
      } catch {
        child = spawn("festival", ["--tts"], { stdio: ["pipe", "ignore", "ignore"] });
        (child.stdin as NodeJS.WritableStream).write(text);
        (child.stdin as NodeJS.WritableStream).end();
      }
    }
    child.on("close", resolve);
    child.on("error", resolve);
  });
}

export async function isTTSAvailable(): Promise<boolean> {
  const { execSync } = await import("child_process");
  const tools = process.platform === "win32" ? ["powershell"] : process.platform === "darwin" ? ["say"] : ["espeak", "festival"];
  for (const t of tools) {
    try { execSync(\`\${t} --version 2>/dev/null || echo ok\`, { stdio: "pipe" }); return true; } catch {}
  }
  return false;
}
`);

write("voice/voice-mode.ts", `import chalk from "chalk";
import { VoiceInput } from "./voice-input.js";
import { speak, isTTSAvailable } from "./voice-output.js";
import { getTheme } from "../ui/theme.js";

export interface VoiceModeOptions {
  tts?: boolean;
  language?: string;
  onTranscription: (text: string) => Promise<string>;
}

export class VoiceMode {
  private input = new VoiceInput();
  private opts: VoiceModeOptions;
  private active = false;

  constructor(opts: VoiceModeOptions) {
    this.opts = opts;
  }

  async start(): Promise<void> {
    const t = getTheme();
    const available = await VoiceInput.isAvailable();
    if (!available) {
      console.log(t.warning("\n  ⚠  Voice input requires: whisper (pip install openai-whisper) + sox/arecord\n"));
      console.log(t.dim("  Install: pip install openai-whisper && brew install sox\n"));
      return;
    }

    this.active = true;
    console.log(t.success("\n  🎙  Voice mode active. Press Ctrl+O to record, Ctrl+C to exit.\n"));

    this.input.on("start", () => {
      process.stdout.write(chalk.magenta("\r  🔴 Recording... (speak now)   "));
    });

    this.input.on("transcription", async (text: string) => {
      console.log(chalk.bold.green("\n\n  You (voice): ") + text);
      try {
        const response = await this.opts.onTranscription(text);
        if (this.opts.tts) {
          const ttsOk = await isTTSAvailable();
          if (ttsOk) await speak(response);
        }
      } catch (err) {
        console.log(chalk.red(`\n  ✗ ${err instanceof Error ? err.message : err}\n`));
      }
    });

    this.input.on("stop", () => {
      if (this.active) {
        process.stdout.write(chalk.dim("\r  🎙  Ready. Press Ctrl+O to record.   \n"));
      }
    });
  }

  triggerRecording(): void {
    if (this.input.isRecording()) {
      this.input.stopRecording();
    } else {
      this.input.startRecording({ language: this.opts.language });
    }
  }

  stop(): void {
    this.active = false;
    this.input.stopRecording();
    console.log(chalk.dim("\n  Voice mode stopped.\n"));
  }
}
`);

write("commands/voice.ts", `import { Command } from "commander";
import chalk from "chalk";
import { VoiceMode } from "../voice/voice-mode.js";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";
import { getTheme } from "../ui/theme.js";

export function voiceCommand(): Command {
  return new Command("voice")
    .description("Start voice mode — speak to BharatBuild CLI")
    .option("--tts", "Enable text-to-speech responses")
    .option("--language <lang>", "Speech language (default: en)", "en")
    .action(async (opts) => {
      const t = getTheme();
      const creds = loadCredentials();
      const config = loadConfig();
      const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);

      console.log(t.heading("\n  🎙  BharatBuild Voice Mode\n"));

      const voice = new VoiceMode({
        tts: opts.tts,
        language: opts.language,
        onTranscription: async (text: string) => {
          let response = "";
          process.stdout.write(t.assistant("  BharatBuild: "));
          for await (const chunk of model.complete({
            model: config.model ?? "claude-3-5-haiku-20241022",
            system: "You are BharatBuild CLI, an AI coding assistant. Give concise spoken responses.",
            messages: [{ role: "user", content: text }],
            tools: [],
            maxTokens: 500,
          })) {
            if (chunk.type === "text_delta" && chunk.text) {
              response += chunk.text;
              process.stdout.write(chunk.text);
            }
          }
          process.stdout.write("\n\n");
          return response;
        },
      });

      await voice.start();

      // Handle Ctrl+O to toggle recording
      process.stdin.setRawMode?.(true);
      process.stdin.resume();
      process.stdin.on("data", (key: Buffer) => {
        const k = key.toString();
        if (k === "\x0f") voice.triggerRecording(); // Ctrl+O
        if (k === "\x03") { voice.stop(); process.exit(0); } // Ctrl+C
      });

      // Keep alive
      await new Promise<void>((resolve) => {
        process.on("SIGINT", () => { voice.stop(); resolve(); });
      });
    });
}
`);

// ═══════════════════════════════════════════════════════════
// 2. ACP — AGENT COMMUNICATION PROTOCOL
// ═══════════════════════════════════════════════════════════

write("acp/acp-types.ts", `export interface ACPMessage {
  jsonrpc: "2.0";
  id?: string | number;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

export interface ACPTask {
  id: string;
  title: string;
  description: string;
  agent?: string;
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
}

export interface ACPCapabilities {
  streaming: boolean;
  tools: string[];
  agents: string[];
  models: string[];
}

export interface ACPSession {
  id: string;
  createdAt: string;
  capabilities: ACPCapabilities;
}
`);

write("acp/acp-server.ts", `import http from "http";
import { EventEmitter } from "events";
import type { ACPMessage, ACPTask, ACPCapabilities } from "./acp-types.js";

export interface ACPServerOptions {
  port?: number;
  host?: string;
  onTask: (task: ACPTask) => Promise<string>;
}

export class ACPServer extends EventEmitter {
  private server: http.Server;
  private opts: ACPServerOptions;
  private sessions = new Map<string, { createdAt: string }>();

  constructor(opts: ACPServerOptions) {
    super();
    this.opts = opts;
    this.server = http.createServer((req, res) => this._handleRequest(req, res));
  }

  private async _handleRequest(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

    if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }

    let body = "";
    req.on("data", (chunk) => { body += chunk.toString(); });
    req.on("end", async () => {
      try {
        const msg = JSON.parse(body) as ACPMessage;
        const result = await this._dispatch(msg);
        res.writeHead(200);
        res.end(JSON.stringify({ jsonrpc: "2.0", id: msg.id, result }));
      } catch (err) {
        res.writeHead(400);
        res.end(JSON.stringify({ jsonrpc: "2.0", error: { code: -32700, message: err instanceof Error ? err.message : "Parse error" } }));
      }
    });
  }

  private async _dispatch(msg: ACPMessage): Promise<unknown> {
    switch (msg.method) {
      case "initialize": {
        const sessionId = \`session-\${Date.now()}\`;
        this.sessions.set(sessionId, { createdAt: new Date().toISOString() });
        return {
          sessionId,
          capabilities: {
            streaming: true,
            tools: ["read", "write", "shell", "glob", "grep"],
            agents: ["default", "planner", "coder", "tester", "fixer", "reviewer"],
            models: ["claude-3-5-haiku-20241022", "gpt-4o", "gemini-1.5-pro"],
          } as ACPCapabilities,
        };
      }
      case "tasks/create": {
        const params = msg.params as Partial<ACPTask>;
        const task: ACPTask = {
          id: \`task-\${Date.now()}\`,
          title: params.title ?? "Unnamed task",
          description: params.description ?? "",
          agent: params.agent ?? "default",
          status: "pending",
        };
        task.status = "running";
        try {
          task.result = await this.opts.onTask(task);
          task.status = "complete";
        } catch (err) {
          task.status = "failed";
          task.result = err instanceof Error ? err.message : String(err);
        }
        return task;
      }
      case "capabilities": {
        return {
          streaming: true,
          tools: ["read", "write", "shell", "glob", "grep"],
          agents: ["default", "planner", "coder", "tester", "fixer", "reviewer"],
          models: ["claude-3-5-haiku-20241022", "gpt-4o", "gemini-1.5-pro"],
        };
      }
      default:
        throw new Error(\`Unknown method: \${msg.method ?? "undefined"}\`);
    }
  }

  listen(port?: number, host?: string): Promise<void> {
    const p = port ?? this.opts.port ?? 3141;
    const h = host ?? this.opts.host ?? "127.0.0.1";
    return new Promise((resolve) => {
      this.server.listen(p, h, () => {
        console.log(\`  ACP server listening on http://\${h}:\${p}\`);
        this.emit("listening", { port: p, host: h });
        resolve();
      });
    });
  }

  close(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server.close((err) => { if (err) reject(err); else resolve(); });
    });
  }
}
`);

write("acp/acp-client.ts", `import type { ACPMessage, ACPTask, ACPSession } from "./acp-types.js";

export class ACPClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private msgId = 1;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async send(method: string, params?: unknown): Promise<unknown> {
    const msg: ACPMessage = { jsonrpc: "2.0", id: this.msgId++, method, ...(params ? { params } : {}) };
    const res = await fetch(this.baseUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(this.sessionId ? { "X-Session-Id": this.sessionId } : {}) },
      body: JSON.stringify(msg),
    });
    const data = await res.json() as ACPMessage;
    if (data.error) throw new Error(data.error.message);
    return data.result;
  }

  async initialize(): Promise<ACPSession> {
    const result = await this.send("initialize") as ACPSession;
    this.sessionId = result.id;
    return result;
  }

  async createTask(title: string, description: string, agent?: string): Promise<ACPTask> {
    return this.send("tasks/create", { title, description, agent }) as Promise<ACPTask>;
  }

  async getCapabilities() {
    return this.send("capabilities");
  }
}
`);

write("commands/acp.ts", `import { Command } from "commander";
import chalk from "chalk";
import { ACPServer } from "../acp/acp-server.js";
import { ACPClient } from "../acp/acp-client.js";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";

export function acpCommand(): Command {
  const cmd = new Command("acp").description("Agent Communication Protocol server and client");

  cmd.command("serve").description("Start ACP server").option("--port <port>", "Port to listen on", "3141").option("--host <host>", "Host to bind to", "127.0.0.1").action(async (opts) => {
    const creds = loadCredentials();
    const config = loadConfig();
    const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);
    console.log(chalk.bold("\n  🔌 Starting ACP Server...\n"));
    const server = new ACPServer({
      port: parseInt(opts.port),
      host: opts.host,
      onTask: async (task) => {
        let result = "";
        for await (const chunk of model.complete({
          model: config.model ?? "claude-3-5-haiku-20241022",
          system: "You are BharatBuild CLI agent.",
          messages: [{ role: "user", content: task.description }],
          tools: [], maxTokens: 2000,
        })) {
          if (chunk.type === "text_delta" && chunk.text) result += chunk.text;
        }
        return result;
      },
    });
    await server.listen(parseInt(opts.port), opts.host);
    console.log(chalk.dim("  Press Ctrl+C to stop.\n"));
    await new Promise<void>((resolve) => process.on("SIGINT", async () => { await server.close(); resolve(); }));
  });

  cmd.command("connect <url>").description("Connect to an ACP server").action(async (url: string) => {
    const client = new ACPClient(url);
    try {
      const session = await client.initialize();
      console.log(chalk.green(\`\n  ✅ Connected to ACP server\`));
      console.log(chalk.dim(\`  Session: \${session.id}\n\`));
      const caps = await client.getCapabilities() as Record<string, unknown>;
      console.log(chalk.bold("  Capabilities:"));
      for (const [k, v] of Object.entries(caps)) console.log(\`    \${chalk.cyan(k)}: \${JSON.stringify(v)}\`);
      console.log();
    } catch (err) { console.log(chalk.red(\`  ✗ \${err instanceof Error ? err.message : err}\n\`)); }
  });

  cmd.command("task <url> <description>").description("Send a task to an ACP server").action(async (url: string, description: string) => {
    const client = new ACPClient(url);
    await client.initialize();
    console.log(chalk.dim("\n  Sending task..."));
    const task = await client.createTask("CLI Task", description);
    console.log(chalk.green(\`\n  ✅ Task \${task.status}\`));
    if (task.result) console.log("\n" + task.result + "\n");
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════════════
// 3. CREW SUPPORT
// ═══════════════════════════════════════════════════════════

write("crew/crew-types.ts", `export interface CrewAgent {
  id: string;
  name: string;
  role: string;
  model?: string;
  status: "idle" | "running" | "complete" | "failed";
  task?: string;
  result?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface CrewSession {
  id: string;
  title: string;
  agents: CrewAgent[];
  createdAt: string;
  status: "active" | "complete" | "failed";
}

export interface CrewTask {
  id: string;
  description: string;
  assignedTo?: string;
  dependsOn?: string[];
  status: "pending" | "running" | "complete" | "failed";
  result?: string;
}
`);

write("crew/crew-manager.ts", `import { EventEmitter } from "events";
import type { CrewAgent, CrewSession, CrewTask } from "./crew-types.js";

export class CrewManager extends EventEmitter {
  private sessions = new Map<string, CrewSession>();
  private tasks = new Map<string, CrewTask>();

  createSession(title: string, agentRoles: Array<{ name: string; role: string; model?: string }>): CrewSession {
    const session: CrewSession = {
      id: \`crew-\${Date.now()}\`,
      title,
      agents: agentRoles.map((r, i) => ({
        id: \`agent-\${i}-\${Date.now()}\`,
        name: r.name,
        role: r.role,
        model: r.model,
        status: "idle",
      })),
      createdAt: new Date().toISOString(),
      status: "active",
    };
    this.sessions.set(session.id, session);
    this.emit("session:created", session);
    return session;
  }

  assignTask(sessionId: string, agentId: string, task: string, handler: (task: string) => Promise<string>): void {
    const session = this.sessions.get(sessionId);
    if (!session) return;
    const agent = session.agents.find((a) => a.id === agentId);
    if (!agent) return;
    agent.status = "running";
    agent.task = task;
    agent.startedAt = new Date().toISOString();
    this.emit("agent:started", { session, agent });

    handler(task).then((result) => {
      agent.status = "complete";
      agent.result = result;
      agent.completedAt = new Date().toISOString();
      this.emit("agent:complete", { session, agent });
      if (session.agents.every((a) => a.status === "complete")) {
        session.status = "complete";
        this.emit("session:complete", session);
      }
    }).catch((err: Error) => {
      agent.status = "failed";
      agent.result = err.message;
      agent.completedAt = new Date().toISOString();
      this.emit("agent:failed", { session, agent });
    });
  }

  getSession(id: string) { return this.sessions.get(id); }
  listSessions() { return Array.from(this.sessions.values()); }

  renderMonitor(sessionId: string): string {
    const session = this.sessions.get(sessionId);
    if (!session) return "  Session not found.";
    const lines = [`  📋 Crew: ${session.title}  [${session.status}]\n`];
    for (const agent of session.agents) {
      const icon = agent.status === "running" ? "⠋" : agent.status === "complete" ? "✓" : agent.status === "failed" ? "✗" : "○";
      const task = agent.task ? `  ${agent.task.slice(0, 40)}` : "";
      lines.push(`  ${icon} [${agent.role}] ${agent.name}${task}`);
    }
    return lines.join("\n");
  }
}

export const crewManager = new CrewManager();
`);

write("crew/crew-monitor.ts", `import chalk from "chalk";
import { crewManager } from "./crew-manager.js";
import type { CrewAgent, CrewSession } from "./crew-types.js";
import { getTheme } from "../ui/theme.js";

let monitorInterval: NodeJS.Timeout | null = null;
let visible = false;

export function openCrewMonitor(sessionId?: string): void {
  const t = getTheme();
  visible = true;
  console.log(t.heading("\n  ┌─────────────────── Crew Monitor (Ctrl+G to close) ────────────┐\n"));

  const sessions = sessionId ? [crewManager.getSession(sessionId)].filter(Boolean) as CrewSession[] : crewManager.listSessions();

  if (sessions.length === 0) {
    console.log(t.dim("  No active crew sessions. Use /spawn <task> to start one.\n"));
    console.log(t.heading("  └────────────────────────────────────────────────────────────────┘\n"));
    return;
  }

  const render = () => {
    if (!visible) { if (monitorInterval) clearInterval(monitorInterval); return; }
    process.stdout.write("\x1B[2J\x1B[H"); // clear screen
    console.log(t.heading("\n  ┌─────────────────── Crew Monitor (Ctrl+G to close) ─────────────┐\n"));
    for (const session of sessions) {
      console.log(t.info(\`  📋 \${session.title}  [\${session.id.slice(0, 8)}]  \${getStatusBadge(session.status)}\n\`));
      for (const agent of session.agents) {
        renderAgent(agent, t);
      }
      console.log();
    }
    console.log(t.heading("  └────────────────────────────────────────────────────────────────┘"));
    console.log(t.dim("\n  Ctrl+G to close | Ctrl+D/Ctrl+U to navigate sessions\n"));
  };

  render();
  monitorInterval = setInterval(render, 500);
}

function renderAgent(agent: CrewAgent, t: ReturnType<typeof getTheme>) {
  const icons: Record<string, string> = { idle: "○", running: "⠋", complete: "✓", failed: "✗" };
  const colors: Record<string, (s: string) => string> = {
    idle: t.dim, running: t.warning, complete: t.success, failed: t.error
  };
  const icon = icons[agent.status] ?? "○";
  const color = colors[agent.status] ?? t.dim;
  const dur = agent.startedAt && agent.completedAt
    ? chalk.dim(` (${Math.round((new Date(agent.completedAt).getTime() - new Date(agent.startedAt).getTime()) / 1000)}s)`)
    : agent.startedAt ? chalk.dim(" (running...)") : "";
  console.log(\`  \${color(icon)} \${chalk.bold(agent.name.padEnd(15))} \${chalk.dim(agent.role.padEnd(12))} \${agent.task ? chalk.dim(agent.task.slice(0, 35)) : ""}\${dur}\`);
}

function getStatusBadge(status: string): string {
  const badges: Record<string, string> = { active: chalk.cyan("ACTIVE"), complete: chalk.green("COMPLETE"), failed: chalk.red("FAILED") };
  return badges[status] ?? chalk.dim(status);
}

export function closeCrewMonitor(): void {
  visible = false;
  if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
}
`);

write("commands/crew.ts", `import { Command } from "commander";
import chalk from "chalk";
import { crewManager } from "../crew/crew-manager.js";
import { openCrewMonitor, closeCrewMonitor } from "../crew/crew-monitor.js";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClient } from "../models/model-router.js";

export function crewCommand(): Command {
  const cmd = new Command("crew").description("Manage multi-agent crew sessions");

  cmd.command("spawn <task>").description("Spawn a parallel agent session").option("--agents <names>", "Comma-separated agent names", "planner,coder,tester").action(async (task: string, opts) => {
    const creds = loadCredentials();
    const config = loadConfig();
    const model = createModelClient(config.model ?? "claude-3-5-haiku-20241022", creds?.token);
    const agentNames = (opts.agents as string).split(",").map((a) => a.trim());
    const session = crewManager.createSession(task, agentNames.map((name) => ({ name, role: name })));
    console.log(chalk.bold(\`\n  🚀 Crew session started: \${session.id}\n\`));

    for (const agent of session.agents) {
      crewManager.assignTask(session.id, agent.id, \`[\${agent.role}] \${task}\`, async (t) => {
        let result = "";
        for await (const chunk of model.complete({
          model: config.model ?? "claude-3-5-haiku-20241022",
          system: \`You are the \${agent.role} agent. Focus on your specific role.\`,
          messages: [{ role: "user", content: t }],
          tools: [], maxTokens: 1000,
        })) {
          if (chunk.type === "text_delta" && chunk.text) result += chunk.text;
        }
        return result;
      });
    }
    console.log(chalk.dim("  Agents working in parallel. Run: bharatbuild crew monitor\n"));
  });

  cmd.command("monitor [sessionId]").description("Open crew monitor (Ctrl+G to open in TUI)").action((sessionId?: string) => {
    openCrewMonitor(sessionId);
    setTimeout(closeCrewMonitor, 10000); // auto-close after 10s in non-interactive mode
  });

  cmd.command("list").description("List crew sessions").action(() => {
    const sessions = crewManager.listSessions();
    if (sessions.length === 0) { console.log(chalk.dim("\n  No crew sessions.\n")); return; }
    console.log(chalk.bold("\n  🤖 Crew Sessions\n"));
    for (const s of sessions) {
      const badge = s.status === "complete" ? chalk.green("✓") : s.status === "failed" ? chalk.red("✗") : chalk.cyan("⠋");
      console.log(\`  \${badge} \${chalk.bold(s.id.slice(0, 12))}  \${s.title.slice(0, 40)}  \${chalk.dim(s.agents.length + " agents")}\`);
    }
    console.log();
  });

  cmd.command("status <sessionId>").description("Get crew session status").action((sessionId: string) => {
    console.log(crewManager.renderMonitor(sessionId));
  });

  return cmd;
}
`);

// ═══════════════════════════════════════════════════════════
// 4. SHELL AUTOCOMPLETE
// ═══════════════════════════════════════════════════════════

write("infra/autocomplete.ts", `import fs from "fs";
import os from "os";
import path from "path";

export function generateBashCompletion(): string {
  return \`# BharatBuild CLI bash completion
_bharatbuild_completion() {
  local cur prev words cword
  _init_completion || return

  local commands="chat ask build test fix review task plan spec hooks model init login logout whoami settings doctor update translate diagnostic issue version mcp agent crew acp voice"

  if [[ \$cword -eq 1 ]]; then
    COMPREPLY=( \$(compgen -W "\$commands" -- "\$cur") )
    return
  fi

  case "\$prev" in
    model) COMPREPLY=( \$(compgen -W "claude-3-5-haiku-20241022 claude-3-5-sonnet-20241022 gpt-4o gpt-4o-mini gemini-1.5-pro ollama/llama3" -- "\$cur") ) ;;
    --effort) COMPREPLY=( \$(compgen -W "low medium high xhigh max" -- "\$cur") ) ;;
    --agent) COMPREPLY=( \$(compgen -W "default planner coder tester fixer reviewer guide" -- "\$cur") ) ;;
    --format) COMPREPLY=( \$(compgen -W "plain json json-pretty" -- "\$cur") ) ;;
    *) COMPREPLY=( \$(compgen -f -- "\$cur") ) ;;
  esac
}
complete -F _bharatbuild_completion bharatbuild\`;
}

export function generateZshCompletion(): string {
  return \`#compdef bharatbuild
# BharatBuild CLI zsh completion

_bharatbuild() {
  local -a commands
  commands=(
    'chat:Start interactive chat session'
    'ask:Ask a single question'
    'build:Build the project'
    'test:Run tests'
    'fix:Fix errors'
    'review:Review code'
    'task:Manage tasks'
    'plan:Create a plan'
    'spec:Spec-driven workflow'
    'hooks:Manage hooks'
    'model:Switch model'
    'init:Initialize project'
    'login:Authenticate'
    'logout:Sign out'
    'whoami:Show current user'
    'settings:Manage settings'
    'doctor:Diagnose issues'
    'update:Update CLI'
    'translate:Natural language to shell'
    'diagnostic:System diagnostics'
    'issue:Create GitHub issue'
    'version:Show version'
    'mcp:Manage MCP servers'
    'agent:Manage agents'
    'crew:Multi-agent crew'
    'acp:Agent Communication Protocol'
    'voice:Voice mode'
  )
  _describe 'command' commands
}
_bharatbuild\`;
}

export function generatePowerShellCompletion(): string {
  return \`# BharatBuild CLI PowerShell completion
Register-ArgumentCompleter -Native -CommandName bharatbuild -ScriptBlock {
  param($wordToComplete, $commandAst, $cursorPosition)
  $commands = @('chat','ask','build','test','fix','review','task','plan','spec','hooks','model','init','login','logout','whoami','settings','doctor','update','translate','diagnostic','issue','version','mcp','agent','crew','acp','voice')
  $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
  }
}\`;
}

export function installCompletion(shell?: string): void {
  const detectedShell = shell ?? (process.env["SHELL"] ?? "bash").split("/").pop() ?? "bash";
  let script = "";
  let installPath = "";

  if (detectedShell.includes("zsh")) {
    script = generateZshCompletion();
    installPath = path.join(os.homedir(), ".zsh", "completions", "_bharatbuild");
  } else if (detectedShell.includes("powershell") || process.platform === "win32") {
    script = generatePowerShellCompletion();
    installPath = path.join(os.homedir(), "Documents", "PowerShell", "bharatbuild-completion.ps1");
  } else {
    script = generateBashCompletion();
    installPath = path.join(os.homedir(), ".bash_completion.d", "bharatbuild");
  }

  fs.mkdirSync(path.dirname(installPath), { recursive: true });
  fs.writeFileSync(installPath, script);
  console.log(\`  Completion installed: \${installPath}\`);
  if (detectedShell.includes("bash")) console.log(\`  Add to ~/.bashrc: source \${installPath}\`);
  else if (detectedShell.includes("zsh")) console.log(\`  Add to ~/.zshrc: fpath=(~/.zsh/completions $fpath)\`);
}
`);

write("commands/autocomplete.ts", `import { Command } from "commander";
import chalk from "chalk";
import { installCompletion, generateBashCompletion, generateZshCompletion, generatePowerShellCompletion } from "../infra/autocomplete.js";

export function autocompleteCommand(): Command {
  return new Command("autocomplete")
    .description("Install shell autocompletion for BharatBuild CLI")
    .argument("[shell]", "Shell: bash|zsh|powershell (auto-detected if omitted)")
    .option("--print", "Print the completion script instead of installing")
    .action((shell?: string, opts?) => {
      const detected = shell ?? (process.env["SHELL"] ?? "bash").split("/").pop() ?? "bash";
      if (opts?.print) {
        if (detected.includes("zsh")) console.log(generateZshCompletion());
        else if (detected.includes("powershell") || process.platform === "win32") console.log(generatePowerShellCompletion());
        else console.log(generateBashCompletion());
        return;
      }
      console.log(chalk.bold(\`\n  🔧 Installing \${detected} completion...\n\`));
      installCompletion(detected);
      console.log(chalk.green("\n  ✅ Autocomplete installed!\n"));
    });
}
`);

// ═══════════════════════════════════════════════════════════
// 5. WIRE ALL NEW COMMANDS INTO CLI.TS
// ═══════════════════════════════════════════════════════════

const cliPath = path.join(s, "cli.ts");
let cliContent = fs.readFileSync(cliPath, "utf8");

const newImports = [
  `import { voiceCommand } from "./commands/voice.js";`,
  `import { acpCommand } from "./commands/acp.js";`,
  `import { crewCommand } from "./commands/crew.js";`,
  `import { autocompleteCommand } from "./commands/autocomplete.js";`,
].filter((imp) => !cliContent.includes(imp));

const newRegs = [
  `program.addCommand(voiceCommand());`,
  `program.addCommand(acpCommand());`,
  `program.addCommand(crewCommand());`,
  `program.addCommand(autocompleteCommand());`,
].filter((r) => !cliContent.includes(r));

if (newImports.length) {
  cliContent = cliContent.replace(
    /import \{ hooksCommand \}/,
    newImports.join("\n") + "\nimport { hooksCommand }"
  );
}
if (newRegs.length) {
  cliContent = cliContent.replace(
    /program\.addCommand\(hooksCommand\(\)\);/,
    `program.addCommand(hooksCommand());\n  ${newRegs.join("\n  ")}`
  );
}
fs.writeFileSync(cliPath, cliContent);
console.log("  updated: cli.ts");

console.log("\n✅ Remaining 3% features created!");
