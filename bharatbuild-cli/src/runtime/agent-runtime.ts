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
import { gitContextSummary } from "../context/git-context.js";
import { createProxyClientIfLoggedIn, type ProxyModelClient } from "../api/proxy-model.js";
import { getShellConfiguration, describeShell } from "../tools/shell/shell-config.js";

/**
 * How to decide — as opposed to what tools exist.
 *
 * The prompt used to be an inventory: "you have tools for reading/writing
 * files… use them to complete tasks", plus a few style notes. That tells the
 * model what it *can* do and nothing about what it *should* do, so it fell
 * back on ordinary conversational manners — describing a plan and waiting for
 * approval, answering from a filename instead of opening the file, and calling
 * a change done without running anything.
 *
 * None of that was a missing capability. The loop already runs up to MAX_TURNS
 * and the tools already work; what was missing was a policy for using them.
 * Each paragraph below exists because its absence produced a specific failure.
 */
const WORKING_PROCEDURE = `
## How to work

Act on the request rather than describing what you would do. If you can find
something out or make a change yourself, do it — do not stop to announce a plan
and wait for approval. Ask only when the request is genuinely ambiguous between
two different deliverables, or when a choice is hard to undo and you cannot
determine the answer from the code.

Look before you answer. Read the file, run the search, check the value. Never
state what a file contains, whether a test passes, or how an API behaves based
on its name or on what is usually true — open it and see. A confident wrong
answer costs far more than the seconds spent checking.

Work the way this codebase already works. Before writing anything, read a
neighbouring file and match what you find: its naming, its structure, its error
handling, how its tests are written. Never import a library without first
confirming it is already a dependency here.

When a fork is open and the answer changes the work, use ask_user rather than
guessing or writing a paragraph of alternatives — it returns a choice you do
not have to parse. Only for a fork you cannot settle yourself: not for
permission, not to check in on work already agreed, and not for something the
code would tell you.

End by naming the judgement call you made. Every task hides a fork the request
did not settle — the language, where the file went, a behaviour you inherited
from the surrounding code. Close with one line saying which way you went and
what the alternative is: "I assumed Python since you didn't say; say the word
for Java." or "Like the function beside it this collapses whitespace, so
\"a  b\" reverses to \"b a\" — tell me if you need the spacing preserved."
A choice made silently is one nobody can correct, and it is usually discovered
much later. One line, one real alternative, about a fork that genuinely
existed — not a menu of things you could do next.

Verify what you changed. After editing, run the project's type-check, tests or
build and read the output. "Done" means you checked, not that you wrote
something. If a check fails, fix it and run it again — do not hand back failing
work as though it were finished.

Prefer an experiment to an inference. When you can check a belief by running
something — call the function, hit the endpoint, set the variable and re-run —
do that instead of reasoning from the source. Reading the code tells you what
it should do; running it tells you what it does, and the gap between those two
is where the bug usually is.

Test the edges, not just the happy path. A single test proving a function runs
is not coverage. When you add or change behaviour, cover the ordinary case, the
boundaries — zero, empty, the limit itself, one past it — and each error it is
meant to raise. Match the depth of the tests already in the file.

Spend as few steps as the work allows. Ask for everything you need at once:
independent reads and searches can go in a single step, and they run
concurrently. Do not re-read a file you have already read, repeat a check whose
inputs have not changed, or explore past what the question needs. Once you have
the answer, stop — another tool call that cannot change your conclusion is
waste, and it is slower and more expensive for the person waiting.

Do what was asked, and all of it. Do not add features, files or abstractions
nobody asked for. If part of the task turns out to be blocked, complete
everything else and say plainly what you left and why, rather than quietly
narrowing the job.

Report what actually happened. If a test fails, say so and show the output. If
you skipped a step, say that. Never claim a result you did not observe.

`.trim();

/** Which tool to reach for, and the traps in the ones that need explaining. */
/** The shell execute_command actually invokes, named so nothing has to guess. */
const SHELL_NAME = describeShell(getShellConfiguration());

