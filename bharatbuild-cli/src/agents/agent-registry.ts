/** BharatBuild CLI - Agent Registry */

export type AgentRole =
  | "default"
  | "planner"
  | "coder"
  | "tester"
  | "fixer"
  | "reviewer"
  | "spec"
  | "quickspec"
  | "bugfix"
  | "guide";

export interface AgentDefinition {
  role: AgentRole;
  name: string;
  description: string;
  systemPrompt: string;
  readOnly?: boolean;   // true = no write tools (like Kiro Plan agent)
  phases?: string[];    // multi-phase agents
}

export const AGENT_REGISTRY: Record<AgentRole, AgentDefinition> = {
  default: {
    role: "default",
    name: "Default",
    description: "General-purpose coding assistant with full tool access",
    systemPrompt:
      "You are BharatBuild AI, an expert software engineer assistant. " +
      "Complete tasks thoroughly using available tools. Write production-quality code.",
  },
  planner: {
    role: "planner",
    name: "Planner",
    description: "Read-only planning agent — explores codebase and creates implementation plans without making changes",
    systemPrompt:
      "You are a senior software architect. Explore the codebase and break tasks into " +
      "clear, ordered implementation steps. Think about dependencies, risks, and the simplest correct approach.",
    readOnly: true,
  },
  coder: {
    role: "coder",
    name: "Coder",
    description: "Writes production-quality code",
    systemPrompt:
      "You are an expert software engineer. Write clean, well-tested, production-quality code. " +
      "Follow existing patterns in the codebase.",
  },
  tester: {
    role: "tester",
    name: "Tester",
    description: "Writes and runs tests",
    systemPrompt:
      "You are a QA engineer. Write comprehensive unit and integration tests. " +
      "Ensure edge cases are covered. Run tests and fix failures.",
  },
  fixer: {
    role: "fixer",
    name: "Fixer",
    description: "Diagnoses and fixes errors",
    systemPrompt:
      "You are a debugging expert. Identify root causes of errors (not symptoms). " +
      "Fix issues without breaking existing functionality.",
  },
  reviewer: {
    role: "reviewer",
    name: "Reviewer",
    description: "Reviews code for quality and security",
    systemPrompt:
      "You are a code reviewer. Check for bugs, security vulnerabilities, performance issues, " +
      "and code quality. Provide specific, actionable feedback.",
  },
  spec: {
    role: "spec",
    name: "Spec",
    description: "Structured feature development with approval gates: Requirements → Design → Tasks",
    systemPrompt:
      "You are a software architect running a structured spec workflow. " +
      "Generate precise requirements, technical designs, and implementation task lists.",
    phases: ["requirements", "design", "tasks"],
  },
  quickspec: {
    role: "quickspec",
    name: "Quick Spec",
    description: "Fast spec workflow — auto-generates Requirements, Design, and Tasks without approval gates",
    systemPrompt:
      "You are a software architect. Quickly generate requirements, design, and tasks " +
      "for a feature without waiting for approval.",
    phases: ["requirements", "design", "tasks"],
  },
  bugfix: {
    role: "bugfix",
    name: "Bug Fix",
    description: "Structured bug investigation: Root Cause Analysis → Fix Design → Implementation",
    systemPrompt:
      "You are a debugging expert running a structured bug fix workflow. " +
      "Investigate systematically, design a minimal fix, then implement it.",
    phases: ["root-cause", "fix-design", "implementation"],
  },
  guide: {
    role: "guide",
    name: "Guide",
    description: "CLI documentation agent — answers questions about BharatBuild CLI features and commands",
    systemPrompt:
      "You are the BharatBuild CLI guide. Answer questions about CLI commands, features, " +
      "configuration, and usage. Be concise and accurate.",
  },
};

export function getAgent(role: AgentRole): AgentDefinition {
  return AGENT_REGISTRY[role];
}

export function getAllAgents(): AgentDefinition[] {
  return Object.values(AGENT_REGISTRY);
}