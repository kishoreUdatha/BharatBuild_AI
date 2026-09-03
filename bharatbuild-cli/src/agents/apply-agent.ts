/**
 * Selecting an agent, in one place.
 *
 * Three things were wrong with how this worked:
 *
 *  1. `readOnly` in the registry was decoration. The only code that read it
 *     printed a "[read-only]" badge next to Planner. Running
 *     `chat --agent planner "create a file"` created the file.
 *
 *  2. chat.ts carried its own six-entry prompt map, while the registry defines
 *     ten agents. `--agent guide`, `spec`, `quickspec` and `bugfix` therefore
 *     fell through to the default prompt without a word.
 *
 *  3. An unknown name did the same. `--agent totally-not-an-agent` started a
 *     normal session, so a typo silently gave you a different agent.
 *
 * The registry is the source of truth here, and an unknown name is an error.
 */

import { AGENT_REGISTRY, type AgentDefinition, type AgentRole } from "./agent-registry.js";

export interface AppliedAgent {
  role: AgentRole;
  name: string;
  readOnly: boolean;
}

export function agentNames(): AgentRole[] {
  return Object.keys(AGENT_REGISTRY) as AgentRole[];
}

export function isKnownAgent(name: string): name is AgentRole {
  return Object.prototype.hasOwnProperty.call(AGENT_REGISTRY, name);
}

/**
 * The system prompt for a role, falling back to `default` for anything the
 * registry does not define.
 *
 * Four modules had grown their own copy of this table — chat.ts, the crew DAG
 * executor, the subagent tool and the hooks runtime — and the wording had
 * already drifted between them ("Break tasks into clear implementation plans"
 * vs "Create clear, ordered implementation plans" vs "Explore the codebase
 * and…"). Same role, three different jobs depending on which subsystem you
 * happened to be in.
 *
 * Unlike resolveAgent this does not throw: these call sites are handed a role
 * from a DAG stage or a hook config, where falling back is the long-standing
 * behaviour and an exception would abort the run.
 */
export function rolePrompt(role: string): string {
  const key = (role ?? "").trim().toLowerCase();
  const def = isKnownAgent(key) ? AGENT_REGISTRY[key] : AGENT_REGISTRY.default;
  return def.systemPrompt;
}

/** Look up an agent, or explain what the valid names are. */
export function resolveAgent(name: string): AgentDefinition {
  const key = (name ?? "").trim().toLowerCase();
  if (!isKnownAgent(key)) {
    throw new Error(`Unknown agent "${name}". Available: ${agentNames().join(", ")}`);
  }
  return AGENT_REGISTRY[key];
}

/**
 * Describe the agent's tools truthfully.
 *
 * The old prompt appended "You have access to tools for reading/writing files,
 * running commands, searching code, and git" to *every* agent — including the
 * one that is supposed to refuse all of that.
 */
function capabilityLine(def: AgentDefinition): string {
  return def.readOnly
    ? "You can read files, list directories, and search code. You cannot write " +
      "files, edit files, or run commands — those tools will refuse. Produce " +
      "your plan as text instead."
    : "You have access to tools for reading/writing files, running commands, " +
      "searching code, and git.";
}

/** The runtime surface this needs; kept narrow so tests can pass a double. */
export interface AgentTarget {
  context?: { setSystemPrompt?(prompt: string): void };
  setPermissionMode?(mode: "ask" | "auto" | "deny" | "plan"): void;
  /**
   * Adopt a role while keeping the rest of the system prompt. Preferred over
   * context.setSystemPrompt, which replaces everything - including the
   * guidance that names todo_list, subagent and delegate.
   */
  setAgentRole?(role: string): void;
}

/**
 * Apply an agent to a runtime: its prompt, and the permissions its role implies.
 *
 * A read-only agent is enforced through plan mode rather than a second
 * mechanism, because that gate already sits in front of every execution path
 * — TUI, headless, and nested subagents alike.
 */
export function applyAgent(
  runtime: AgentTarget,
  name: string,
  workingDir: string,
): AppliedAgent {
  const def = resolveAgent(name);

  // A read-only agent that cannot be restricted is the bug this module exists
  // to fix. Refuse loudly rather than hand back something labelled read-only
  // that is free to write — that is precisely how Planner shipped.
  if (def.readOnly) {
    if (typeof runtime.setPermissionMode !== "function") {
      throw new Error(
        `Cannot apply read-only agent "${def.role}": this runtime cannot restrict tools.`,
      );
    }
    runtime.setPermissionMode("plan");
  }

  const role = `${def.systemPrompt}\n\nWorking directory: ${workingDir}\n${capabilityLine(def)}`;

  // Prefer the additive path. setSystemPrompt replaces the whole prompt, so
  // using it here removed the standard tool guidance and left the agent
  // unaware of todo_list, subagent, delegate and thinking.
  if (typeof runtime.setAgentRole === "function") {
    runtime.setAgentRole(role);
  } else {
    // Losing the prompt is a degradation, not a safety failure, so a runtime
    // without either method must not abort the switch.
    runtime.context?.setSystemPrompt?.(role);
  }

  return { role: def.role, name: def.name, readOnly: !!def.readOnly };
}
