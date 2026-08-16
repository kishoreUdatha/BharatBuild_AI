/**
 * BharatBuild CLI - Goal Tool
 *
 * Provides the `goal` tool that lets the agent declare a completion goal,
 * track progress across iterations, and signal when all acceptance criteria
 * have been met. Mirrors Kiro's goal/completion contract pattern.
 *
 * The agent calls `goal` with command "complete" when it has verified that
 * all success criteria in its task are satisfied.
 */

// ── Tool Definition ────────────────────────────────────────────────────────

export const goalDefinition = {
  name: "goal",
  description:
    "Manage task completion goals. Use this to:\n" +
    "  - 'create': Declare acceptance criteria for a task at the start\n" +
    "  - 'verify': Record a verification result for an iteration\n" +
    "  - 'complete': Signal that ALL acceptance criteria have been met (verified by evidence)\n" +
    "  - 'status': Check the current status of a goal\n" +
    "Never call 'complete' without first verifying each criterion with concrete evidence.",
  input_schema: {
    type: "object",
    properties: {
      command: {
        type: "string",
        enum: ["create", "verify", "complete", "status"],
        description: "The goal operation to perform.",
      },
      goal_id: {
        type: "string",
        description: "Goal ID (required for verify, complete, status). Returned by create.",
      },
      description: {
        type: "string",
        description: "Task description (required for create).",
      },
      criteria: {
        type: "array",
        items: { type: "string" },
        description: "List of acceptance criteria strings (required for create).",
      },
      passed: {
        type: "boolean",
        description: "Whether this verification iteration passed (required for verify).",
      },
      notes: {
        type: "string",
        description: "Evidence or notes for this verification (required for verify).",
      },
      summary: {
        type: "string",
        description: "Summary of what was accomplished and verified (required for complete).",
      },
      max_iterations: {
        type: "number",
        description: "Max retry iterations before the goal is marked failed (default: 5).",
      },
    },
    required: ["command"],
  },
} as const;

// ── Goal state ─────────────────────────────────────────────────────────────

export interface GoalState {
  id: string;
  description: string;
  acceptanceCriteria: string[];
  iteration: number;
  maxIterations: number;
  status: "running" | "complete" | "failed";
  verificationResults: Array<{ iteration: number; passed: boolean; notes: string }>;
  completedSummary?: string;
  createdAt: string;
  updatedAt: string;
}

const goals = new Map<string, GoalState>();

export function createGoal(description: string, criteria: string[], maxIterations = 5): GoalState {
  const g: GoalState = {
    id: `goal-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    description,
    acceptanceCriteria: criteria,
    iteration: 0,
    maxIterations,
    status: "running",
    verificationResults: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  goals.set(g.id, g);
  return g;
}

export function updateGoal(id: string, update: Partial<GoalState>): GoalState | null {
  const g = goals.get(id);
  if (!g) return null;
  Object.assign(g, update, { updatedAt: new Date().toISOString() });
  return g;
}

export function verifyGoal(id: string, passed: boolean, notes: string): GoalState | null {
  const g = goals.get(id);
  if (!g) return null;
  g.verificationResults.push({ iteration: g.iteration, passed, notes });
  g.iteration++;
  g.updatedAt = new Date().toISOString();
  if (passed) g.status = "complete";
  else if (g.iteration >= g.maxIterations) g.status = "failed";
  return g;
}

export function getGoal(id: string) { return goals.get(id); }
export function listGoals() { return Array.from(goals.values()); }

// ── Tool executor ──────────────────────────────────────────────────────────

export interface GoalInput {
  command: "create" | "verify" | "complete" | "status";
  goal_id?: string;
  description?: string;
  criteria?: string[];
  passed?: boolean;
  notes?: string;
  summary?: string;
  max_iterations?: number;
}

export function executeGoal(input: GoalInput): { content: string; isError: boolean } {
  const { command, goal_id } = input;

  switch (command) {
    case "create": {
      if (!input.description) {
        return { content: "Error: description is required for create", isError: true };
      }
      if (!input.criteria || input.criteria.length === 0) {
        return { content: "Error: criteria array is required for create", isError: true };
      }
      const goal = createGoal(input.description, input.criteria, input.max_iterations);
      return {
        content: JSON.stringify({
          goal_id: goal.id,
          status: goal.status,
          message: `Goal created with ${goal.acceptanceCriteria.length} acceptance criteria.`,
          criteria: goal.acceptanceCriteria,
        }, null, 2),
        isError: false,
      };
    }

    case "verify": {
      if (!goal_id) return { content: "Error: goal_id is required for verify", isError: true };
      if (input.passed === undefined) return { content: "Error: passed is required for verify", isError: true };
      if (!input.notes) return { content: "Error: notes (evidence) is required for verify", isError: true };

      const goal = verifyGoal(goal_id, input.passed, input.notes);
      if (!goal) return { content: `Error: goal ${goal_id} not found`, isError: true };

      return {
        content: JSON.stringify({
          goal_id: goal.id,
          status: goal.status,
          iteration: goal.iteration,
          max_iterations: goal.maxIterations,
          verification_result: { passed: input.passed, notes: input.notes },
          all_verifications: goal.verificationResults,
        }, null, 2),
        isError: false,
      };
    }

    case "complete": {
      if (!goal_id) return { content: "Error: goal_id is required for complete", isError: true };
      if (!input.summary) return { content: "Error: summary is required for complete — cite the evidence", isError: true };

      const goal = goals.get(goal_id);
      if (!goal) return { content: `Error: goal ${goal_id} not found`, isError: true };

      goal.status = "complete";
      goal.completedSummary = input.summary;
      goal.updatedAt = new Date().toISOString();

      return {
        content: JSON.stringify({
          goal_id: goal.id,
          status: "complete",
          summary: input.summary,
          total_iterations: goal.iteration,
          criteria_met: goal.acceptanceCriteria,
          message: "Goal marked complete. All acceptance criteria satisfied.",
        }, null, 2),
        isError: false,
      };
    }

    case "status": {
      if (!goal_id) {
        // Return all goals if no ID given
        const all = listGoals();
        if (all.length === 0) return { content: "No goals tracked.", isError: false };
        return {
          content: JSON.stringify(all.map((g) => ({
            id: g.id,
            status: g.status,
            description: g.description.slice(0, 80),
            iteration: g.iteration,
          })), null, 2),
          isError: false,
        };
      }
      const goal = goals.get(goal_id);
      if (!goal) return { content: `Error: goal ${goal_id} not found`, isError: true };
      return {
        content: JSON.stringify({
          id: goal.id,
          status: goal.status,
          description: goal.description,
          criteria: goal.acceptanceCriteria,
          iteration: goal.iteration,
          max_iterations: goal.maxIterations,
          verifications: goal.verificationResults,
          completed_summary: goal.completedSummary,
        }, null, 2),
        isError: false,
      };
    }

    default:
      return { content: `Unknown command: ${command}`, isError: true };
  }
}