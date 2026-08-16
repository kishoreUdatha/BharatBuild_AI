/** BharatBuild CLI - Spec Agent
 *
 * Approval-gated structured feature development.
 * Mirrors Kiro CLI's Spec agent exactly:
 *   Phase 1: Requirements  — generates requirements.md, waits for approval
 *   Phase 2: Design        — generates design.md, waits for approval
 *   Phase 3: Tasks         — generates tasks.md, ready for execution
 *
 * QuickSpecAgent skips approval gates and auto-generates all three phases.
 */
import type { ModelClient } from "../runtime/agent-loop.js";
import { EventStream } from "../runtime/event-stream.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto } from "../models/model-router.js";
import fs from "fs";
import path from "path";
import readline from "readline";

// ── Shared prompt templates ────────────────────────────────────────────────

function requirementsPrompt(feature: string): string {
  return `Generate a requirements document for: "${feature}"

Format as Markdown:
# Requirements: ${feature}

## Overview
[2-3 sentence description]

## Functional Requirements
### REQ-1: [Title]
**Priority:** must | should | could
**Description:** [What it does]
**Acceptance Criteria:**
- [ ] [Testable criterion]

[Continue REQ-2, REQ-3, ...]

## Non-Functional Requirements
- Performance: [...]
- Security: [...]
- Usability: [...]

## Out of Scope
- [What is NOT included]

Be specific and testable. Each requirement must have clear acceptance criteria.`;
}

function designPrompt(feature: string, requirements: string): string {
  return `Generate a technical design document for: "${feature}"

Requirements already defined:
${requirements.slice(0, 2000)}

Format as Markdown:
# Design: ${feature}

## Overview
[Architecture summary]

## Components
### [Component Name]
- **Purpose:** [What it does]
- **File:** [path/to/file.ts]
- **Interface:** [Key exports/API]

## Data Flow
[How data moves through the system]

## Data Models
[Key interfaces/types]

## API / Interface Changes
[Any new endpoints or function signatures]

## Dependencies
[External packages or internal modules needed]

## Open Questions
- [ ] [Decision needed]

Be concrete — include actual file paths and function signatures.`;
}

function tasksPrompt(feature: string, design: string): string {
  return `Generate an implementation task list for: "${feature}"

Design already defined:
${design.slice(0, 2000)}

Format as Markdown:
# Tasks: ${feature}

## Implementation Plan

- [ ] **Task 1:** [Title]
  - File: [path/to/file]
  - Changes: [What to implement]
  - Depends on: [none | Task X]

- [ ] **Task 2:** [Title]
  ...

## Testing Tasks
- [ ] Write unit tests for [component]
- [ ] Write integration tests for [feature]

## Definition of Done
- [ ] All tasks complete
- [ ] Tests pass
- [ ] No TypeScript errors

Order tasks by dependency. Each task should be completable in one focused session.`;
}

// ── Spec output helpers ────────────────────────────────────────────────────

function getSpecDir(): string {
  return path.join(process.cwd(), ".bharatbuild", "specs");
}

async function generatePhase(
  prompt: string,
  model: ModelClient,
  modelId: string,
  onChunk?: (text: string) => void
): Promise<string> {
  let output = "";
  for await (const chunk of model.complete({
    model: modelId,
    system: "You are a senior software architect. Generate precise, actionable spec documents.",
    messages: [{ role: "user", content: prompt }],
    tools: [],
    maxTokens: 3000,
  })) {
    if (chunk.type === "text_delta" && chunk.text) {
      output += chunk.text;
      onChunk?.(chunk.text);
    }
  }
  return output;
}

async function askApproval(phase: string, filePath: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(
      `\n  ✓ ${phase} written to ${filePath}\n  Approve and continue to next phase? [Y/n] `,
      (answer) => {
        rl.close();
        resolve(answer.trim().toLowerCase() !== "n");
      }
    );
  });
}

// ── Approval-gated Spec Agent ──────────────────────────────────────────────

export class SpecAgent {
  readonly events: EventStream;
  private model: ModelClient;
  private modelId: string;

