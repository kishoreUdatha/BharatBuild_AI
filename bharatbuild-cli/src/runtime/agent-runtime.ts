// BharatBuild CLI - Agent Runtime
// Top-level orchestrator that wires all runtime components together.
// Includes: steering file, project context, auto model, compaction.

import { AgentLoop, AgentLoopOptions, ModelClient } from "./agent-loop.js";
import { ContextManager }    from "./context-manager.js";
import { ToolDispatcher }    from "./tool-dispatcher.js";
import { EventStream }       from "./event-stream.js";
import { CostMeter }         from "./cost-meter.js";
import { SessionManager }    from "./session-manager.js";
import { CLIConfig }         from "../config/config.js";
import { loadSteeringFile }  from "../spec/steering-file.js";
import { buildProjectContext } from "../context/project-context.js";
import { checkPermission }     from "../permissions/permission-manager.js";
import { discoverSkills, buildSkillsPrompt } from "../skills/index.js";
import { resolveModel } from "../config/constants.js";
import { createProxyClientIfLoggedIn, type ProxyModelClient } from "../api/proxy-model.js";

export interface RuntimeOptions {
  config:    CLIConfig;
  model:     ModelClient;
  sessionId?: string;
}

export class AgentRuntime {
  readonly events:     EventStream;
  readonly context:    ContextManager;
  readonly dispatcher: ToolDispatcher;
  readonly cost:       CostMeter;

  private _loop:        AgentLoop;
  private _session:     SessionManager;
  private _mcp?:        import("../mcp/mcp-client.js").MCPClient;
  private _config:      CLIConfig;
  private _sessionId:   string;
  private _abortController: AbortController | null = null;
  /** Proxy client when user is logged in — routes calls through BharatBuild backend */
  private _proxy:       ProxyModelClient | null = null;
  /** Server-reported credits remaining after last turn (-1 = unknown) */
  serverCreditsRemaining = -1;

  constructor(opts: RuntimeOptions) {
    this._config    = opts.config;
    this._session   = new SessionManager();
    this._sessionId = opts.sessionId ?? this._session.generateId();

    // Use proxy (server-side) when logged in — same as Kiro routing through Bedrock
    // Fall back to direct provider client when not authenticated
    this._proxy = createProxyClientIfLoggedIn();
    const activeModel = this._proxy ?? opts.model;

    this.events     = new EventStream();
    this.context    = new ContextManager();
    this.dispatcher = new ToolDispatcher(this.events, activeModel);
    this.cost       = new CostMeter(opts.config.model);

    this.context.setModelClient(activeModel as any, opts.config.model ?? "auto");

    this._loop = new AgentLoop(
      activeModel,
      this.context,
      this.dispatcher,
      this.events,
      this.cost,
    );

    this._setSystemPrompt();
  }

  /** True when routing through BharatBuild backend (user is logged in) */
  get isProxied(): boolean { return this._proxy !== null; }

  get sessionId(): string { return this._sessionId; }

  private _setSystemPrompt(): void {
    const parts: string[] = [
      "You are BharatBuild AI, an expert software engineer assistant.",
    ];

    // 1. Load steering file (project-level overrides)
    try {
      const steering = loadSteeringFile(this._config.workingDir);
      if (steering.persona) {
        parts.push(`\n## Persona\n${steering.persona.trim()}`);
      }
      if (steering.rules && steering.rules.length > 0) {
        parts.push(`\n## Rules\n${steering.rules.map((r) => `- ${r}`).join("\n")}`);
      }
    } catch {
      // Steering file is optional — ignore errors
    }

    // 2. Project context (language, framework, file count, etc.)
    try {
      const ctx = buildProjectContext(this._config.workingDir);
      if (ctx.systemPromptAddition) {
        parts.push(`\n## Project Context\n${ctx.systemPromptAddition}`);
      }
    } catch {
      // Fallback: just use working dir
      parts.push(`\nWorking directory: ${this._config.workingDir}`);
    }

    // 3. Active skills (auto-discovered from .bharatbuild/skills/)
    try {
      const skills = discoverSkills(this._config.workingDir);
      const skillsPrompt = buildSkillsPrompt(skills);
      if (skillsPrompt) parts.push(skillsPrompt);
    } catch {
      // Skills are optional
    }

    // 4. Standard tool guidance
    parts.push(
      "\nYou have access to tools for reading/writing files, running shell commands, " +
      "searching code, and managing git. Use them to complete tasks.\n" +
      "Always think step by step. Write production-quality code.\n" +
      "When fixing errors, show the root cause before the fix.\n" +
      "Use the todo_list tool for multi-step tasks. Use the thinking tool for complex reasoning.\n" +
      "Use subagent or delegate to hand off specialist subtasks."
    );

    this.context.setSystemPrompt(parts.join("\n"));
  }

