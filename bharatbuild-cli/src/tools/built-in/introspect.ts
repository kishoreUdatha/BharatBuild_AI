/**
 * BharatBuild CLI — Built-in Tool: introspect
 * Look up documentation about this chat application's own features,
 * slash commands, settings, or capabilities.
 */

import type { BuiltInTool, ToolResult } from "./types.js";

export const introspectTool: BuiltInTool = {
  definition: {
    name: "introspect",
    source: "built-in",
    status: "approval_required",
    description: "Look up documentation about this chat application's own features, slash commands, settings, or capabilities.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The user's question about this assistant's usage, features, or capabilities.",
        },
        doc_path: {
          type: "string",
          description: "Path to a specific doc to retrieve (e.g., 'features/tangent-mode.md').",
        },
      },
      required: [],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const query = params["query"] as string | undefined;
    const docPath = params["doc_path"] as string | undefined;

    if (docPath) {
      return lookupDoc(docPath);
    }

    if (query) {
      return searchDocs(query);
    }

    // The schema marks both arguments optional, so a bare call is valid and
    // must not come back as an error. List what can be asked about instead -
    // that is the useful answer to "introspect" with no question, and it lets
    // the model pick a doc_path on the next turn rather than guessing.
    return {
      content: `Available documentation topics:\n${Object.keys(DOCS).map((k) => `  - ${k}`).join("\n")}\n\nCall again with doc_path=<topic> to read one, or query=<text> to search.`,
      isError: false,
    };
  },
};

// ── Documentation knowledge base ───────────────────────────────────────────

const DOCS: Record<string, string> = {
  "commands": `# BharatBuild CLI Commands

## Chat Commands
  bharatbuild chat [prompt]    Interactive chat with full tool use
  bharatbuild ask <question>   Single-shot question, no tools

## Development Commands
  bharatbuild build [--fix]    Build project, optionally auto-fix errors
  bharatbuild test [--fix]     Run tests, optionally auto-fix failures
  bharatbuild fix [issue]      Fix build errors, test failures, or described issue
  bharatbuild plan <goal>      Generate implementation plan
  bharatbuild task <desc>      Run a task with full agent
  bharatbuild review [target]  Code review
  bharatbuild init             Initialize project

## Spec & Planning
  bharatbuild spec new <title> Generate requirements + design doc

## Model Management
  bharatbuild model [id]       Show or set AI model

## Agent & Crew
  bharatbuild crew spawn       Multi-agent crew sessions
  bharatbuild agent list       Manage agent configs

## Settings & Auth
  bharatbuild settings         CLI settings management
  bharatbuild login/logout     Authentication
  bharatbuild whoami           Account info
  bharatbuild doctor           Environment diagnostics`,

  "slash-commands": `# Slash Commands (inside chat/REPL)

  /help           Show all commands
  /model [id]     Show or switch AI model
  /mode <name>    Switch platform mode (student, developer, founder, college, api-partner)
  /tools          Show available tools and their approval status
  /reset          Clear conversation context
  /compact        Compact conversation history
  /exit           Exit

## Mode Shortcuts
  /mode student       Switch to student mode
  /mode developer     Switch to developer mode
  /mode founder       Switch to founder mode`,

  "models": `# Available Models

## Auto Mode (Default)
  Model: auto — Best model selected dynamically per request

## Anthropic Claude
  haiku | claude-haiku-4-5      Fast, cheap
  sonnet | claude-sonnet-5      Balanced (default working tier)
  opus | claude-opus-5          Most capable

## OpenAI GPT-5.6
  gpt56sol      Hardest multi-step
  gpt56terra    Balanced agentic
  gpt56luna     Cheapest GPT

## Budget Models
  deepseek-3.2          128K context
  minimax-m2.5          200K, near-Opus quality
  qwen3-coder-next      256K, cheapest`,

  "tools": `# Built-in Tools (14)

All tools require approval before execution.

| Tool          | Description                                        |
|---------------|----------------------------------------------------|
| read          | Read files, directories, and images                |
| write         | Create and edit text files                          |
| glob          | Find files matching glob patterns                  |
| grep          | Regex text search in files                         |
| shell         | Execute shell commands                             |
| code          | Code intelligence, AST parsing, symbol search      |
| web_fetch     | Fetch content from URLs                            |
| web_search    | Search the web for information                     |
| knowledge     | Index and search content across sessions           |
| subagent      | Spawn and coordinate AI agents                     |
| todo_list     | Task list management                               |
| goal          | Signal goal completion                             |
| introspect    | Look up CLI documentation                          |
| use_aws       | Make AWS CLI API calls                             |`,

  "settings": `# Configuration

## Config File
  ~/.bharatbuild/config.json

## Environment Variables
  BHARATBUILD_API_URL          Backend URL
  BHARATBUILD_MODEL            Default model
  BHARATBUILD_TOKEN            Auth token
  ANTHROPIC_API_KEY            Direct Anthropic access
  OPENAI_API_KEY               Direct OpenAI access
  BRAVE_SEARCH_API_KEY         Web search API key

## Permission Modes
  auto     — Auto-approve safe operations, ask for risky ones
  ask      — Always ask for approval
  allow    — Allow all (caution: dangerous)`,

  "features": `# BharatBuild CLI Features

## Platform Modes
  🎓 Student Mode     — Academic project generation
  💻 Developer Mode   — AI code generation
  🚀 Founder Mode     — Startup tools
  🏫 College Mode     — Admin dashboard
  🔌 API Partner Mode — API key management

## Agent Capabilities
  - Multi-turn chat with context
  - File read/write with approval
  - Shell command execution
  - Code intelligence and symbol search
  - Web search and fetch
  - Multi-agent pipelines (crew/subagent)
  - Task tracking
  - Knowledge base (persistent across sessions)
  - Git operations`,
};

function searchDocs(query: string): ToolResult {
  const lower = query.toLowerCase();
  const results: string[] = [];

  for (const [key, doc] of Object.entries(DOCS)) {
    if (key.includes(lower) || doc.toLowerCase().includes(lower)) {
      // Extract relevant section
      const lines = doc.split("\n");
      const matchingLines: string[] = [];
      for (let i = 0; i < lines.length; i++) {
        if (lines[i]!.toLowerCase().includes(lower)) {
          const start = Math.max(0, i - 2);
          const end = Math.min(lines.length, i + 5);
          matchingLines.push(...lines.slice(start, end));
          matchingLines.push("...");
        }
      }
      if (matchingLines.length > 0) {
        results.push(`[${key}]\n${matchingLines.join("\n")}`);
      } else {
        results.push(`[${key}]\n${doc.slice(0, 300)}...`);
      }
    }
  }

  if (results.length === 0) {
    return { content: `No documentation found for: "${query}". Try: commands, slash-commands, models, tools, settings, features.`, isError: false };
  }

  return { content: results.join("\n\n---\n\n"), isError: false };
}

function lookupDoc(docPath: string): ToolResult {
  const key = docPath.replace(/\.md$/, "").replace(/^features\//, "").replace(/\//g, "-");
  const doc = DOCS[key];
  if (doc) return { content: doc, isError: false };

  // Try fuzzy match
  const lower = key.toLowerCase();
  for (const [k, v] of Object.entries(DOCS)) {
    if (k.includes(lower) || lower.includes(k)) {
      return { content: v, isError: false };
    }
  }

  return { content: `Documentation not found: ${docPath}. Available: ${Object.keys(DOCS).join(", ")}`, isError: true };
}
