/**
 * BharatBuild CLI - Guide Tool
 * Answers questions about the BharatBuild CLI itself.
 * The guide agent knows all commands, features, and configurations.
 */

import type { ModelClient } from "../../runtime/agent-loop.js";
import { MODEL_TIERS } from "../../config/constants.js";

// ── Tool Definition ────────────────────────────────────────────────────────

export const guideDefinition = {
  name: "guide",
  description:
    "Ask the BharatBuild CLI guide agent a question about the CLI's features, " +
    "commands, configuration, or capabilities. Use this when the user asks how " +
    "to use a CLI feature, what commands are available, or how to configure something.",
  input_schema: {
    type: "object",
    properties: {
      question: {
        type: "string",
        description: "The question about BharatBuild CLI features or usage.",
      },
    },
    required: ["question"],
  },
} as const;

// ── Guide knowledge ────────────────────────────────────────────────────────

const GUIDE_SYSTEM = `You are the BharatBuild CLI guide agent. You know everything about the CLI:

COMMANDS:
  bharatbuild                  Interactive REPL (default mode)
  bharatbuild chat [prompt]    Interactive chat with full tool use
  bharatbuild ask <question>   Single-shot question, no tools
  bharatbuild build [--fix]    Build project, optionally auto-fix errors
  bharatbuild test [--fix]     Run tests, optionally auto-fix failures
  bharatbuild fix [issue]      Fix build errors, test failures, or described issue
  bharatbuild plan <goal>      Generate implementation plan
  bharatbuild task <desc>      Run a task with full agent
  bharatbuild review [target]  Code review
  bharatbuild spec new <title> Generate requirements + design doc
  bharatbuild model [id]       Show or set AI model
  bharatbuild crew spawn       Multi-agent crew sessions
  bharatbuild agent list       Manage agent configs
  bharatbuild hooks            File watcher + git hooks
  bharatbuild mcp              Model Context Protocol servers
  bharatbuild settings         CLI settings management
  bharatbuild init             Initialize project
  bharatbuild login/logout     Authentication
  bharatbuild whoami           Account info

SLASH COMMANDS (inside chat/REPL):
  /help           Show all commands
  /model [id]     Show or switch AI model
  /mode <name>    Switch platform mode
  /reset          Clear conversation context
  /exit           Exit

MODELS:
  auto                       Best model selected per request (default)
  haiku | claude-haiku-4-5   Fast, cheap
  sonnet | claude-sonnet-5   Balanced
  opus | claude-opus-5       Most capable
  gpt-4o, gpt-4o-mini        OpenAI
  gemini-1.5-pro             Google
  ollama/llama3              Local

TOOLS AVAILABLE TO AGENT:
  read_file, write_file, list_files, find_files
  execute_command
  git_status, git_diff, git_log, git_add, git_commit
  search_code, search_files
  subagent, delegate, goal
  thinking, knowledge, todo_list, guide

CONFIGURATION:
  ~/.bharatbuild/config.json   User config
  .bharatbuild/steering.md     Project steering file (persona, rules, model)
  BHARATBUILD_API_URL          Backend URL env var
  BHARATBUILD_MODEL            Model env var
  ANTHROPIC_API_KEY            Direct Anthropic key (bypasses backend)
  OPENAI_API_KEY               Direct OpenAI key

Answer clearly and concisely. Be specific about exact command syntax.`;

// ── Tool executor ──────────────────────────────────────────────────────────

export interface GuideInput {
  question: string;
}

export async function* runGuideAgent(input: string, model: ModelClient): AsyncIterable<string> {
  for await (const chunk of model.complete({
    model: MODEL_TIERS.haiku,
    system: GUIDE_SYSTEM,
    messages: [{ role: "user", content: input }],
    tools: [],
    maxTokens: 1500,
  })) {
    if (chunk.type === "text_delta" && chunk.text) yield chunk.text;
  }
}

export async function executeGuide(
  input: GuideInput,
  model: ModelClient
): Promise<{ content: string; isError: boolean }> {
  if (!input.question?.trim()) {
    return { content: "Error: question is required", isError: true };
  }

  let answer = "";
  for await (const chunk of runGuideAgent(input.question, model)) {
    answer += chunk;
  }

  return {
    content: answer || "Guide agent returned no response.",
    isError: false,
  };
}