  /**
   * Connect configured MCP servers and expose their tools to the agent.
   *
   * Best-effort and idempotent: a server that fails to start is reported and
   * skipped rather than failing the session. Safe to call when none are
   * configured - it becomes a no-op.
   */
  async initMCP(): Promise<void> {
    if (this._mcp) return;
    try {
      const { MCPClient } = await import("../mcp/mcp-client.js");
      const mcp = new MCPClient();
      const result = await mcp.initialize(this._config.workingDir);

      if (result.started.length === 0 && result.failed.length === 0) return; // none configured

      this._mcp = mcp;
      this.dispatcher.setMCPClient(mcp);

      for (const f of result.failed) {
        await this.events.emit(EventStream.error(`MCP server "${f.name}" unavailable: ${f.error}`, false));
      }
      if (result.toolCount > 0) {
        await this.events.emit(EventStream.status(
          `${result.toolCount} MCP tool(s) from ${result.started.length} server(s)`, "thinking",
        ));
      }
    } catch (err) {
      await this.events.emit(EventStream.error(
        `MCP initialization failed: ${err instanceof Error ? err.message : String(err)}`, false,
      ));
    }
  }

  /** Connected MCP client, or undefined when none are configured. */
  get mcp(): import("../mcp/mcp-client.js").MCPClient | undefined {
    return this._mcp;
  }

  /** Shut down MCP servers. Call when the session ends. */
  async closeMCP(): Promise<void> {
    await this._mcp?.close().catch(() => {});
    this._mcp = undefined;
  }

  async run(
    userMessage: string,
    opts?: Partial<AgentLoopOptions> & {
      onPermission?: AgentLoopOptions["onPermission"];
    },
  ): Promise<void> {
    this._abortController = new AbortController();
    await this.initMCP();

    // Default permission handler — uses permission-manager policy
    const defaultOnPermission = async (toolName: string, input: Record<string, unknown>) => {
      // Pass the session config so permissionMode/nonInteractive are honored;
      // checkPermission would otherwise re-read config from disk.
      return checkPermission(toolName, input, this._config);
    };

    await this._loop.run(userMessage, {
      model:        resolveModel(this._config.model),
      maxTurns:     this._config.maxTurns,
      signal:       this._abortController.signal,
      onPermission: opts?.onPermission ?? defaultOnPermission,
      ...opts,
    });

    // If proxied — pick up server-authoritative credit balance from last turn
    if (this._proxy) {
      this.serverCreditsRemaining = this._proxy.lastCreditsRemaining;
    }

    // auto-save session
    this._session.save(this._sessionId, {
      title:        userMessage.slice(0, 60),
      model:        this._config.model,
      createdAt:    Date.now(),
      updatedAt:    Date.now(),
      messageCount: this.context.messages.length,
      workingDir:   this._config.workingDir,
    }, this.context);
  }

  cancel(): void {
    this._abortController?.abort();
  }

  resume(sessionId: string): boolean {
    const saved = this._session.load(sessionId);
    if (!saved) return false;
    this._sessionId = sessionId;
    this.context.clear();
    this.context.pushAll(saved.context.messages);
    this.context.setSystemPrompt((saved.context as any).systemPrompt ?? "");
    return true;
  }

  reset(): void {
    this.context.clear();
    this.cost.reset();
    this._sessionId = this._session.generateId();
    this._setSystemPrompt();
  }
}