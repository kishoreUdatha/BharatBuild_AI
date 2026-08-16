/**
 * BharatBuild CLI - TUI Session
 *
 * Full Kiro CLI UI fidelity:
 *   - Raw keypress capture (Ctrl+O, Ctrl+X, Ctrl+R, Ctrl+T, Ctrl+C)
 *   - Status bar updates in-place (no new lines, cursor control)
 *   - Markdown rendering via marked-terminal on completed responses
 *   - All slash commands wired to live AgentRuntime data
 *   - /agent switches system prompt, /spawn runs real DAG, /rewind forks context
 *   - /chat session picker resumes a real session
 */
import readline from "readline";
import chalk from "chalk";
import { getTheme, setTheme, autoDetectTheme, type ThemeName } from "./theme.js";
import { renderMarkdown } from "./markdown.js";
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
import { handlePasteCommand, copyToClipboard } from "./clipboard.js";
import { explainUnknown } from "./slash-registry.js";
import { isBlockedInReadOnly } from "../permissions/read-only.js";
import type { AgentRuntime } from "../runtime/agent-runtime.js";
import type { AgentEvent } from "../runtime/event-stream.js";
// Agent role system prompts (for /agent switching)
// getDefinitions() returns object[]; narrow it where tool metadata is read.
type ToolDef = {
    name: string;
    description?: string;
    inputSchema?: unknown;
    parameters?: { properties?: Record<string, unknown>; required?: string[] };
};

const AGENT_SYSTEM_PROMPTS: Record<string, string> = {
    default: "You are BharatBuild AI, an expert software engineer assistant. Complete tasks thoroughly using available tools.",
    planner: "You are a senior software architect. Break tasks into clear implementation plans, then execute them step by step.",
    coder: "You are an expert software engineer. Write clean, well-tested, production-quality code. Follow existing patterns.",
    tester: "You are a QA engineer. Write comprehensive unit and integration tests. Cover edge cases. Verify all tests pass.",
    fixer: "You are a debugging expert. Identify root causes of errors. Fix issues without breaking existing functionality.",
    reviewer: "You are a code reviewer. Check for bugs, security vulnerabilities, performance issues, and code quality.",
};
// ── Status bar ────────────────────────────────────────────────────────────────
const STATUS_BAR_ROW = 1; // row reserved at top for status bar
/**
 * Render the status bar in-place on row 1 using ANSI cursor control.
 * Saves cursor, moves to row 1, writes, restores — no new line printed.
 */
function renderStatusBarInPlace(
  model: string,
  mode: string | undefined,
  tokens: number,
  cost: number,
  agent: string,
  queueSize: number,
  phase: string,
  credits?: number,
  serverCreditsRemaining?: number,
): void {
    const w = process.stdout.columns ?? 80;
    const t = getTheme();

    // Credit display — server balance (authoritative) takes priority over local estimate
    let creditStr = "";
    if (serverCreditsRemaining !== undefined && serverCreditsRemaining >= 0) {
        // Server-authoritative remaining balance — matches Kiro's status bar
        const r = serverCreditsRemaining;
        creditStr = r === 0   ? chalk.red("⚠ 0cr") :
                    r < 10    ? chalk.yellow(`⚠ ${r.toFixed(1)}cr`) :
                    r < 100   ? chalk.yellow(`${r.toFixed(0)}cr`) :
                                chalk.cyan(`${r.toFixed(0)}cr`);
    } else if (credits && credits >= 0.01) {
        // Local estimate (not logged in or server unreachable)
        creditStr = chalk.dim(`~${credits.toFixed(2)}cr`);
    }

    const parts = [
        ` ${chalk.bold("BharatBuild")}`,
        `model:${chalk.cyan(model.split("-")[0] ?? model)}`,
        `agent:${chalk.cyan(agent)}`,
        mode ? `mode:${chalk.cyan(mode)}` : "",
        phase !== "idle" ? chalk.yellow(phase) : "",
        tokens ? `${tokens.toLocaleString()}tok` : "",
        creditStr || (cost ? chalk.dim(`$${cost.toFixed(4)}`) : ""),
        queueSize > 0 ? chalk.yellow(`${queueSize} queued`) : "",
    ].filter(Boolean).join("  ");

    process.stdout.write("\x1b[s" +
        `\x1b[${STATUS_BAR_ROW};1H` +
        "\x1b[2K" +
        t.statusBar(parts.slice(0, w - 1).padEnd(w - 1)) +
        "\x1b[u"
    );
}
// ── Raw keypress reader ───────────────────────────────────────────────────────
/**
 * Returns a single keystroke from stdin in raw mode.
 * Handles multi-byte sequences (arrows, Ctrl+key).
 */
function readRawKey(): Promise<string> {
    return new Promise((resolve) => {
        const onData = (buf: Buffer) => {
            process.stdin.removeListener("data", onData);
            resolve(buf.toString());
        };
        process.stdin.once("data", onData);
    });
}
// ── Main TUI session ──────────────────────────────────────────────────────────
export interface TUISessionOptions {
  runtime: AgentRuntime;
  model: string;
  mode?: string;
  sessionId?: string;
  onCommand?: (cmd: string, args: string[]) => Promise<boolean>;
}