  constructor(model?: ModelClient, modelId?: string) {
    const config = loadConfig();
    this.modelId = modelId ?? config.model ?? "auto";
    this.model = model ?? createModelClientAuto(this.modelId);
    this.events = new EventStream();
  }

  async run(feature: string): Promise<void> {
    const specDir = getSpecDir();
    fs.mkdirSync(specDir, { recursive: true });

    await this.events.emit({ type: "status", message: `Starting spec for: ${feature}`, phase: "planning", timestamp: Date.now() });

    // ── Phase 1: Requirements ──────────────────────────────────────────────
    console.log(`\n  📋 Phase 1: Requirements\n`);
    process.stdout.write("  Generating");
    const reqContent = await generatePhase(
      requirementsPrompt(feature), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    console.log();
    const reqPath = path.join(specDir, "requirements.md");
    fs.writeFileSync(reqPath, reqContent);
    console.log(`\n${reqContent}\n`);

    const req1 = await askApproval("Requirements", reqPath);
    if (!req1) { console.log("  Spec cancelled at requirements phase.\n"); return; }

    // ── Phase 2: Design ────────────────────────────────────────────────────
    console.log(`\n  🏗️  Phase 2: Design\n`);
    process.stdout.write("  Generating");
    const designContent = await generatePhase(
      designPrompt(feature, reqContent), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    console.log();
    const designPath = path.join(specDir, "design.md");
    fs.writeFileSync(designPath, designContent);
    console.log(`\n${designContent}\n`);

    const req2 = await askApproval("Design", designPath);
    if (!req2) { console.log("  Spec cancelled at design phase.\n"); return; }

    // ── Phase 3: Tasks ─────────────────────────────────────────────────────
    console.log(`\n  ✅ Phase 3: Tasks\n`);
    process.stdout.write("  Generating");
    const tasksContent = await generatePhase(
      tasksPrompt(feature, designContent), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    console.log();
    const tasksPath = path.join(specDir, "tasks.md");
    fs.writeFileSync(tasksPath, tasksContent);
    console.log(`\n${tasksContent}\n`);

    console.log(`  ✓ Spec complete!\n`);
    console.log(`  Requirements : ${reqPath}`);
    console.log(`  Design       : ${designPath}`);
    console.log(`  Tasks        : ${tasksPath}\n`);
    console.log(`  Run 'bharatbuild task' to start implementing.\n`);
  }
}

// ── Quick Spec Agent (no approval gates) ──────────────────────────────────

export class QuickSpecAgent {
  readonly events: EventStream;
  private model: ModelClient;
  private modelId: string;

  constructor(model?: ModelClient, modelId?: string) {
    const config = loadConfig();
    this.modelId = modelId ?? config.model ?? "auto";
    this.model = model ?? createModelClientAuto(this.modelId);
    this.events = new EventStream();
  }

  async run(feature: string): Promise<void> {
    const specDir = getSpecDir();
    fs.mkdirSync(specDir, { recursive: true });

    await this.events.emit({ type: "status", message: `Quick spec for: ${feature}`, phase: "planning", timestamp: Date.now() });
    console.log(`\n  ⚡ Quick Spec: ${feature}\n`);

    // Phase 1
    process.stdout.write("  [1/3] Requirements");
    const reqContent = await generatePhase(
      requirementsPrompt(feature), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    fs.writeFileSync(path.join(specDir, "requirements.md"), reqContent);
    console.log(" ✓");

    // Phase 2
    process.stdout.write("  [2/3] Design      ");
    const designContent = await generatePhase(
      designPrompt(feature, reqContent), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    fs.writeFileSync(path.join(specDir, "design.md"), designContent);
    console.log(" ✓");

    // Phase 3
    process.stdout.write("  [3/3] Tasks       ");
    const tasksContent = await generatePhase(
      tasksPrompt(feature, designContent), this.model, this.modelId,
      () => process.stdout.write(".")
    );
    fs.writeFileSync(path.join(specDir, "tasks.md"), tasksContent);
    console.log(" ✓");

    console.log(`\n  ✓ Quick spec complete — all phases generated.\n`);
    console.log(`  Files in: ${specDir}\n`);
    console.log(`  Run 'bharatbuild task' to start implementing.\n`);
  }
}