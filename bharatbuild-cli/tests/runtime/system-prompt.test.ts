/**
 * The system prompt is the only thing that tells the agent a tool is worth
 * reaching for. Two problems lived here:
 *
 *  - Nothing instructed it to check on a background process. A server reports
 *    itself ready, crashes a second later, and the only trace is output nobody
 *    read.
 *  - Selecting an agent called context.setSystemPrompt, which *replaces* the
 *    prompt — deleting every line below, including the ones naming todo_list,
 *    subagent and delegate.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { AgentRuntime } from "../../src/runtime/agent-runtime.js";
import { loadConfig } from "../../src/config/config.js";
import { applyAgent } from "../../src/agents/apply-agent.js";

let dir: string;
let rt: AgentRuntime;

beforeAll(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-prompt-"));
  rt = new AgentRuntime({ config: { ...loadConfig(), workingDir: dir }, model: null as never });
});
afterAll(() => {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* lock */ }
});

describe("running a long-lived process", () => {
  it("tells the agent to start it in the background", () => {
    // Without this it uses a plain command, which blocks until the timeout and
    // is then killed — the app never stays up.
    expect(rt.context.systemPrompt).toContain("background:true");
  });

  it("tells it to read the output afterwards", () => {
    expect(rt.context.systemPrompt).toContain("read_process_output");
  });

  it("says why, not just what", () => {
    // "print ready and then fail" is the case; an instruction without the
    // reason is one the model drops under pressure.
    expect(rt.context.systemPrompt).toMatch(/ready.*then fail|then fails/i);
  });

  it("mentions stopping it", () => {
    expect(rt.context.systemPrompt).toContain("stop_process");
  });
});

describe("the guidance survives agent selection", () => {
  const NAMED = ["todo_list", "thinking", "subagent", "delegate", "read_process_output", "background:true"];

  it("is present in a default session", () => {
    for (const t of NAMED) expect(rt.context.systemPrompt, t).toContain(t);
  });

  it("is still present after choosing a writing agent", () => {
    applyAgent(rt, "coder", dir);
    for (const t of NAMED) expect(rt.context.systemPrompt, t).toContain(t);
  });

  it("is still present after choosing a read-only agent", () => {
    applyAgent(rt, "planner", dir);
    for (const t of NAMED) expect(rt.context.systemPrompt, t).toContain(t);
  });

  it("puts the agent's own role in the prompt too", () => {
    applyAgent(rt, "reviewer", dir);
    expect(rt.context.systemPrompt).toMatch(/code reviewer/i);
  });
});