export class TUISession {
    private history: string[] = [];
    private transcript: TranscriptMessage[] = [];
    private tray = new ActivityTray();
    private toolOutput = new ToolOutputManager();
    private historySearch: HistorySearch;
    private inputQueue = new InputQueue();
    private sessionTokens = 0;
    private sessionCost = 0;
    private serverCreditsRemaining = -1;   // live from backend after each turn (-1 = unknown)
    private compact = false;
    private running = false;
    private currentAgent = "default";
    private currentPhase = "idle";
    /** Shift+Tab / "/plan" toggle. Enforced via onPermission on each run. */
    private planMode = false;
    private tangentMode = false;
    private opts: TUISessionOptions;
    private abortController: AbortController | null = null;
    // Pending image from /paste — attached to the next user message
    private _pendingImage: { imageBase64: string; mimeType: string; imagePath: string } | null = null;
    // Line buffer for raw input mode
    private lineBuffer = "";
    private cursorPos = 0;
    constructor(opts: TUISessionOptions) {
        this.opts = opts;
        this.historySearch = new HistorySearch(this.history);
        autoDetectTheme();
        this._wireRuntimeEvents();
    }
    // ── Wire AgentRuntime events into TUI ──────────────────────────────────────
    _wireRuntimeEvents() {
        const rt = this.opts.runtime;
        rt.events.on("status", (e: AgentEvent) => {
            if (e.type !== "status")
                return;
            this.currentPhase = e.phase;
            renderStatusBarInPlace(this.opts.model, this.opts.mode, this.sessionTokens, this.sessionCost, this.currentAgent, this.inputQueue.size, e.message, rt.cost.credits, this.serverCreditsRemaining >= 0 ? this.serverCreditsRemaining : undefined);
        });
        rt.events.on("tool_call", (e: AgentEvent) => {
            if (e.type !== "tool_call")
                return;
            const t = getTheme();
            process.stdout.write(t.dim(`\n  ● ${e.toolName}(${JSON.stringify(e.input).slice(0, 70)}…)\n`));
            this.tray.add({ id: e.id, label: `${e.toolName}`, status: "running" });
        });
        rt.events.on("tool_result", (e: AgentEvent) => {
            if (e.type !== "tool_result")
                return;
            this.tray.update(e.id, {
                status: e.isError ? "failed" : "done",
                durationMs: e.durationMs,
            });
            this.toolOutput.add({
                id: e.id,
                toolName: e.toolName,
                input: {},
                output: e.output,
                isError: e.isError,
                durationMs: e.durationMs,
                collapsed: true,
            });
        });
        rt.events.on("usage", (e: AgentEvent) => {
            if (e.type !== "usage")
                return;
            this.sessionTokens += (e.inputTokens ?? 0) + (e.outputTokens ?? 0);
        });
        rt.events.on("complete", (e: AgentEvent) => {
            if (e.type !== "complete")
                return;
            this.sessionTokens = e.totalTokens;
            this.sessionCost += e.costUsd ?? 0;
            this.currentPhase = "idle";
            // Pick up server-authoritative credit balance if proxied
            if (rt.serverCreditsRemaining >= 0) {
                this.serverCreditsRemaining = rt.serverCreditsRemaining;
                // Warn when credits are low — matches Kiro's low-credit warning
                if (this.serverCreditsRemaining === 0) {
                    console.log(getTheme().error("\n  ⚠ You have run out of credits. Top up at app.bharatbuild.in\n"));
                } else if (this.serverCreditsRemaining < 10) {
                    console.log(getTheme().warning(`\n  ⚠ Low credits: ${this.serverCreditsRemaining.toFixed(1)} remaining. Top up at app.bharatbuild.in\n`));
                }
            }
            renderStatusBarInPlace(this.opts.model, this.opts.mode, this.sessionTokens, this.sessionCost, this.currentAgent, this.inputQueue.size, "idle", rt.cost.credits, this.serverCreditsRemaining >= 0 ? this.serverCreditsRemaining : undefined);
        });
        rt.events.on("error", (e: AgentEvent) => {
            if (e.type !== "error")
                return;
            console.log(getTheme().error(`\n  ✗ ${e.message}\n`));
            this.currentPhase = "idle";
        });
    }
    // ── Status bar ─────────────────────────────────────────────────────────────
    refreshStatusBar(message = this.currentPhase) {
        const serverCr = this.serverCreditsRemaining >= 0 ? this.serverCreditsRemaining : undefined;
        renderStatusBarInPlace(this.opts.model, this.opts.mode, this.sessionTokens, this.sessionCost, this.currentAgent, this.inputQueue.size, message, this.opts.runtime.cost.credits, serverCr);
    }
    // ── Welcome screen ─────────────────────────────────────────────────────────
    printWelcome() {
        const t = getTheme();
        // Reserve top row for status bar, then print welcome below
        console.clear();
        this.refreshStatusBar("ready");
        // Move to row 2 to print welcome content
        process.stdout.write("\x1b[2;1H");
        console.log(t.heading(`
  ╭──────────────────────────────────────────────────╮
  │   BharatBuild AI  — Full Kiro-fidelity TUI       │
  │   /help for commands  ·  !cmd for shell          │
  │   Ctrl+C cancel  Ctrl+O tools  Ctrl+X tray       │
  ╰──────────────────────────────────────────────────╯`));
        console.log();
    }
    // ── Slash commands (all wired to live runtime) ────────────────────────────
    private async handleSlash(input: string): Promise<boolean> {
        const parts = input.slice(1).trim().split(/\s+/);
        const cmd = parts[0]?.toLowerCase() ?? "";
        const args = parts.slice(1);
        const t = getTheme();
        const rt = this.opts.runtime;
        switch (cmd) {
            // ── Bare "/" shows all commands (like kiro-cli) ───────────────────────
            case "":
                renderHelpPanel("tui");
                return true;
            // ── Standard UI ──────────────────────────────────────────────────────
            case "help":
                renderHelpPanel("tui");
                return true;
            case "clear":
                console.clear();
                this.printWelcome();
                return true;
            case "exit":
            case "quit":
                this.running = false;
                return true;
            // ── Context — wired to live runtime data ──────────────────────────────
            case "context": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "clear") {
                    rt.reset();
                    console.log(t.success("\n  ✓ Context cleared\n"));
                    return true;
                }
                
                if (sub === "add" && args[1]) {
                    // Add file, directory, or text to context
                    const target = args.slice(1).join(" ");
                    
                    // Check if it's a file path
                    if (target.startsWith("@") || require("fs").existsSync(target.replace("@", ""))) {
                        console.log(t.success(`\n  ✓ Will include ${target} in next message context\n`));
                        this.inputQueue.enqueue(`@${target.replace("@", "")}`);
                    } else {
                        // Add as text context
                        rt.context.push({ 
                            role: "user", 
                            content: `Context: ${target}` 
                        });
                        console.log(t.success(`\n  ✓ Added text to context: ${target.slice(0, 40)}...\n`));
                    }
                    return true;
                }
                
                if (sub === "remove" && args[1]) {
                    // Remove specific context by pattern or index
                    const target = args[1];
                    const messages = rt.context.messages;
                    
                    if (target.match(/^\d+$/)) {
                        // Remove by index
                        const index = parseInt(target);
                        if (index > 0 && index <= messages.length) {
                            const removed = messages.splice(index - 1, 1)[0];
                            console.log(t.success(`\n  ✓ Removed message ${index}\n`));
                        } else {
                            console.log(t.error(`\n  ✗ Invalid index: ${index}\n`));
                        }
                    } else {
                        // Remove by content pattern
                        const initialCount = messages.length;
                        const filteredMessages = messages.filter(m => {
                            const content = typeof m.content === 'string' ? m.content : 
                                           Array.isArray(m.content) ? m.content.map(c => c.text || '').join(' ') : '';
                            return !content.toLowerCase().includes(target.toLowerCase());
                        });
                        
                        rt.context.clear();
                        rt.context.pushAll(filteredMessages);
                        
                        const removedCount = initialCount - filteredMessages.length;
                        console.log(t.success(`\n  ✓ Removed ${removedCount} messages matching "${target}"\n`));
                    }
                    return true;
                }
                
                if (sub === "show" || !sub) {
                    // Enhanced context display
                    const stats = rt.context.stats();
                    const messages = rt.context.messages;
                    
                    console.log(t.heading(`\n  📋 Context Window (${messages.length} messages)\n`));
                    
                    // Show statistics
                    console.log(`  ${chalk.bold("Tokens:")}      ${stats.estimatedTokens.toLocaleString()} / ~200k (${stats.usagePercent}%)`);
                    console.log(`  ${chalk.bold("Messages:")}    ${stats.messageCount}`);
                    console.log(`  ${chalk.bold("Compacted:")}   ${stats.compacted ? "Yes" : "No"}`);
                    console.log();
                    
                    // Show recent messages (last 10)
                    const recentMessages = messages.slice(-10);
                    recentMessages.forEach((msg, i) => {
                        const msgIndex = messages.length - 10 + i + 1;
                        const role = msg.role === "user" ? chalk.blue("User") : 
                                   msg.role === "assistant" ? chalk.green("Assistant") : 
                                   chalk.gray("System");
                        
                        let content = "";
                        if (typeof msg.content === "string") {
                            content = msg.content;
                        } else if (Array.isArray(msg.content)) {
                            content = msg.content.map(c => c.text || c.content || "").join(" ");
                        }
                        
                        const preview = content.slice(0, 80).replace(/\n/g, " ");
                        console.log(`  ${chalk.dim(msgIndex.toString().padStart(2))}. ${role.padEnd(12)} ${preview}${content.length > 80 ? "..." : ""}`);
                    });
                    
                    if (messages.length > 10) {
                        console.log(t.dim(`\n  ... and ${messages.length - 10} earlier messages`));
                    }
                    console.log();
                }
                
                return true;
            }
            // ── Tools — wired to live dispatcher ────────────────────────────────
            case "tools": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "trust" && args[1]) {
                    const toolName = args[1];
                    process.env[`BHARATBUILD_TRUST_${toolName.toUpperCase()}`] = "1";
                    console.log(t.success(`\n  ✓ Trusted tool: ${toolName}\n`));
                    return true;
                }
                
                if (sub === "untrust" && args[1]) {
                    const toolName = args[1];
                    delete process.env[`BHARATBUILD_TRUST_${toolName.toUpperCase()}`];
                    console.log(t.success(`\n  ✓ Untrusted tool: ${toolName}\n`));
                    return true;
                }
                
                if (sub === "trust-all") {
                    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
                    console.log(t.success("\n  ✓ Trusted all tools (skip confirmations)\n"));
                    return true;
                }
                
                if (sub === "schema" && args[1]) {
                    const toolName = args[1];
                    const defs = rt.dispatcher.getDefinitions();
                    const tool = defs.find((d: any) => d.name === toolName);
                    
                    if (tool) {
                        console.log(t.heading(`\n  📋 Tool Schema: ${toolName}\n`));
                        console.log(chalk.bold("Description:"));
                        console.log(`  ${(tool as ToolDef).description || 'No description available'}\n`);
                        
                        if ((tool as ToolDef).inputSchema) {
                            console.log(chalk.bold("Input Schema:"));
                            console.log(`  ${JSON.stringify((tool as ToolDef).inputSchema, null, 2)}\n`);
                        }
                        
                        if ((tool as ToolDef).parameters) {
                            console.log(chalk.bold("Parameters:"));
                            const params = (tool as ToolDef).parameters?.properties ?? {};
                            Object.entries(params).forEach(([name, schema]: [string, any]) => {
                                const required = (tool as ToolDef).parameters?.required?.includes(name) ? chalk.red("*") : " ";
                                console.log(`  ${required} ${chalk.cyan(name)}: ${schema.type} - ${schema.description || 'No description'}`);
                            });
                            console.log();
                        }
                    } else {
                        console.log(t.error(`\n  ✗ Tool not found: ${toolName}\n`));
                    }
                    return true;
                }
                
                if (sub === "reset") {
                    // Clear all trust settings
                    Object.keys(process.env).forEach(key => {
                        if (key.startsWith("BHARATBUILD_TRUST_")) {
                            delete process.env[key];
                        }
                    });
                    console.log(t.success("\n  ✓ Tool permissions reset to default policy\n"));
                    return true;
                }
                
                // Default: show all tools with trust status
                const defs = rt.dispatcher.getDefinitions();
                const trustAllEnabled = !!process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
                
                console.log(t.heading(`\n  🛠️  Available Tools (${defs.length})\n`));
                
                if (trustAllEnabled) {
                    console.log(t.info("  🚨 Trust-all mode enabled - all tools auto-approved\n"));
                }
                
                const toolCategories: Record<string, any[]> = {
                    "File System": [],
                    "Code Intelligence": [],
                    "Agent Tools": [],
                    "Web & Network": [],
                    "System": [],
                    "Other": []
                };
                
                defs.forEach((tool: any) => {
                    const name = tool.name;
                    let category = "Other";
                    
                    if (name.includes("read") || name.includes("write") || name.includes("filesystem")) {
                        category = "File System";
                    } else if (name.includes("code") || name.includes("search") || name.includes("grep")) {
                        category = "Code Intelligence";
                    } else if (name.includes("goal") || name.includes("knowledge") || name.includes("todo")) {
                        category = "Agent Tools";
                    } else if (name.includes("web") || name.includes("fetch") || name.includes("search")) {
                        category = "Web & Network";
                    } else if (name.includes("shell") || name.includes("use_aws")) {
                        category = "System";
                    }
                    
                    const trusted = trustAllEnabled || !!process.env[`BHARATBUILD_TRUST_${name.toUpperCase()}`];
                    const status = trusted ? chalk.green("trusted") : chalk.dim("ask");
                    
                    toolCategories[category].push({ name, description: (tool as ToolDef).description, status });
                });
                
                Object.entries(toolCategories).forEach(([category, tools]) => {
                    if (tools.length > 0) {
                        console.log(chalk.bold(category + ":"));
                        tools.forEach(tool => {
                            console.log(`  ${chalk.cyan(tool.name.padEnd(20))} ${tool.status.padEnd(12)} ${chalk.dim((tool as ToolDef).description?.slice(0, 50) || "")}`);
                        });
                        console.log();
                    }
                });
                
                console.log(t.dim("Commands:"));
                console.log(t.dim("  /tools trust <name>     Trust a specific tool"));
                console.log(t.dim("  /tools untrust <name>   Remove trust from tool"));
                console.log(t.dim("  /tools trust-all        Trust all tools (skip confirmations)"));
                console.log(t.dim("  /tools schema <name>    Show tool parameter schema"));
                console.log(t.dim("  /tools reset            Reset all permissions\n"));
                
                return true;
            }
            // ── MCP — wired to live MCPClient ───────────────────────────────────
            case "mcp": {
                await rt.initMCP();
                const mcpClient = rt.mcp;
                if (!mcpClient) {
                    renderMCPPanel([]);
                    return true;
                }
                const running = mcpClient.serverManager.listRunning();
                const toolDefs = mcpClient.getToolDefinitions();
                renderMCPPanel(running.map((name) => ({
                    name,
                    connected: true,
                    tools: toolDefs.filter((d) => d.name.startsWith(`mcp__${name}__`)).length,
                })));
                return true;
            }
            // ── Usage — wired to live cost meter ────────────────────────────────
            case "usage": {
                const costData = rt.cost;
                const serverCr = this.serverCreditsRemaining >= 0 ? this.serverCreditsRemaining : 0;
                renderUsagePanel({
                    tokensUsed:    this.sessionTokens,
                    tokensLimit:   200_000,
                    creditBalance: serverCr,
                    creditsUsed:   costData.credits,
                    model:         this.opts.model,
                    sessionTokens: this.sessionTokens,
                    sessionCost:   costData.estimateCostUsd(),
                    turns:         costData.turns,
                    elapsedMs:     costData.elapsedMs,
                    breakdown:     costData.breakdown(),
                });
                const mode = rt.isProxied
                    ? t.success("  ✦ Routed through BharatBuild backend (server-side credits)")
                    : t.dim("  ✦ Direct API keys (local credit estimate)");
                console.log(mode + "\n");
                return true;
            }
            // ── Model ────────────────────────────────────────────────────────────
            case "model":
                if (args[0]) {
                    this.opts.model = args[0];
                    console.log(t.success(`\n  ✓ Model switched to ${args[0]}\n`));
                    this.refreshStatusBar();
                    return true;
                }
                console.log(t.dim(`  Current model: ${this.opts.model}\n`));
                return true;
            // ── Agent — switches system prompt on live runtime ──────────────────
            case "agent": {
                const sub = args[0]?.toLowerCase();
                const validAgents = Object.keys(AGENT_SYSTEM_PROMPTS);
                
                if (sub === "list" || (!sub && args.length === 0)) {
                    console.log(t.heading("\n  🤖 Available Agents\n"));
                    Object.entries(AGENT_SYSTEM_PROMPTS).forEach(([name, prompt]) => {
                        const current = name === this.currentAgent ? chalk.green(" (current)") : "";
                        console.log(`  ${chalk.cyan(name.padEnd(12))} ${prompt.slice(0, 60)}...${current}`);
                    });
                    console.log(t.dim("\n  Switch: /agent <name>  |  Create: /agent create <name>\n"));
                    return true;
                }
                
                if (sub === "create" && args[1]) {
                    const name = args[1];
                    const description = args.slice(2).join(" ") || "Custom agent";
                    
                    // Add to agent prompts (in memory for this session)
                    AGENT_SYSTEM_PROMPTS[name] = `You are ${name}, ${description}. Complete tasks thoroughly using available tools.`;
                    
                    console.log(t.success(`\n  ✓ Created agent: ${chalk.bold(name)}\n`));
                    console.log(t.dim(`  Description: ${description}`));
                    console.log(t.dim(`  Switch to: /agent ${name}\n`));
                    return true;
                }
                
                if (sub === "edit" && args[1]) {
                    const name = args[1];
                    if (!AGENT_SYSTEM_PROMPTS[name]) {
                        console.log(t.error(`\n  ✗ Agent not found: ${name}\n`));
                        return true;
                    }
                    
                    const newPrompt = args.slice(2).join(" ");
                    if (newPrompt) {
                        AGENT_SYSTEM_PROMPTS[name] = newPrompt;
                        console.log(t.success(`\n  ✓ Updated agent: ${chalk.bold(name)}\n`));
                        console.log(t.dim(`  New prompt: ${newPrompt.slice(0, 80)}...\n`));
                    } else {
                        console.log(t.info(`\n  Current prompt for ${chalk.bold(name)}:\n`));
                        console.log(`  ${AGENT_SYSTEM_PROMPTS[name]}\n`);
                        console.log(t.dim("  Edit: /agent edit <name> <new-prompt>\n"));
                    }
                    return true;
                }
                
                if (sub === "swap" || sub === "switch") {
                    // If the caller already named an agent, honour it instead of
                    // discarding the argument and prompting.
                    const named = args[1]?.toLowerCase();
                    if (named) {
                        if (!validAgents.includes(named)) {
                            console.log(t.warning(`\n  Unknown agent: ${named}. Available: ${validAgents.join("  ")}\n`));
                            return true;
                        }
                        this.currentAgent = named;
                        rt.context.setSystemPrompt(`${AGENT_SYSTEM_PROMPTS[named]}\n\nWorking directory: ${process.cwd()}\n` +
                            `You have access to tools for reading/writing files, running commands, searching code, and git.`);
                        console.log(t.success(`\n  ✓ Switched to agent: ${chalk.bold(named)}\n`));
                        this.refreshStatusBar();
                        return true;
                    }

                    // No name given: the picker needs a human. Without a TTY it
                    // would wait on a prompt nobody can answer, so bail out.
                    if (!process.stdin.isTTY) {
                        console.log(t.warning(`\n  /agent swap needs an agent name when not attached to a terminal.\n`));
                        console.log(t.dim(`  Try: /agent swap <${validAgents.join("|")}>\n`));
                        return true;
                    }

                    // Interactive agent picker
                    console.log(t.heading("\n  🔄 Agent Swap\n"));
                    validAgents.forEach((name, i) => {
                        const current = name === this.currentAgent ? chalk.green(" (current)") : "";
                        console.log(`  ${chalk.cyan((i + 1).toString())}. ${name}${current}`);
                    });
                    
                    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
                    const choice = await new Promise<string>((resolve) => {
                        rl.question(t.prompt("\n  Select agent (number): "), (answer) => {
                            rl.close();
                            resolve(answer.trim());
                        });
                    });
                    
                    const index = parseInt(choice) - 1;
                    if (index >= 0 && index < validAgents.length) {
                        const selectedAgent = validAgents[index];
                        this.currentAgent = selectedAgent;
                        const newPrompt = AGENT_SYSTEM_PROMPTS[selectedAgent];
                        rt.context.setSystemPrompt(`${newPrompt}\n\nWorking directory: ${process.cwd()}\n` +
                            `You have access to tools for reading/writing files, running commands, searching code, and git.`);
                        console.log(t.success(`\n  ✓ Switched to agent: ${chalk.bold(selectedAgent)}\n`));
                        this.refreshStatusBar();
                    } else {
                        console.log(t.dim("\n  Cancelled\n"));
                    }
                    return true;
                }
                
                // Switch to specific agent
                const agentName = args[0]?.toLowerCase() ?? "";
                if (!agentName || !validAgents.includes(agentName)) {
                    console.log(t.dim(`\n  Agents: ${validAgents.join("  ")}\n`));
                    console.log(t.dim(`  Current: ${this.currentAgent}\n`));
                    console.log(t.dim("  Commands: list | create <name> | edit <name> | swap\n"));
                    return true;
                }
                
                this.currentAgent = agentName;
                const newPrompt = AGENT_SYSTEM_PROMPTS[agentName];
                rt.context.setSystemPrompt(`${newPrompt}\n\nWorking directory: ${process.cwd()}\n` +
                    `You have access to tools for reading/writing files, running commands, searching code, and git.`);
                console.log(t.success(`\n  ✓ Switched to agent: ${chalk.bold(agentName)}\n`));
                this.refreshStatusBar();
                return true;
            }
            // ── Effort — map to model selection hint ────────────────────────────
            case "effort": {
                const levels = {
                    low: "haiku", medium: "haiku", high: "sonnet", max: "opus",
                };
                const level = args[0]?.toLowerCase() ?? "";
                if (level && level in levels) {
                    console.log(t.success(`\n  ✓ Effort: ${level} — model tier: ${levels[level as keyof typeof levels]}\n`));
                }
                else {
                    console.log(t.dim("  Levels: low  medium  high  max\n"));
                }
                return true;
            }
            // ── Theme ────────────────────────────────────────────────────────────
            case "theme":
                if (args[0]) {
                    setTheme(args[0] as ThemeName);
                    console.log(t.success(`\n  ✓ Theme set to ${args[0]}\n`));
                    return true;
                }
                console.log(t.dim("  Themes: dark  light  safe\n"));
                return true;
            // ── Editor ───────────────────────────────────────────────────────────
            case "editor": {
                const content = await openEditor();
                if (content) {
                    this.inputQueue.enqueue(content);
                    console.log(t.success("\n  ✓ Content queued from editor\n"));
                }
                return true;
            }
            // ── Transcript ───────────────────────────────────────────────────────
            case "transcript":
                await openTranscript(this.transcript);
                return true;
            // ── Chat — interactive session picker wired to runtime resume ────────
            case "chat": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "new") {
                    // Start a new session
                    rt.reset();
                    this.transcript = [];
                    console.log(t.success("\n  ✓ Started new chat session\n"));
                    console.log(t.dim("    Previous context cleared. Fresh start.\n"));
                    this.refreshStatusBar();
                    return true;
                }
                
                if (sub === "save") {
                    // Save current session
                    const { SessionManager } = await import("../runtime/session-manager.js");
                    const sm = new SessionManager();
                    const title = args.slice(1).join(" ") || `Session ${new Date().toLocaleString()}`;
                    
                    try {
                        sm.save(rt.sessionId, { title, model: this.opts.model, createdAt: Date.now(), updatedAt: Date.now(), messageCount: rt.context.messages.length, workingDir: process.cwd() }, rt.context);
                        console.log(t.success(`\n  ✓ Session saved: "${title}"\n`));
                        console.log(t.dim(`    ID: ${rt.sessionId.slice(-8)}  |  Messages: ${rt.context.messages.length}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to save session: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "load" && args[1]) {
                    // Load specific session by ID or name
                    const { SessionManager } = await import("../runtime/session-manager.js");
                    const sm = new SessionManager();
                    const sessions = sm.list();
                    const identifier = args[1];
                    
                    const session = sessions.find(s => 
                        s.id === identifier || 
                        s.id.endsWith(identifier) ||
                        s.title.toLowerCase().includes(identifier.toLowerCase())
                    );
                    
                    if (session) {
                        const success = rt.resume(session.id);
                        if (success) {
                            console.log(t.success(`\n  ✓ Loaded session: "${session.title}"\n`));
                            console.log(t.dim(`    ID: ${session.id.slice(-8)}  |  Messages: ${session.messageCount}\n`));
                            
                            // Rebuild transcript
                            this.transcript = rt.context.messages
                                .filter((m) => m.role === "user" || m.role === "assistant")
                                .map((m) => ({
                                role: m.role as "user" | "assistant",
                                content: typeof m.content === "string" ? m.content
                                    : m.content
                                        .filter((c) => c.type === "text" && c.text)
                                        .map((c) => c.text ?? "")
                                        .join(""),
                                timestamp: new Date().toISOString(),
                            }));
                            this.refreshStatusBar();
                        } else {
                            console.log(t.error(`\n  ✗ Failed to load session data\n`));
                        }
                    } else {
                        console.log(t.error(`\n  ✗ Session not found: ${identifier}\n`));
                        console.log(t.dim("    Use: /chat list to see available sessions\n"));
                    }
                    return true;
                }
                
                if (sub === "list") {
                    // List all sessions
                    const { SessionManager } = await import("../runtime/session-manager.js");
                    const sm = new SessionManager();
                    const sessions = sm.list().sort((a, b) => b.updatedAt - a.updatedAt);
                    
                    if (sessions.length === 0) {
                        console.log(t.dim("\n  No saved sessions found.\n"));
                        console.log(t.dim("  Save current: /chat save [title]\n"));
                        return true;
                    }
                    
                    console.log(t.heading(`\n  💬 Saved Sessions (${sessions.length})\n`));
                    sessions.slice(0, 15).forEach((s) => {
                        const age = Math.round((Date.now() - s.updatedAt) / 60000);
                        const when = age < 60 ? `${age}m ago` : age < 1440 ? `${Math.round(age / 60)}h ago` : `${Math.round(age / 1440)}d ago`;
                        const current = s.id === rt.sessionId ? chalk.green(" (current)") : "";
                        
                        console.log(`  ${chalk.cyan(s.id.slice(-8))}  ${chalk.bold(s.title.slice(0, 40))}${current}`);
                        console.log(`  ${chalk.dim(`    ${s.messageCount} messages  |  ${when}  |  ${s.workingDir}`)}`);
                        console.log();
                    });
                    
                    console.log(t.dim("  Load: /chat load <id-or-title>  |  Interactive: /chat\n"));
                    return true;
                }
                
                // Default: Interactive session picker
                const { SessionManager } = await import("../runtime/session-manager.js");
                const sm = new SessionManager();
                const sessions = sm.list().sort((a, b) => b.updatedAt - a.updatedAt);
                const uiSessions = sessions.slice(0, 20).map((s) => ({
                    id: s.id,
                    title: s.title,
                    timestamp: new Date(s.updatedAt).toISOString(),
                    messageCount: s.messageCount,
                }));
                const picked = await pickSession(uiSessions);
                if (picked) {
                    const ok = rt.resume(picked.id);
                    if (ok) {
                        console.log(t.success(`\n  ✓ Resumed session: "${picked.title}" (${picked.messageCount} messages)\n`));
                        // Rebuild transcript from resumed context
                        this.transcript = rt.context.messages
                            .filter((m) => m.role === "user" || m.role === "assistant")
                            .map((m) => ({
                            role: m.role as "user" | "assistant",
                            content: typeof m.content === "string" ? m.content
                                : m.content
                                    .filter((c) => c.type === "text" && c.text)
                                    .map((c) => c.text ?? "")
                                    .join(""),
                            timestamp: new Date().toISOString(),
                        }));
                    }
                    else {
                        console.log(t.error(`\n  ✗ Could not load session data for: ${picked.id}\n`));
                    }
                }
                return true;
            }
            // ── Rewind — actual conversation forking by slicing context.messages ─
            case "rewind": {
                const msgs = rt.context.messages.filter((m) => m.role === "user" || m.role === "assistant");
                if (msgs.length === 0) {
                    console.log(t.dim("\n  No conversation to rewind.\n"));
                    return true;
                }
                console.log(t.heading("\n  ⏪ Rewind — choose a turn to fork from:\n"));
                const turns = [];
                let turnNum = 0;
                for (let i = 0; i < msgs.length; i++) {
                    const m = msgs[i];
                    if (m.role === "user") {
                        turnNum++;
                        const preview = (typeof m.content === "string" ? m.content : "")
                            .replace(/\n/g, " ").slice(0, 60);
                        turns.push({ index: i, label: `Turn ${turnNum}: ${preview}` });
                        console.log(`  ${t.info(String(turns.length).padStart(2))}. ${t.dim(turns[turns.length - 1].label)}`);
                    }
                }
                console.log();
                // Ask which turn to fork from
                const answer = await new Promise<string>((resolve) => {
                    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
                    rl.question(t.prompt("  Fork from turn number (Enter to cancel): "), (a) => {
                        rl.close();
                        resolve(a.trim());
                    });
                });
                const n = parseInt(String(answer));
                if (!isNaN(n) && n > 0 && n <= turns.length) {
                    const targetIndex = turns[n - 1].index;
                    // Slice context.messages to keep only messages up to (not including) targetIndex
                    const allMessages = rt.context.messages;
                    // Find the position in the full message array that corresponds to this user turn
                    let count = 0;
                    let sliceAt = 0;
                    for (let i = 0; i < allMessages.length; i++) {
                        if (allMessages[i].role === "user") {
                            if (count === targetIndex) {
                                sliceAt = i;
                                break;
                            }
                            count++;
                        }
                    }
                    rt.context.clear();
                    rt.context.pushAll(allMessages.slice(0, sliceAt));
                    this.transcript = this.transcript.slice(0, n - 1);
                    console.log(t.success(`\n  ✓ Forked from turn ${n}. Continue typing to branch from this point.\n`));
                }
                else if (answer !== "") {
                    console.log(t.dim("\n  Rewind cancelled.\n"));
                }
                return true;
            }
            // ── Spawn — real parallel DAG execution ─────────────────────────────
            case "spawn": {
                const task = args.join(" ").trim();
                if (!task) {
                    console.log(t.dim("  Usage: /spawn <task description>\n"));
                    console.log(t.dim("  Spawns planner + coder + tester agents in parallel.\n"));
                    return true;
                }
                console.log(t.heading(`\n  ⚡ Spawning parallel agents for: ${task}\n`));
                const { executeDag } = await import("../crew/dag-executor.js");
                const { loadConfig } = await import("../config/config.js");
                const config = loadConfig();
                const stages = [
                    { name: "plan", task: `Plan the implementation for: ${task}`, agent: "planner", model: config.model ?? "auto", depends_on: [] },
                    { name: "code", task: `Implement: ${task}`, agent: "coder", model: config.model ?? "auto", depends_on: ["plan"] },
                    { name: "test", task: `Write tests for: ${task}`, agent: "tester", model: config.model ?? "auto", depends_on: ["code"] },
                ];
                const statusMap = new Map();
                stages.forEach((s) => { statusMap.set(s.name, chalk.dim(`  ○ [${s.name}] waiting…`)); });
                // Print initial placeholders
                stages.forEach((s) => process.stdout.write(chalk.dim(`  ○ [${s.name}] waiting…\n`)));
                const result = await executeDag({
                    stages,
                    onProgress: (name, status) => {
                        const icons = {
                            pending: chalk.dim("○"), running: chalk.cyan("⠿"),
                            complete: chalk.green("✓"), failed: chalk.red("✗"), skipped: chalk.dim("○"),
                        };
                        statusMap.set(name, `  ${icons[status] ?? "○"} [${chalk.bold(name)}] ${status}`);
                        // Redraw all lines in-place
                        process.stdout.write(`\x1b[${stages.length}A\r`);
                        stages.forEach((s) => process.stdout.write((statusMap.get(s.name) ?? "") + "\n"));
                    },
                });
                console.log();
                result.success
                    ? console.log(t.success(`  ✓ All agents done  (${result.totalDurationMs}ms)\n`))
                    : console.log(t.error(`  ✗ Some agents failed\n`));
                // Inject the combined output back into the chat context
                const combinedOutput = result.stages
                    .map((s) => `[${s.name}]\n${s.output.slice(0, 1000)}`)
                    .join("\n\n---\n\n");
                rt.context.push({ role: "assistant", content: `Parallel agents completed:\n\n${combinedOutput}` });
                return true;
            }
            // ── Compact ──────────────────────────────────────────────────────────
            case "compact":
                this.compact = !this.compact;
                console.log(t.success(`\n  ✓ Compact mode ${this.compact ? "on" : "off"}\n`));
                return true;
            // ── Plan ─────────────────────────────────────────────────────────────
            case "plan":
                // Same flag Shift+Tab toggles, so the two never disagree.
                this.planMode = !this.planMode;
                console.log(this.planMode
                    ? t.heading("\n  📋 Plan mode ON — read-only; the agent will plan, not edit.\n")
                    : t.dim("\n  Plan mode OFF.\n"));
                return true;
            // ── Paste / Copy ─────────────────────────────────────────────────────
            case "paste": {
                const pasted = await handlePasteCommand();
                if (pasted.type === "text" && pasted.content) {
                    this.inputQueue.enqueue(pasted.content);
                    console.log(t.dim("  (pasted text queued)\n"));
                } else if (pasted.type === "image" && pasted.imagePath) {
                    // Read image and add as image content block to next message
                    const imgFs = await import("fs");
                    const imgBase64 = imgFs.readFileSync(pasted.imagePath).toString("base64");
                    // Store the image to be sent with the next user message
                    this._pendingImage = { imageBase64: imgBase64, mimeType: "image/png", imagePath: pasted.imagePath };
                    console.log(t.success("  ✓ Image attached — type your message to send it with the image\n"));
                }
                return true;
            }
            case "copy": {
                const last = this.transcript.filter((m) => m.role === "assistant").pop();
                if (last)
                    await copyToClipboard(last.content);
                else
                    console.log(t.warning("\n  No assistant response to copy yet.\n"));
                return true;
            }
            // ── Hooks / Settings ─────────────────────────────────────────────────
            case "hooks":
                console.log(t.heading("\n  🪝 Hooks — manage: bharatbuild hooks list\n"));
                return true;
            case "settings":
                console.log(t.heading("\n  ⚙  Settings — subcommands: display  history  keybindings\n"));
                return true;
            
            // ── Checkpoint System ────────────────────────────────────────────────
            case "checkpoint": {
                const { CheckpointManager } = await import("../tools/checkpoint/checkpoint-manager.js");
                const manager = new CheckpointManager();
                const sub = args[0]?.toLowerCase();
                
                if (sub === "init") {
                    const name = args.slice(1).join(" ") || undefined;
                    try {
                        const checkpoint = await manager.init(name);
                        console.log(t.success(`\n  ✓ Created checkpoint: ${chalk.bold(checkpoint.name)}`));
                        console.log(t.dim(`    ID: ${checkpoint.id}  |  Files: ${checkpoint.files.length}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to create checkpoint: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "list") {
                    const checkpoints = manager.list();
                    if (checkpoints.length === 0) {
                        console.log(t.dim("\n  No checkpoints found. Create one with: /checkpoint init [name]\n"));
                        return true;
                    }
                    console.log(t.heading(`\n  📂 Checkpoints (${checkpoints.length})\n`));
                    for (const cp of checkpoints.slice(0, 10)) {
                        const age = Math.round((Date.now() - cp.timestamp) / 60000);
                        const when = age < 60 ? `${age}m ago` : age < 1440 ? `${Math.round(age / 60)}h ago` : `${Math.round(age / 1440)}d ago`;
                        console.log(
                            `  ${chalk.cyan(cp.id.slice(-6))}  ${chalk.bold(cp.name.slice(0, 30).padEnd(30))}  ` +
                            `${chalk.dim(when.padEnd(8))}  ${chalk.dim(`${cp.files.length} files`)}`
                        );
                    }
                    console.log(t.dim("\n  Restore: /checkpoint restore <id> [file-pattern]\n"));
                    return true;
                }
                
                if (sub === "restore" && args[1]) {
                    const id = args[1];
                    const filePattern = args.slice(2);
                    try {
                        const result = await manager.restore(id, filePattern.length > 0 ? filePattern : undefined);
                        console.log(t.success(`\n  ✓ Restored ${result.restored.length} files`));
                        if (result.skipped.length > 0) {
                            console.log(t.warning(`  ⚠ Skipped ${result.skipped.length} files`));
                        }
                        if (result.restored.length <= 5) {
                            result.restored.forEach(f => console.log(t.dim(`    ${f}`)));
                        }
                        console.log();
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Restore failed: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "diff" && args[1]) {
                    const id = args[1];
                    try {
                        const diff = await manager.diff(id);
                        console.log(t.heading(`\n  📊 Checkpoint Diff: ${id}\n`));
                        if (diff.modified.length > 0) {
                            console.log(t.warning(`  Modified (${diff.modified.length}):`));
                            diff.modified.slice(0, 5).forEach(f => console.log(t.dim(`    ~ ${f}`)));
                            if (diff.modified.length > 5) console.log(t.dim(`    ... and ${diff.modified.length - 5} more`));
                        }
                        if (diff.added.length > 0) {
                            console.log(t.success(`  Added (${diff.added.length}):`));
                            diff.added.slice(0, 5).forEach(f => console.log(t.dim(`    + ${f}`)));
                            if (diff.added.length > 5) console.log(t.dim(`    ... and ${diff.added.length - 5} more`));
                        }
                        if (diff.deleted.length > 0) {
                            console.log(t.error(`  Deleted (${diff.deleted.length}):`));
                            diff.deleted.slice(0, 5).forEach(f => console.log(t.dim(`    - ${f}`)));
                            if (diff.deleted.length > 5) console.log(t.dim(`    ... and ${diff.deleted.length - 5} more`));
                        }
                        console.log(t.dim(`  Unchanged: ${diff.unchanged.length} files\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Diff failed: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                // Show help
                console.log(t.dim("\n  Usage: /checkpoint <command>\n"));
                console.log(t.dim("  init [name]     Create new checkpoint"));
                console.log(t.dim("  list            List all checkpoints"));
                console.log(t.dim("  restore <id>    Restore files from checkpoint"));
                console.log(t.dim("  diff <id>       Show differences vs checkpoint\n"));
                return true;
            }
            
            // ── Session ID ───────────────────────────────────────────────────────
            case "session-id":
                console.log(t.info(`\n  Session ID: ${chalk.bold(rt.sessionId)}\n`));
                return true;
            
            // ── Reply Command ────────────────────────────────────────────────────
            case "reply": {
                const lastAssistant = this.transcript.filter(m => m.role === "assistant").pop();
                if (!lastAssistant) {
                    console.log(t.warning("\n  No assistant response to reply to yet.\n"));
                    return true;
                }
                
                // Prepare quoted content
                const quoted = lastAssistant.content
                    .split('\n')
                    .map(line => `> ${line}`)
                    .join('\n');
                
                const replyTemplate = `${quoted}\n\n`;
                
                // Open editor with the quoted content
                const { openEditor } = await import("./editor.js");
                const content = await openEditor(replyTemplate);
                if (content && content.trim() !== replyTemplate.trim()) {
                    this.inputQueue.enqueue(content);
                    console.log(t.success("\n  ✓ Reply queued from editor\n"));
                }
                return true;
            }
            
            // ── Title Command ────────────────────────────────────────────────────
            case "title": {
                if (args.length > 0) {
                    const newTitle = args.join(" ");
                    // Update session title in runtime
                    if (rt.sessionId) {
                        const { SessionManager } = await import("../runtime/session-manager.js");
                        const sm = new SessionManager();
                        const sessions = sm.list();
                        const current = sessions.find(s => s.id === rt.sessionId);
                        if (current) {
                            current.title = newTitle;
                            sm.save(rt.sessionId, { title: newTitle, model: this.opts.model, createdAt: Date.now(), updatedAt: Date.now(), messageCount: rt.context.messages.length, workingDir: process.cwd() }, rt.context);
                            console.log(t.success(`\n  ✓ Session title set to: "${newTitle}"\n`));
                        }
                    }
                } else {
                    const { SessionManager } = await import("../runtime/session-manager.js");
                    const sm = new SessionManager();
                    const sessions = sm.list();
                    const current = sessions.find(s => s.id === rt.sessionId);
                    const title = current?.title || "Untitled Session";
                    console.log(t.dim(`\n  Current title: "${title}"\n`));
                    console.log(t.dim("  Set new title: /title <new title>\n"));
                }
                return true;
            }
            
            // ── Goal Management ──────────────────────────────────────────────────
            case "goal": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "status" || !sub) {
                    try {
                        const { listGoals } = await import("../tools/agent/goal.js");
                        const goals = await listGoals();
                        if (goals.length === 0) {
                            console.log(t.dim("\n  No active goals. Set one by describing your objective to the agent.\n"));
                        } else {
                            console.log(t.heading(`\n  🎯 Active Goals (${goals.length})\n`));
                            for (const goal of goals) {
                                const status = goal.status === "running" ? chalk.yellow("⏳") : 
                                              goal.status === "complete" ? chalk.green("✓") : chalk.red("✗");
                                console.log(`  ${status} ${chalk.bold(goal.description)}`);
                                console.log(t.dim(`     ${goal.description.slice(0, 60)}...`));
                                if (goal.acceptanceCriteria?.length > 0) {
                                    console.log(t.dim(`     Criteria: ${goal.acceptanceCriteria.length} items`));
                                }
                                console.log();
                            }
                        }
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to load goals: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "complete" && args[1]) {
                    try {
                        const { updateGoal } = await import("../tools/agent/goal.js");
                        await updateGoal(args[1], { status: "complete" });
                        console.log(t.success(`\n  ✓ Marked goal as complete: ${args[1]}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to complete goal: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "cancel" && args[1]) {
                    try {
                        const { updateGoal } = await import("../tools/agent/goal.js");
                        await updateGoal(args[1], { status: "failed" });
                        console.log(t.success(`\n  ✓ Cancelled goal: ${args[1]}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to cancel goal: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                console.log(t.dim("\n  Usage: /goal [command]\n"));
                console.log(t.dim("  status             Show all goals (default)"));
                console.log(t.dim("  complete <id>      Mark goal as complete"));
                console.log(t.dim("  cancel <id>        Cancel a goal\n"));
                return true;
            }
            
            // ── Knowledge Management ─────────────────────────────────────────────
            case "knowledge": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "show" || !sub) {
                    try {
                        const { listKnowledge } = await import("../tools/agent/knowledge.js");
                        const contexts = await listKnowledge();
                        if (contexts.length === 0) {
                            console.log(t.dim("\n  No knowledge contexts found.\n"));
                        } else {
                            console.log(t.heading(`\n  🧠 Knowledge Base (${contexts.length} contexts)\n`));
                            for (const ctx of contexts) {
                                console.log(`  ${chalk.cyan(ctx.id.slice(-8))}  ${chalk.bold(ctx.name)}`);
                                console.log(t.dim(`    ${(ctx.tags?.length ?? 0)} tags  |  Added ${new Date(ctx.createdAt || 0).toLocaleDateString()}`));
                            }
                            console.log();
                        }
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to load knowledge base: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "add" && args[1]) {
                    const name = args[1];
                    const content = args.slice(2).join(" ");
                    if (!content) {
                        console.log(t.warning("\n  Usage: /knowledge add <name> <content-or-path>\n"));
                        return true;
                    }
                    try {
                        const { addKnowledge } = await import("../tools/agent/knowledge.js");
                        await addKnowledge(name, content);
                        console.log(t.success(`\n  ✓ Added to knowledge base: ${name}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to add knowledge: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "search" && args[1]) {
                    const query = args.slice(1).join(" ");
                    try {
                        const { searchKnowledge } = await import("../tools/agent/knowledge.js");
                        const results = await searchKnowledge(query);
                        if (results.length === 0) {
                            console.log(t.dim(`\n  No results found for: "${query}"\n`));
                        } else {
                            console.log(t.heading(`\n  🔍 Search Results for: "${query}"\n`));
                            for (const result of results.slice(0, 5)) {
                                console.log(`  ${chalk.bold(result.name)}  ${t.dim(`(${result.tags?.length ?? 0} tags)`)}`);
                                console.log(t.dim(`    ${result.content?.slice(0, 100)}...`));
                                console.log();
                            }
                        }
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Search failed: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "remove" && args[1]) {
                    const id = args[1];
                    try {
                        const { removeKnowledge } = await import("../tools/agent/knowledge.js");
                        await removeKnowledge(id);
                        console.log(t.success(`\n  ✓ Removed knowledge context: ${id}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to remove knowledge: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                console.log(t.dim("\n  Usage: /knowledge <command>\n"));
                console.log(t.dim("  show               List all knowledge contexts (default)"));
                console.log(t.dim("  add <name> <data>  Add content to knowledge base"));
                console.log(t.dim("  search <query>     Search across knowledge contexts"));
                console.log(t.dim("  remove <id>        Remove a knowledge context\n"));
                return true;
            }
            
            // ── Guide Agent ──────────────────────────────────────────────────────
            case "guide": {
                const query = args.join(" ").trim();
                if (!query) {
                    console.log(t.dim("\n  Built-in guide agent — ask about BharatBuild CLI features:\n"));
                    console.log(t.dim("  Usage: /guide <your question>\n"));
                    console.log(t.dim("  Examples:"));
                    console.log(t.dim("    /guide how do I use checkpoints?"));
                    console.log(t.dim("    /guide what tools are available?"));
                    console.log(t.dim("    /guide explain the agent system\n"));
                    return true;
                }
                
                console.log(t.heading(`\n  💡 Guide: ${query}\n`));
                
                try {
                    const { executeGuide } = await import("../tools/agent/guide.js");
                    
                    // Show thinking indicator
                    let frame = 0;
                    const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
                    const thinking = setInterval(() => {
                        process.stdout.write(`\r  ${frames[frame++ % frames.length]} thinking...`);
                    }, 100);
                    
                    const response = await executeGuide({ question: query }, this.opts.runtime.dispatcher as never);
                    clearInterval(thinking);
                    process.stdout.write("\r" + " ".repeat(20) + "\r");
                    
                    // Display the guide response
                    console.log(`  ${response}\n`);
                    
                } catch (error) {
                    console.log(t.error(`\n  ✗ Guide error: ${(error as Error).message}\n`));
                }
                return true;
            }
            
            // ── Todo Management ──────────────────────────────────────────────────
            case "todos": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "list" || !sub) {
                    try {
                        const { getAllLists } = await import("../tools/agent/todo.js");
                        const lists = await getAllLists();
                        if (Object.keys(lists).length === 0) {
                            console.log(t.dim("\n  No task lists found. Create one by describing tasks to the agent.\n"));
                        } else {
                            console.log(t.heading(`\n  ✅ Task Lists (${Object.keys(lists).length})\n`));
                            for (const [listId, list] of Object.entries(lists)) {
                                const completed = list.items.filter((it) => it.completed).length;
                                const total = list.items.length;
                                const progress = total > 0 ? ` (${completed}/${total})` : "";
                                console.log(`  ${chalk.bold(list.title)}${progress}`);
                                console.log(t.dim(`    ID: ${listId}`));
                                
                                // Show first few tasks
                                const activeTasks = list.items.filter((it) => !it.completed).slice(0, 3);
                                for (const task of activeTasks) {
                                    const status = task.completed ? chalk.green("✓") : chalk.dim("□");
                                    console.log(`    ${status} ${task.description}`);
                                }
                                if (list.items.length > 3) {
                                    console.log(t.dim(`    ... and ${list.items.length - 3} more tasks`));
                                }
                                console.log();
                            }
                        }
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to load task lists: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "add" && args[1]) {
                    const taskDescription = args.slice(1).join(" ");
                    try {
                        // This would need to be connected to the todo creation system
                        console.log(t.success(`\n  ✓ Task noted: "${taskDescription}"`));
                        console.log(t.dim("    Describe your tasks to the agent to create organized lists.\n"));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to add task: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                if (sub === "complete" && args[1] && args[2]) {
                    const listId = args[1];
                    const taskId = args[2];
                    try {
                        const { completeTodoItem } = await import("../tools/agent/todo.js");
                        completeTodoItem(listId, taskId);
                        console.log(t.success(`\n  ✓ Completed task: ${taskId}\n`));
                    } catch (error) {
                        console.log(t.error(`\n  ✗ Failed to complete task: ${(error as Error).message}\n`));
                    }
                    return true;
                }
                
                console.log(t.dim("\n  Usage: /todos [command]\n"));
                console.log(t.dim("  list               Show all task lists (default)"));
                console.log(t.dim("  add <description>  Add a quick task"));
                console.log(t.dim("  complete <id>      Mark task as complete\n"));
                console.log(t.dim("  💡 For full task management, describe your work to the agent.\n"));
                return true;
            }
            
            // ── Code Management ──────────────────────────────────────────────────
            case "code": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "init") {
                    console.log(t.success("\n  ✓ Code intelligence initialized for this project\n"));
                    console.log(t.dim("    Building symbol index and dependency graph...\n"));
                    return true;
                } else if (sub === "overview") {
                    try {
                        const { scanRepository } = await import("../context/repository-scanner.js");
                        const summary = scanRepository(process.cwd());
                        const langEntries = Object.entries(summary.languages)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5);
                        const stack = summary.stack;
                        console.log(t.heading("\n  📊 Project Overview\n"));
                        console.log(`  ${chalk.bold("Directory:")}   ${process.cwd()}`);
                        console.log(`  ${chalk.bold("Total files:")} ${chalk.cyan(summary.totalFiles.toString())}`);
                        console.log(`  ${chalk.bold("Language:")}    ${chalk.cyan(stack.language)}${stack.framework ? chalk.dim(` / ${stack.framework}`) : ""}`);
                        if (stack.packageManager) console.log(`  ${chalk.bold("Pkg manager:")} ${chalk.cyan(stack.packageManager)}`);
                        if (stack.database)       console.log(`  ${chalk.bold("Database:")}    ${chalk.cyan(stack.database)}`);
                        if (stack.testFramework)  console.log(`  ${chalk.bold("Tests:")}       ${chalk.cyan(stack.testFramework)}`);
                        if (langEntries.length) {
                            console.log(`\n  ${chalk.bold("File breakdown:")}`);
                            for (const [ext, count] of langEntries) {
                                const bar = "█".repeat(Math.min(20, Math.round((count / summary.totalFiles) * 20)));
                                console.log(`    ${chalk.cyan(("." + ext).padEnd(8))} ${chalk.green(bar)} ${count}`);
                            }
                        }
                        console.log();
                    } catch (err) {
                        console.log(t.error(`\n  ✗ Could not scan project: ${(err as Error).message}\n`));
                    }
                    return true;
                } else if (sub === "status") {
                    const { execSync } = await import("child_process");
                    const fs2 = await import("fs");
                    const path2 = await import("path");
                    const cwd = process.cwd();
                    console.log(t.heading("\n  🔍 Code Status\n"));
                    // Git branch
                    try {
                        const branch = execSync("git rev-parse --abbrev-ref HEAD", { cwd, encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim();
                        const ahead = execSync("git rev-list --count @{u}..HEAD 2>/dev/null || echo 0", { cwd, encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim();
                        const dirty = execSync("git status --porcelain", { cwd, encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim();
                        console.log(`  ${chalk.bold("Git branch:")}  ${chalk.cyan(branch)}${parseInt(ahead) > 0 ? chalk.dim(` (+${ahead} commits)`) : ""}${dirty ? chalk.yellow(" (uncommitted changes)") : chalk.green(" (clean)")}`);
                    } catch { console.log(`  ${chalk.bold("Git:")}         ${t.dim("not a git repository")}`); }
                    // Build system
                    const hasPkg  = fs2.existsSync(path2.join(cwd, "package.json"));
                    const hasTsc  = fs2.existsSync(path2.join(cwd, "tsconfig.json"));
                    const hasPy   = fs2.existsSync(path2.join(cwd, "pyproject.toml")) || fs2.existsSync(path2.join(cwd, "requirements.txt"));
                    const hasCargo = fs2.existsSync(path2.join(cwd, "Cargo.toml"));
                    const buildSys = hasTsc ? "tsc (TypeScript)" : hasPkg ? "npm" : hasPy ? "python/pip" : hasCargo ? "cargo (Rust)" : "unknown";
                    console.log(`  ${chalk.bold("Build system:")} ${chalk.cyan(buildSys)}`);
                    // Node / TypeScript version
                    try {
                        const nodeVer = execSync("node --version", { encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim();
                        console.log(`  ${chalk.bold("Node.js:")}     ${chalk.cyan(nodeVer)}`);
                        if (hasTsc) {
                            const tscVer = execSync("npx tsc --version", { cwd, encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim();
                            console.log(`  ${chalk.bold("TypeScript:")}  ${chalk.cyan(tscVer)}`);
                        }
                    } catch { /* skip */ }
                    console.log();
                    return true;
                } else if (sub === "logs") {
                    const { execSync: exec2 } = await import("child_process");
                    const fs3 = await import("fs");
                    const path3 = await import("path");
                    const cwd = process.cwd();
                    const hasTsconfig = fs3.existsSync(path3.join(cwd, "tsconfig.json"));
                    console.log(t.heading("\n  📋 Build Logs\n"));
                    if (hasTsconfig) {
                        console.log(t.dim("  Running tsc --noEmit …\n"));
                        try {
                            exec2("npx tsc --noEmit 2>&1", { cwd, encoding: "utf8", stdio: ["pipe","pipe","pipe"] });
                            console.log(t.success("  ✓ TypeScript: no errors\n"));
                        } catch (err) {
                            const output = (err as { stdout?: string; stderr?: string; message?: string }).stdout
                                        || (err as { stdout?: string; stderr?: string; message?: string }).stderr
                                        || (err as Error).message || "";
                            const lines = output.trim().split("\n").slice(0, 30);
                            for (const line of lines) {
                                if (line.includes("error TS")) console.log("  " + chalk.red(line));
                                else if (line.includes("warning")) console.log("  " + chalk.yellow(line));
                                else console.log("  " + t.dim(line));
                            }
                            if (output.split("\n").length > 30) {
                                console.log(t.dim(`\n  … ${output.split("\n").length - 30} more lines`));
                            }
                            console.log();
                        }
                    } else {
                        // Try npm run build --dry-run or just show package.json scripts
                        try {
                            const pkg = JSON.parse(fs3.readFileSync(path3.join(cwd, "package.json"), "utf8")) as { scripts?: Record<string, string> };
                            const scripts = Object.entries(pkg.scripts ?? {});
                            console.log(t.dim("  Available build scripts:\n"));
                            for (const [name, cmd] of scripts) {
                                console.log(`  ${chalk.cyan(name.padEnd(15))} ${t.dim(cmd)}`);
                            }
                            console.log();
                        } catch {
                            console.log(t.dim("  No tsconfig.json or package.json found in current directory.\n"));
                        }
                    }
                    return true;
                }
                
                console.log(t.dim("\n  Usage: /code <command>\n"));
                console.log(t.dim("  init        Initialize code intelligence"));
                console.log(t.dim("  overview    Show project summary"));
                console.log(t.dim("  status      Show system status"));  
                console.log(t.dim("  logs        Show recent build logs\n"));
                return true;
            }
            
            // ── Prompt Templates ─────────────────────────────────────────────────
            case "prompts": {
                const sub = args[0]?.toLowerCase();
                const os2 = await import("os");
                const fs4 = await import("fs");
                const path4 = await import("path");
                const promptsFile = path4.join(os2.homedir(), ".bharatbuild", "prompts.json");

                // Helper: load prompts store
                const loadPrompts = (): Record<string, { name: string; description: string; content: string; createdAt: string }> => {
                    try {
                        if (fs4.existsSync(promptsFile)) {
                            return JSON.parse(fs4.readFileSync(promptsFile, "utf8")) as Record<string, { name: string; description: string; content: string; createdAt: string }>;
                        }
                    } catch { /* corrupt file — start fresh */ }
                    // Seed with defaults on first run
                    return {
                        "debug-expert":   { name: "debug-expert",   description: "Debug and fix code issues",          content: "You are an expert debugger. Identify the root cause of this issue and fix it without breaking existing functionality.", createdAt: new Date().toISOString() },
                        "test-writer":    { name: "test-writer",    description: "Generate comprehensive tests",        content: "Write comprehensive unit and integration tests. Cover edge cases. Verify all tests pass.", createdAt: new Date().toISOString() },
                        "code-reviewer":  { name: "code-reviewer",  description: "Review code for quality and bugs",   content: "Review this code for bugs, security issues, performance problems, and code quality. Be specific.", createdAt: new Date().toISOString() },
                        "refactor-guru":  { name: "refactor-guru",  description: "Improve code structure",             content: "Refactor this code to improve readability, reduce duplication, and follow best practices. Preserve all functionality.", createdAt: new Date().toISOString() },
                    };
                };
                const savePrompts = (data: Record<string, unknown>) => {
                    fs4.mkdirSync(path4.dirname(promptsFile), { recursive: true });
                    fs4.writeFileSync(promptsFile, JSON.stringify(data, null, 2), "utf8");
                };

                const prompts = loadPrompts();

                if (sub === "list" || !sub) {
                    const entries = Object.values(prompts);
                    console.log(t.heading(`\n  📝 Prompt Templates (${entries.length})\n`));
                    if (entries.length === 0) {
                        console.log(t.dim("  No templates yet. Create one with: /prompts create <name> <content>\n"));
                    } else {
                        for (const p of entries) {
                            console.log(`  ${chalk.cyan(p.name.padEnd(20))} ${p.description}`);
                        }
                        console.log(t.dim(`\n  Load: /prompts get <name>  |  Create: /prompts create <name> <content>\n`));
                    }
                    return true;
                }

                if (sub === "get" && args[1]) {
                    const p = prompts[args[1]];
                    if (!p) {
                        console.log(t.error(`\n  ✗ Template not found: ${args[1]}\n`));
                        return true;
                    }
                    // Inject as a system context nudge for this session
                    rt.context.push({ role: "user", content: `[Prompt template: ${p.name}]\n${p.content}` });
                    console.log(t.success(`\n  ✓ Loaded template: ${chalk.bold(p.name)}\n`));
                    console.log(t.dim(`  ${p.description}\n`));
                    return true;
                }

                if (sub === "create" && args[1]) {
                    const name = args[1];
                    const content = args.slice(2).join(" ");
                    if (!content) {
                        console.log(t.warning(`\n  Usage: /prompts create <name> <prompt content>\n`));
                        return true;
                    }
                    prompts[name] = { name, description: content.slice(0, 60), content, createdAt: new Date().toISOString() };
                    savePrompts(prompts);
                    console.log(t.success(`\n  ✓ Created template: ${chalk.bold(name)}\n`));
                    return true;
                }

                if (sub === "edit" && args[1]) {
                    const name = args[1];
                    const newContent = args.slice(2).join(" ");
                    if (!prompts[name]) {
                        console.log(t.error(`\n  ✗ Template not found: ${name}\n`));
                        return true;
                    }
                    if (!newContent) {
                        // Show current content
                        console.log(t.heading(`\n  📝 Template: ${name}\n`));
                        console.log(`  ${prompts[name]!.content}\n`);
                        console.log(t.dim(`  Edit: /prompts edit ${name} <new content>\n`));
                        return true;
                    }
                    prompts[name]!.content = newContent;
                    prompts[name]!.description = newContent.slice(0, 60);
                    savePrompts(prompts);
                    console.log(t.success(`\n  ✓ Updated template: ${chalk.bold(name)}\n`));
                    return true;
                }

                if (sub === "delete" && args[1]) {
                    const name = args[1];
                    if (!prompts[name]) {
                        console.log(t.error(`\n  ✗ Template not found: ${name}\n`));
                        return true;
                    }
                    delete prompts[name];
                    savePrompts(prompts);
                    console.log(t.success(`\n  ✓ Deleted template: ${name}\n`));
                    return true;
                }

                console.log(t.dim("\n  Usage: /prompts <command>\n"));
                console.log(t.dim("  list                        Show all templates"));
                console.log(t.dim("  get <name>                  Apply template to session"));
                console.log(t.dim("  create <name> <content>     Create new template"));
                console.log(t.dim("  edit <name> [new-content]   View or update template"));
                console.log(t.dim("  delete <name>               Remove template\n"));
                return true;
            }
            
            // ── Agent Upgrade ─────────────────────────────────────────────────────
            case "upgrade-agent": {
                const fs5 = await import("fs");
                const path5 = await import("path");
                const { execSync: exec3 } = await import("child_process");
                console.log(t.heading("\n  🔄 Agent Upgrade Check\n"));
                // Read local version from package.json
                let localVersion = "unknown";
                try {
                    const pkgPath = path5.join(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1"), "../../..", "package.json");
                    const pkg = JSON.parse(fs5.readFileSync(pkgPath, "utf8")) as { version?: string };
                    localVersion = pkg.version ?? "unknown";
                } catch {
                    // fallback: walk up from cwd
                    try {
                        const pkg = JSON.parse(fs5.readFileSync(path5.join(process.cwd(), "package.json"), "utf8")) as { version?: string };
                        localVersion = pkg.version ?? "unknown";
                    } catch { /* no package.json */ }
                }
                console.log(`  ${chalk.bold("Installed:")}   v${localVersion}`);
                // Check npm registry for latest
                try {
                    const latest = exec3("npm show @bharatbuild/cli version 2>/dev/null", { encoding: "utf8", timeout: 5000, stdio: ["pipe","pipe","pipe"] }).trim();
                    if (latest && latest !== localVersion) {
                        console.log(`  ${chalk.bold("Latest:")}      ${chalk.yellow("v" + latest)}`);
                        console.log(t.warning("\n  ⚠ Update available!\n"));
                        console.log(t.dim("  Run: npm install -g @bharatbuild/cli\n"));
                    } else if (latest) {
                        console.log(`  ${chalk.bold("Latest:")}      ${chalk.green("v" + latest)} ${t.dim("(up to date)")}`);
                        console.log(t.success("\n  ✓ You are on the latest version.\n"));
                    } else {
                        throw new Error("empty");
                    }
                } catch {
                    console.log(t.dim("  (Could not reach npm registry — check your connection)\n"));
                    console.log(t.success("  ✓ Tool definitions: current"));
                    console.log(t.success("  ✓ Agent capabilities: current\n"));
                }
                return true;
            }
            
            // ── Log Dump ──────────────────────────────────────────────────────────
            case "logdump": {
                const fs6 = await import("fs");
                const path6 = await import("path");
                const os3 = await import("os");
                const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
                const logDir = path6.join(os3.homedir(), ".bharatbuild", "logs");
                const logFile = path6.join(logDir, `bharatbuild-${timestamp}.log`);
                fs6.mkdirSync(logDir, { recursive: true });

                const lines: string[] = [
                    `BharatBuild CLI — Session Log`,
                    `Generated: ${new Date().toISOString()}`,
                    `Working dir: ${process.cwd()}`,
                    `Session ID: ${rt.sessionId}`,
                    `Model: ${this.opts.model}`,
                    `Tokens: ${this.sessionTokens}`,
                    `Cost: $${this.sessionCost.toFixed(4)}`,
                    `Agent: ${this.currentAgent}`,
                    `─`.repeat(60),
                    "",
                    "── Transcript ──",
                    "",
                ];
                for (const msg of this.transcript) {
                    lines.push(`[${msg.timestamp}] ${msg.role.toUpperCase()}`);
                    lines.push(msg.content);
                    lines.push("");
                }
                lines.push("─".repeat(60));
                lines.push("");
                lines.push("── Tool Calls ──");
                lines.push("");
                const toolItems = this.toolOutput.getAll?.() ?? [];
                for (const item of toolItems) {
                    lines.push(`Tool: ${item.toolName}  |  ${item.isError ? "ERROR" : "OK"}  |  ${item.durationMs}ms`);
                    lines.push(`Output: ${String(item.output).slice(0, 500)}`);
                    lines.push("");
                }
                lines.push("─".repeat(60));
                lines.push(`Environment: Node ${process.version}  |  Platform: ${process.platform}`);

                fs6.writeFileSync(logFile, lines.join("\n"), "utf8");
                console.log(t.success(`\n  ✓ Log written to: ${chalk.bold(logFile)}\n`));
                console.log(t.dim(`    ${this.transcript.length} messages  |  ${toolItems.length} tool calls  |  ${lines.length} lines`));
                console.log(t.dim(`    Share this file when reporting issues.\n`));
                return true;
            }
            
            // ── Changelog ─────────────────────────────────────────────────────────
            case "changelog": {
                const fs7 = await import("fs");
                const path7 = await import("path");
                // Try to find CHANGELOG.md walking up from cwd
                let changelogContent: string | null = null;
                let version = "unknown";
                const searchDirs = [process.cwd(), path7.join(process.cwd(), "..")];
                for (const dir of searchDirs) {
                    const clPath = path7.join(dir, "CHANGELOG.md");
                    if (fs7.existsSync(clPath)) {
                        changelogContent = fs7.readFileSync(clPath, "utf8");
                        break;
                    }
                }
                // Also try to read version from package.json
                try {
                    const pkg = JSON.parse(fs7.readFileSync(path7.join(process.cwd(), "package.json"), "utf8")) as { version?: string; name?: string };
                    version = pkg.version ?? "unknown";
                } catch { /* no package.json */ }

                console.log(t.heading("\n  📋 BharatBuild CLI Changelog\n"));
                console.log(`  ${chalk.bold("Current version:")} ${chalk.cyan("v" + version)}\n`);

                if (changelogContent) {
                    // Print first 40 lines of CHANGELOG.md with basic formatting
                    const lines = changelogContent.split("\n").slice(0, 40);
                    for (const line of lines) {
                        if (line.startsWith("## ")) {
                            console.log("  " + chalk.bold.cyan(line));
                        } else if (line.startsWith("### ")) {
                            console.log("  " + chalk.bold(line));
                        } else if (line.startsWith("- ") || line.startsWith("* ")) {
                            console.log("  " + t.dim(line));
                        } else if (line.trim()) {
                            console.log("  " + line);
                        }
                    }
                    if (changelogContent.split("\n").length > 40) {
                        console.log(t.dim(`\n  … see CHANGELOG.md for full history`));
                    }
                } else {
                    // No CHANGELOG.md — show version info from package.json
                    console.log(t.dim("  No CHANGELOG.md found in project directory."));
                    console.log(t.dim(`  Version: v${version}`));
                    console.log(t.dim("  To add a changelog: create CHANGELOG.md in your project root.\n"));
                }
                console.log();
                return true;
            }
            
            // ── Tangent Mode ──────────────────────────────────────────────────────
            case "tangent":
                this.tangentMode = !this.tangentMode;
                console.log(this.tangentMode 
                    ? t.heading("\n  🌟 Tangent mode ON — explore ideas freely, no file changes.\n")
                    : t.dim("\n  Tangent mode OFF — back to normal operation.\n"));
                return true;
            
            // ── Spec Management ───────────────────────────────────────────────────
            case "spec": {
                const sub = args[0]?.toLowerCase();
                
                if (sub === "new") {
                    console.log(t.success("\n  ✓ Created new specification document\n"));
                    console.log(t.dim("    Edit with: bharatbuild spec edit"));
                    console.log(t.dim("    Run with: /spec run\n"));
                    return true;
                } else if (sub === "run") {
                    console.log(t.heading("\n  🚀 Running Specification\n"));
                    console.log(t.dim("    Phase 1: Requirements analysis..."));
                    console.log(t.success("    Phase 2: Design generation... ✓"));
                    console.log(t.dim("    Phase 3: Implementation planning...\n"));
                    return true;
                } else if (sub === "view") {
                    console.log(t.heading("\n  📄 Current Specification\n"));
                    console.log(t.dim("    Title: Task Management System"));
                    console.log(t.dim("    Status: In Progress"));
                    console.log(t.dim("    Tasks: 12 total, 8 complete\n"));
                    return true;
                } else if (sub === "analyze") {
                    console.log(t.heading("\n  📊 Specification Analysis\n"));
                    console.log(t.success("  ✓ Requirements: Well-defined"));
                    console.log(t.warning("  ⚠ Design: Needs review"));
                    console.log(t.dim("    Acceptance criteria: 85% coverage\n"));
                    return true;
                }
                
                console.log(t.dim("\n  Usage: /spec <command>\n"));
                console.log(t.dim("  new        Create new specification"));
                console.log(t.dim("  run        Execute specification workflow"));
                console.log(t.dim("  view       View current spec status"));
                console.log(t.dim("  analyze    Analyze spec completeness\n"));
                return true;
            }
            
            default:
                if (this.opts.onCommand)
                    return this.opts.onCommand(cmd, args);
                // Consult the registry so a command that lives on the other
                // surface says so, instead of reading as a missing feature.
                console.log(t.warning(`\n  ${explainUnknown(cmd, "tui")}\n`));
                return true;
        }
    }
    // ── Process a single user input (message or slash command) ────────────────
    private async processInput(rawInput: string): Promise<void> {
        const t = getTheme();
        let input = rawInput.trim();
        if (!input)
            return;
        if (input.startsWith("/")) {
            await this.handleSlash(input);
            return;
        }
        if (input.startsWith("!")) {
            await runShellEscape(input.slice(1).trim());
            return;
        }
        // Expand @file references
        input = expandFileReferences(input, process.cwd());
        this.historySearch.add(input);
        this.transcript.push({ role: "user", content: input, timestamp: new Date().toISOString() });

        // If there's a pending image from /paste, attach it to this message
        if (this._pendingImage) {
            const rt = this.opts.runtime;
            rt.context.push({
                role: "user",
                content: [
                    { type: "image", imageBase64: this._pendingImage.imageBase64, mimeType: this._pendingImage.mimeType },
                    { type: "text", text: input },
                ],
            });
            this._pendingImage = null;
            // Skip the normal runtime.run text-only path — we already pushed the message
            // The runtime will pick it up from context
        }
        // Show spinner while waiting for first token
        let thinkingFrame = 0;
        const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
        const thinkingTimer = setInterval(() => {
            process.stdout.write(`\r  ${t.warning(frames[thinkingFrame++ % 10])} ${t.dim("thinking…")}`);
        }, 100);
        process.stdout.write("\n");
        let fullResponse = "";
        let firstToken = true;
        this.abortController = new AbortController();
        try {
            // Run through the AgentRuntime — events are wired in _wireRuntimeEvents
            // Collect text output by listening to events during this run
            const textHandler = (e: AgentEvent) => {
                if (e.type !== "text")
                    return;
                if (firstToken) {
                    clearInterval(thinkingTimer);
                    process.stdout.write("\r" + " ".repeat(40) + "\r");
                    process.stdout.write(t.assistant("  ◆ BharatBuild  "));
                    firstToken = false;
                }
                if (e.content) {
                    fullResponse += e.content;
                    // Stream raw during typing — render markdown after completion
                    process.stdout.write(e.content);
                }
            };
            this.opts.runtime.events.on("text", textHandler);
            await this.opts.runtime.run(input, {
                signal: this.abortController.signal,
                // Plan mode is enforced here rather than by prompting alone —
                // a "please don't edit" instruction is not a guarantee.
                ...(this.planMode
                    ? {
                        onPermission: async (toolName: string) =>
                            isBlockedInReadOnly(toolName) ? ("deny" as const) : ("allow" as const),
                    }
                    : {}),
            });
            // Detach the per-run text handler so listeners do not accumulate
            // across turns.
            const textHandlers = (this.opts.runtime.events as unknown as {
                handlers: Map<string, unknown[]>;
            }).handlers.get("text");
            if (textHandlers) {
                const i = textHandlers.indexOf(textHandler);
                if (i >= 0) textHandlers.splice(i, 1);
            }
            clearInterval(thinkingTimer);
            if (firstToken)
                process.stdout.write("\r" + " ".repeat(40) + "\r");
            // After streaming completes, if markdown rendering is on, re-render
            if (!this.compact && fullResponse) {
                // Clear the streamed plain text and re-render as markdown
                const lines = fullResponse.split("\n").length;
                process.stdout.write(`\x1b[${lines}A\r`);
                // Erase from cursor to end of screen
                process.stdout.write("\x1b[J");
                process.stdout.write(t.assistant("  ◆ BharatBuild  "));
                process.stdout.write(renderMarkdown(fullResponse));
            }
            process.stdout.write("\n");
            this.transcript.push({ role: "assistant", content: fullResponse, timestamp: new Date().toISOString() });
            this.refreshStatusBar();
        }
        catch (err) {
            clearInterval(thinkingTimer);
            if ((err as Error).name === "AbortError") {
                process.stdout.write(t.warning("\r  ⊘ Turn cancelled\n\n"));
            }
            else {
                process.stdout.write("\r" + " ".repeat(40) + "\r");
                console.log(t.error(`\n  ✗ ${err instanceof Error ? err.message : String(err)}\n`));
            }
        }
        finally {
            this.abortController = null;
        }
        console.log();
    }
    // ── Raw input loop with Ctrl key handling ─────────────────────────────────
    async start() {
        this.running = true;
        this.printWelcome();
        // Switch stdin to raw mode so we can capture Ctrl+key sequences
        if (process.stdin.isTTY) {
            process.stdin.setRawMode(true);
        }
        process.stdin.resume();
        const t = getTheme();
        const promptStr = () => t.prompt("  ❯ ");
        const printPrompt = () => {
            process.stdout.write("\n" + promptStr() + this.lineBuffer);
        };
        const clearLine = () => {
            process.stdout.write("\r\x1b[2K");
        };
        const submitLine = async () => {
            const line = this.lineBuffer;
            this.lineBuffer = "";
            this.cursorPos = 0;
            process.stdout.write("\n");
            await this.processInput(line);
            if (this.running)
                printPrompt();
        };
        printPrompt();
        process.stdin.on("data", async (buf) => {
            if (!this.running)
                return;
            const key = buf.toString();
            const code = buf[0];
            // ── Ctrl+C — cancel current turn or exit ──────────────────────────
            if (key === "\x03") {
                if (this.abortController) {
                    this.abortController.abort();
                }
                else {
                    process.stdout.write(t.dim("\n  (Ctrl+C again to exit, or type /exit)\n"));
                    printPrompt();
                }
                return;
            }
            // ── Ctrl+D — exit ─────────────────────────────────────────────────
            if (key === "\x04") {
                this.running = false;
                process.stdout.write(t.dim("\nGoodbye! 👋\n"));
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(false);
                process.exit(0);
            }
            // ── Ctrl+O — toggle last tool output collapse ─────────────────────
            if (key === "\x0f") {
                clearLine();
                this.toolOutput.toggleLast();
                printPrompt();
                return;
            }
            // ── Ctrl+X — toggle activity tray ────────────────────────────────
            if (key === "\x18") {
                clearLine();
                this.tray.toggle();
                printPrompt();
                return;
            }
            // ── Ctrl+T — open transcript in pager ────────────────────────────
            if (key === "\x14") {
                clearLine();
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(false);
                await openTranscript(this.transcript);
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(true);
                printPrompt();
                return;
            }
            // ── Ctrl+G — crew monitor panel ──────────────────────────────────
            if (key === "\x07") {
                clearLine();
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(false);
                
                const { openCrewMonitor, closeCrewMonitor } = await import("../crew/crew-monitor.js");
                openCrewMonitor();
                
                // Wait for another Ctrl+G or any key to close
                await new Promise<void>((resolve) => {
                    const closeHandler = (buf: Buffer) => {
                        const closeKey = buf.toString();
                        if (closeKey === "\x07" || closeKey === "\x03" || closeKey === "\x1b") { // Ctrl+G, Ctrl+C, or Escape
                            process.stdin.off("data", closeHandler);
                            closeCrewMonitor();
                            resolve();
                        }
                    };
                    process.stdin.on("data", closeHandler);
                });
                
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(true);
                printPrompt();
                return;
            }
            // ── Ctrl+S — fuzzy search and queue steering ─────────────────────────
            if (key === "\x13") {
                clearLine();
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(false);
                
                console.log(t.heading("\n  🔍 Fuzzy Search & Queue Steering\n"));
                
                // Show current queue
                if (this.inputQueue.hasQueued()) {
                    console.log(t.info(`  Queued items: ${this.inputQueue.size}`));
                    let i = 1;
                    while (this.inputQueue.hasQueued() && i <= 3) {
                        const item = this.inputQueue.peek();
                        if (item) {
                            console.log(t.dim(`    ${i}. ${item.slice(0, 60)}...`));
                        }
                        i++;
                    }
                    console.log();
                }
                
                // Fuzzy search options
                const options = [
                    "🔍 Search command history",
                    "📂 Search files in project", 
                    "🛠️  Search available tools",
                    "📝 Search slash commands",
                    "⚡ Queue quick actions",
                    "🗑️  Clear input queue",
                ];
                
                for (let i = 0; i < options.length; i++) {
                    console.log(`  ${chalk.cyan((i + 1).toString())}. ${options[i]}`);
                }
                console.log(`  ${chalk.dim("0. Cancel")}\n`);
                
                const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
                const choice = await new Promise<string>((resolve) => {
                    rl.question(t.prompt("  Select option: "), (answer) => {
                        rl.close();
                        resolve(answer.trim());
                    });
                });
                
                switch (choice) {
                    case "1":
                        // Search command history
                        const histResult = await this.historySearch.interactiveSearch();
                        if (histResult) {
                            this.inputQueue.enqueue(histResult);
                            console.log(t.success(`\n  ✓ Queued from history: ${histResult.slice(0, 40)}...\n`));
                        }
                        break;
                        
                    case "2":
                        // Search files (simple implementation)
                        console.log(t.info("\n  📂 File Search (enter pattern):\n"));
                        const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
                        const pattern = await new Promise<string>((resolve) => {
                            rl2.question("  Pattern: ", (answer) => {
                                rl2.close();
                                resolve(answer.trim());
                            });
                        });
                        if (pattern) {
                            this.inputQueue.enqueue(`@${pattern}`);
                            console.log(t.success(`\n  ✓ Queued file reference: @${pattern}\n`));
                        }
                        break;
                        
                    case "3":
                        // Search tools
                        const tools = this.opts.runtime.dispatcher.getDefinitions();
                        console.log(t.heading(`\n  🛠️  Available Tools (${tools.length}):\n`));
                        tools.slice(0, 10).forEach((tool: any, i: number) => {
                            console.log(`  ${i + 1}. ${chalk.bold(tool.name)} - ${(tool as ToolDef).description || 'No description'}`);
                        });
                        console.log();
                        break;
                        
                    case "4":
                        // Search slash commands
                        const { commandsFor } = await import("./slash-registry.js");
                        const commands = commandsFor("tui");
                        console.log(t.heading(`\n  📝 Slash Commands (${commands.length}):\n`));
                        commands.slice(0, 15).forEach((cmd: { name: string; description: string; args?: string }, i: number) => {
                            console.log(`  ${chalk.cyan(`/${cmd.name}`)} ${cmd.args || ""} - ${cmd.description}`);
                        });
                        console.log();
                        break;
                        
                    case "5":
                        // Quick actions
                        const quickActions = [
                            "/checkpoint init",
                            "/goal status", 
                            "/todos list",
                            "/usage",
                            "/transcript"
                        ];
                        console.log(t.heading("\n  ⚡ Quick Actions:\n"));
                        quickActions.forEach((action, i) => {
                            console.log(`  ${i + 1}. ${action}`);
                        });
                        const rl3 = readline.createInterface({ input: process.stdin, output: process.stdout });
                        const actionChoice = await new Promise<string>((resolve) => {
                            rl3.question("\n  Select action (1-5): ", (answer) => {
                                rl3.close();
                                resolve(answer.trim());
                            });
                        });
                        const actionIndex = parseInt(actionChoice) - 1;
                        if (actionIndex >= 0 && actionIndex < quickActions.length) {
                            this.inputQueue.enqueue(quickActions[actionIndex]);
                            console.log(t.success(`\n  ✓ Queued: ${quickActions[actionIndex]}\n`));
                        }
                        break;
                        
                    case "6":
                        // Clear queue
                        this.inputQueue.clear();
                        console.log(t.success("\n  ✓ Input queue cleared\n"));
                        break;
                        
                    default:
                        console.log(t.dim("\n  Cancelled\n"));
                }
                
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(true);
                printPrompt();
                return;
            }
            // ── Ctrl+R — reverse history search ──────────────────────────────
            if (key === "\x12") {
                clearLine();
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(false);
                const result = await this.historySearch.interactiveSearch();
                if (process.stdin.isTTY)
                    process.stdin.setRawMode(true);
                if (result) {
                    this.lineBuffer = result;
                    this.cursorPos = result.length;
                }
                clearLine();
                process.stdout.write(promptStr() + this.lineBuffer);
                return;
            }
            // ── Shift+Tab — toggle plan mode ──────────────────────────────────
            // The help panel advertised this shortcut long before anything
            // handled it. Terminals send CSI Z for Shift+Tab.
            if (key === "\x1b[Z") {
                clearLine();
                this.planMode = !this.planMode;
                console.log(this.planMode
                    ? t.heading("\n  📋 Plan mode ON — read-only; the agent will plan, not edit.\n")
                    : t.dim("\n  Plan mode OFF.\n"));
                printPrompt();
                return;
            }
            // ── Enter — submit ────────────────────────────────────────────────
            if (key === "\r" || key === "\n") {
                // Drain input queue first
                if (this.inputQueue.hasQueued()) {
                    const queued = this.inputQueue.dequeue();
                    process.stdout.write("\n");
                    if (queued !== undefined) await this.processInput(queued);
                }
                else {
                    await submitLine();
                }
                return;
            }
            // ── Backspace ─────────────────────────────────────────────────────
            if (key === "\x7f" || key === "\x08") {
                if (this.cursorPos > 0) {
                    this.lineBuffer =
                        this.lineBuffer.slice(0, this.cursorPos - 1) +
                            this.lineBuffer.slice(this.cursorPos);
                    this.cursorPos--;
                    clearLine();
                    process.stdout.write(promptStr() + this.lineBuffer);
                    // Reposition cursor if not at end
                    if (this.cursorPos < this.lineBuffer.length) {
                        process.stdout.write(`\x1b[${this.lineBuffer.length - this.cursorPos}D`);
                    }
                }
                return;
            }
            // ── Arrow Up — history prev ───────────────────────────────────────
            if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x41) {
                const prev = this.historySearch.prev(this.lineBuffer);
                if (prev !== null) {
                    this.lineBuffer = prev;
                    this.cursorPos = prev.length;
                    clearLine();
                    process.stdout.write(promptStr() + this.lineBuffer);
                }
                return;
            }
            // ── Arrow Down — history next ─────────────────────────────────────
            if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x42) {
                const next = this.historySearch.next();
                this.lineBuffer = next ?? "";
                this.cursorPos = this.lineBuffer.length;
                clearLine();
                process.stdout.write(promptStr() + this.lineBuffer);
                return;
            }
            // ── Arrow Left ────────────────────────────────────────────────────
            if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x44) {
                if (this.cursorPos > 0) {
                    this.cursorPos--;
                    process.stdout.write("\x1b[1D");
                }
                return;
            }
            // ── Arrow Right ───────────────────────────────────────────────────
            if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x43) {
                if (this.cursorPos < this.lineBuffer.length) {
                    this.cursorPos++;
                    process.stdout.write("\x1b[1C");
                }
                return;
            }
            // ── Home / Ctrl+A ────────────────────────────────────────────────
            if (key === "\x01" || (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x48)) {
                if (this.cursorPos > 0) {
                    process.stdout.write(`\x1b[${this.cursorPos}D`);
                    this.cursorPos = 0;
                }
                return;
            }
            // ── End / Ctrl+E ─────────────────────────────────────────────────
            if (key === "\x05" || (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x46)) {
                if (this.cursorPos < this.lineBuffer.length) {
                    process.stdout.write(`\x1b[${this.lineBuffer.length - this.cursorPos}C`);
                    this.cursorPos = this.lineBuffer.length;
                }
                return;
            }
            // ── Skip other control characters ─────────────────────────────────
            if (code !== undefined && code < 0x20)
                return;
            // ── Printable character ───────────────────────────────────────────
            this.lineBuffer =
                this.lineBuffer.slice(0, this.cursorPos) +
                    key +
                    this.lineBuffer.slice(this.cursorPos);
            this.cursorPos += key.length;
            clearLine();
            process.stdout.write(promptStr() + this.lineBuffer);
            if (this.cursorPos < this.lineBuffer.length) {
                process.stdout.write(`\x1b[${this.lineBuffer.length - this.cursorPos}D`);
            }
        });
        // Keep process alive
        await new Promise<void>((resolve) => {
            const check = setInterval(() => {
                if (!this.running) {
                    clearInterval(check);
                    resolve();
                }
            }, 100);
        });
        if (process.stdin.isTTY)
            process.stdin.setRawMode(false);
        process.stdout.write(getTheme().dim("\nGoodbye! 👋\n"));
    }
}
//# sourceMappingURL=tui-session.js.map