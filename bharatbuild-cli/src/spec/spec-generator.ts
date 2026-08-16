import fs from "fs";
import path from "path";
import type { ModelClient } from "../runtime/agent-loop.js";
import { MODEL_TIERS } from "../config/constants.js";

export interface SpecGeneratorOptions {
  title: string;
  description: string;
  outputDir?: string;
}

export async function generateSpec(
  options: SpecGeneratorOptions,
  model: ModelClient
): Promise<{ requirementsPath: string; designPath: string }> {
  const dir = path.join(options.outputDir ?? process.cwd(), ".bharatbuild", "specs");
  fs.mkdirSync(dir, { recursive: true });

  const reqPrompt = `Generate a requirements document for: "${options.title}"
Description: ${options.description}

Format as markdown with:
# Requirements: ${options.title}
## Overview
## Functional Requirements
### REQ-1: [title]
[description with must/should/could]
### REQ-2: ...
## Non-Functional Requirements
## Acceptance Criteria`;

  const designPrompt = `Generate a technical design document for: "${options.title}"
Description: ${options.description}

Format as markdown with:
# Design: ${options.title}
## Overview
## Architecture
## Components
## Data Flow
## Open Questions`;

  let reqContent = "";
  let designContent = "";

  // Generate requirements
  process.stdout.write("  Generating requirements...");
  for await (const chunk of model.complete({
    model: MODEL_TIERS.sonnet,
    system: "You are a software architect. Generate concise, actionable spec documents.",
    messages: [{ role: "user", content: reqPrompt }],
    tools: [],
    maxTokens: 2000,
  })) {
    if (chunk.type === "text_delta") { reqContent += chunk.text; process.stdout.write("."); }
  }
  console.log(" done");

  // Generate design
  process.stdout.write("  Generating design doc...");
  for await (const chunk of model.complete({
    model: MODEL_TIERS.sonnet,
    system: "You are a software architect. Generate concise, actionable design documents.",
    messages: [{ role: "user", content: designPrompt }],
    tools: [],
    maxTokens: 2000,
  })) {
    if (chunk.type === "text_delta") { designContent += chunk.text; process.stdout.write("."); }
  }
  console.log(" done");

  const reqPath = path.join(dir, "requirements.md");
  const designPath = path.join(dir, "design.md");
  fs.writeFileSync(reqPath, reqContent);
  fs.writeFileSync(designPath, designContent);

  return { requirementsPath: reqPath, designPath: designPath };
}
