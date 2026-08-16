/**
 * BharatBuild CLI - Thinking Tool
 * Allows the agent to record its reasoning process (extended thinking).
 * Mirrors Kiro's thinking block support.
 */

// ── Tool Definition ────────────────────────────────────────────────────────

export const thinkingDefinition = {
  name: "thinking",
  description:
    "Record a structured thinking/reasoning block. Use this to think through " +
    "complex problems step by step before taking action. The reasoning is stored " +
    "and can be reviewed. This helps with multi-step planning, debugging, and " +
    "architectural decisions.",
  input_schema: {
    type: "object",
    properties: {
      reasoning: {
        type: "string",
        description: "Your step-by-step reasoning process. Think out loud here.",
      },
      conclusion: {
        type: "string",
        description: "The conclusion or decision reached after reasoning.",
      },
    },
    required: ["reasoning", "conclusion"],
  },
} as const;

// ── State ──────────────────────────────────────────────────────────────────

export interface ThinkingBlock {
  id: string;
  reasoning: string;
  conclusion: string;
  durationMs: number;
  timestamp: string;
}

const blocks: ThinkingBlock[] = [];

export function recordThinking(reasoning: string, conclusion: string, durationMs = 0): ThinkingBlock {
  const block: ThinkingBlock = {
    id: `think-${Date.now()}`,
    reasoning,
    conclusion,
    durationMs,
    timestamp: new Date().toISOString(),
  };
  blocks.push(block);
  return block;
}

export function getThinkingBlocks(): ThinkingBlock[] { return [...blocks]; }
export function clearThinking(): void { blocks.length = 0; }

// ── Tool executor ──────────────────────────────────────────────────────────

export interface ThinkingInput {
  reasoning: string;
  conclusion: string;
}

export function executeThinking(input: ThinkingInput): { content: string; isError: boolean } {
  if (!input.reasoning?.trim()) {
    return { content: "Error: reasoning is required", isError: true };
  }
  if (!input.conclusion?.trim()) {
    return { content: "Error: conclusion is required", isError: true };
  }

  const block = recordThinking(input.reasoning, input.conclusion);
  return {
    content: JSON.stringify({
      id: block.id,
      conclusion: block.conclusion,
      message: "Thinking recorded. Proceed with the conclusion.",
    }, null, 2),
    isError: false,
  };
}