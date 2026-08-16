/**
 * BharatBuild CLI — Built-in Tool: goal
 * Signal goal completion. A goal is a binding completion contract.
 * The system will continue re-prompting until the contract is satisfied.
 */

import type { BuiltInTool, ToolResult } from "./types.js";

export const goalTool: BuiltInTool = {
  definition: {
    name: "goal",
    source: "built-in",
    status: "approval_required",
    description: "Signal goal completion. A goal is a binding completion contract — the system will continue re-prompting until the contract is satisfied.",
    parameters: {
      type: "object",
      properties: {
        command: {
          type: "string",
          enum: ["complete", "status"],
          description: "The goal action to perform: 'complete' to certify all criteria met, 'status' to check progress.",
        },
        summary: {
          type: "string",
          description: "Brief summary of what was accomplished and how it was verified (required for 'complete').",
        },
      },
      required: ["command"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const command = params["command"] as string;

    switch (command) {
      case "complete":
        return completeGoal(params);
      case "status":
        return goalStatus();
      default:
        return { content: `Unknown command: ${command}`, isError: true };
    }
  },
};

// ── State ──────────────────────────────────────────────────────────────────

interface GoalState {
  id: string;
  status: "running" | "complete";
  summary?: string;
  completedAt?: string;
  createdAt: string;
}

const goals: GoalState[] = [];
let activeGoal: GoalState | null = null;

export function setActiveGoal(description?: string): GoalState {
  const goal: GoalState = {
    id: `goal-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    status: "running",
    createdAt: new Date().toISOString(),
  };
  goals.push(goal);
  activeGoal = goal;
  return goal;
}

export function getActiveGoal(): GoalState | null {
  return activeGoal;
}

function completeGoal(params: Record<string, unknown>): ToolResult {
  const summary = params["summary"] as string;

  if (!summary) {
    return { content: "Error: 'summary' is required for complete — cite the evidence.", isError: true };
  }

  if (activeGoal) {
    activeGoal.status = "complete";
    activeGoal.summary = summary;
    activeGoal.completedAt = new Date().toISOString();
  }

  return {
    content: JSON.stringify({
      command: "complete",
      status: "complete",
      summary,
      message: "Goal marked complete. All success criteria satisfied.",
    }, null, 2),
    isError: false,
  };
}

function goalStatus(): ToolResult {
  if (!activeGoal) {
    return { content: "No active goal.", isError: false };
  }

  return {
    content: JSON.stringify({
      id: activeGoal.id,
      status: activeGoal.status,
      summary: activeGoal.summary,
      created_at: activeGoal.createdAt,
      completed_at: activeGoal.completedAt,
    }, null, 2),
    isError: false,
  };
}