const TOOL_GUIDANCE = `
## Tools

Prefer glob and grep to guess at where something lives, and read_file before
editing. Use todo_list to track a multi-step task, thinking for reasoning you
need to work through, and subagent or delegate for a self-contained subtask.

To run an app or a dev server, use execute_command with background:true, then
call read_process_output once it has had a moment to start. A server often
prints "ready" and then fails, and nothing will tell you — reading its output is
the only way to know it is actually up. Check again after a change that should
trigger a reload, and stop_process when it is no longer needed.

Prefer editing an existing file to creating a new one, and do not create
documentation files unless they were asked for.

For a .ipynb, use read_notebook and edit_notebook rather than read_file and
apply_patch. A notebook is JSON: read_file returns metadata and base64 image
data with the code buried inside it, and patching that JSON by hand corrupts
the file as soon as one quote is mismatched.

Shell commands run through ${SHELL_NAME}, and execute_command takes a
working_dir argument. Use it rather than prefixing a directory change,
which is spelled differently on each platform and fails silently on some.
Nothing about the shell needs discovering: five calls were once spent
probing for it before any real work began.
`.trim();

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
  private _modelClient!: RuntimeOptions["model"];
  /** Server-reported credits remaining after last turn (-1 = unknown) */
  serverCreditsRemaining = -1;

  /**
   * The model that actually served the last turn, which is not always the one
   * asked for. The backend's local profile deliberately routes sonnet and opus
   * to haiku to save cost, and that substitution was invisible: the status bar
   * kept showing "sonnet" while haiku answered.
   */
  servedModel: string | null = null;

  /**
   * Change what tools are allowed for the rest of the session.
   *
   * Needed so a read-only agent is actually read-only. The registry has always
   * carried `readOnly: true` for the Planner, but the only code that read it
   * printed a "[read-only]" badge — selecting the agent left it free to write,
   * which it did.
   */
  setPermissionMode(mode: CLIConfig["permissionMode"]): void {
    this._config = { ...this._config, permissionMode: mode };
  }

  /** The mode currently in force. */
  get permissionMode(): CLIConfig["permissionMode"] {
    return this._config.permissionMode;
  }

  constructor(opts: RuntimeOptions) {
    this._config    = opts.config;
    this._session   = new SessionManager();
    this._sessionId = opts.sessionId ?? this._session.generateId();

    // Use proxy (server-side) when logged in — same as Kiro routing through Bedrock
    // Fall back to direct provider client when not authenticated
    this._proxy = createProxyClientIfLoggedIn();
    const activeModel = this._proxy ?? opts.model;
    this._modelClient = activeModel;

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

  /** The client the loop actually talks to (proxy when logged in). */
  get modelClient(): RuntimeOptions["model"] { return this._modelClient; }

  /** Session store, so UIs can list/rename sessions without their own instance. */
  get sessions(): SessionManager { return this._session; }

  /**
   * Everything except git state. buildProjectContext() walks the repo, so it
   * is computed once; git status is cheap and is refreshed per user turn
   * because the agent itself keeps changing the working tree.
   */
  private _staticPromptParts: string[] | null = null;

  /** The selected agent's role text, kept separate from the standard parts. */
  private _agentRole: string | null = null;

  /**
   * Adopt an agent's role while keeping the rest of the system prompt.
   *
   * Agent selection used to call context.setSystemPrompt directly, which
   * *replaces* the prompt — so choosing an agent silently deleted the
   * guidance naming todo_list, subagent, delegate and thinking, along with
   * "think step by step" and "show the root cause before the fix". The
   * agent then behaved as though those tools did not exist.
   */
  setAgentRole(role: string): void {
    this._agentRole = role;
    this._setSystemPrompt();
  }

  private _setSystemPrompt(): void {
    if (this._staticPromptParts) {
      this.context.setSystemPrompt(this._composePrompt(this._staticPromptParts));
      return;
    }

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

    // 4. How to work, then what with.
    // Leading newline per section, matching how Persona and Rules are pushed.
    parts.push(`
${WORKING_PROCEDURE}`, `
${TOOL_GUIDANCE}`);

    this._staticPromptParts = parts;
    this.context.setSystemPrompt(this._composePrompt(parts));
  }

  /** Static parts plus a freshly-read git summary. */
  private _composePrompt(parts: string[]): string {
    // The role goes first: it is the most specific instruction, and the
    // standard tool guidance below it still applies whichever agent is on.
    const all = this._agentRole ? [this._agentRole, ...parts] : [...parts];
    try {
      const git = gitContextSummary(this._config.workingDir);
      if (git) all.push(`\n## Git\n${git}`);
    } catch {
      // Git context is a nicety; it must never stop a turn.
    }
    return all.join("\n");
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
    // The working tree moves as the agent edits, so re-read git state for
    // each user turn rather than reusing the snapshot from session start.
    this._setSystemPrompt();
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
      this.servedModel = this._proxy.lastModelUsed || null;
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