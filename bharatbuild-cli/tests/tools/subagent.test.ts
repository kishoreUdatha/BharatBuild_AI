/**
 * subagent had two faults. Validation only checked that `stages` was
 * non-empty, so a stage missing a required field crashed inside
 * `prompt_template.replace(...)` and returned "Cannot read properties of
 * undefined". And no agent was ever spawned: stages were reported "complete"
 * against work that had not happened.
 *
 * Stage execution is injectable so these run without a model or a network -
 * the default runner spawns a real nested AgentRuntime.
 */
import { describe, it, expect } from "vitest";
import { subagentTool, SubagentPipeline, stageConfig, stagesFor, type StageRunner } from "../../src/tools/built-in/subagent.js";

const run = (input: Record<string, unknown>) => subagentTool.execute(input);
const stage = (over: Record<string, unknown> = {}) => ({
  name: "s1", role: "kiro_default", prompt_template: "do {task}", ...over,
});

/** Records the order stages ran in and the prompt each one received. */
function recorder(reply: (name: string) => string = (n) => `${n} output`) {
  const seen: Array<{ name: string; prompt: string }> = [];
  const runner: StageRunner = async (s, prompt) => {
    seen.push({ name: s.name, prompt });
    return reply(s.name);
  };
  return { seen, runner };
}

describe("input validation", () => {
  it("names the stage and the missing field", async () => {
    const r = await run({ task: "t", stages: [{ name: "s1" }] });
    expect(r.isError).toBe(true);
    expect(r.content).toContain("'s1'");
    expect(r.content).toContain("prompt_template");
    expect(r.content).not.toContain("Cannot read properties");
  });

  it("falls back to the index when even the name is missing", async () => {
    const r = await run({ task: "t", stages: [{ role: "kiro_default" }] });
    expect(r.isError).toBe(true);
    expect(r.content).toContain("index 0");
  });

  it("reports every problem at once rather than one per round trip", async () => {
    const r = await run({ task: "t", stages: [{ name: "s1" }] });
    expect(r.content).toContain("'role'");
    expect(r.content).toContain("'prompt_template'");
  });

  it("rejects a dependency on a stage that does not exist", async () => {
    // Otherwise the scheduler finds nothing ready and blames a circular
    // dependency, which points at the wrong problem entirely.
    const r = await run({ task: "t", stages: [stage({ depends_on: ["ghost"] })] });
    expect(r.isError).toBe(true);
    expect(r.content).toContain("ghost");
  });

  it("rejects duplicate stage names", async () => {
    // Results are keyed by name, so the second silently replaced the first.
    const r = await run({ task: "t", stages: [stage(), stage({ prompt_template: "other" })] });
    expect(r.isError).toBe(true);
    expect(r.content).toContain("more than once");
  });
});

describe("running the pipeline", () => {
  it("actually runs each stage", async () => {
    // The whole point: this used to report success without calling anything.
    const { seen, runner } = recorder();
    const r = await new SubagentPipeline("build", [stage({ name: "plan" })], runner).execute();
    expect(seen.map((s) => s.name)).toEqual(["plan"]);
    expect(r.isError).toBe(false);
    expect(r.content).toContain("plan output");
  });

  it("substitutes {task} into the prompt", async () => {
    const { seen, runner } = recorder();
    await new SubagentPipeline("build a parser", [stage({ prompt_template: "please {task} now" })], runner).execute();
    expect(seen[0]!.prompt).toContain("build a parser");
    expect(seen[0]!.prompt).not.toContain("{task}");
  });

  it("runs a dependent stage after the one it needs", async () => {
    const { seen, runner } = recorder();
    await new SubagentPipeline("build", [
      stage({ name: "code", depends_on: ["plan"] }),
      stage({ name: "plan" }),
    ], runner).execute();
    expect(seen.map((s) => s.name)).toEqual(["plan", "code"]);
  });

  it("passes an upstream stage's output into the next prompt", async () => {
    // Each stage is a fresh runtime with no memory, so anything it needs has
    // to be handed over explicitly or it invents it.
    const { seen, runner } = recorder((n) => (n === "plan" ? "STEP-ONE-THEN-TWO" : "done"));
    await new SubagentPipeline("build", [
      stage({ name: "plan" }),
      stage({ name: "code", depends_on: ["plan"] }),
    ], runner).execute();
    const code = seen.find((s) => s.name === "code")!;
    expect(code.prompt).toContain("STEP-ONE-THEN-TWO");
  });

  it("runs independent stages together", async () => {
    const { seen, runner } = recorder();
    await new SubagentPipeline("build", [stage({ name: "a" }), stage({ name: "b" })], runner).execute();
    expect(seen.map((s) => s.name).sort()).toEqual(["a", "b"]);
  });
});

describe("when a stage goes wrong", () => {
  const explode: StageRunner = async (s) => {
    if (s.name === "plan") throw new Error("model unavailable");
    return `${s.name} output`;
  };

  it("reports the failure instead of a tick", async () => {
    const r = await new SubagentPipeline("build", [stage({ name: "plan" })], explode).execute();
    expect(r.isError).toBe(true);
    expect(r.content).toContain("failed");
    expect(r.content).toContain("model unavailable");
  });

  it("skips the stages that depended on it", async () => {
    // Running "code" with no plan produces confident nonsense: the prompt
    // refers to a plan that does not exist, so the agent invents one.
    const ran: string[] = [];
    const runner: StageRunner = async (s) => {
      ran.push(s.name);
      return explode(s, "");
    };
    const r = await new SubagentPipeline("build", [
      stage({ name: "plan" }),
      stage({ name: "code", depends_on: ["plan"] }),
    ], runner).execute();
    expect(ran).toEqual(["plan"]);
    expect(r.content).toContain("skipped");
    expect(r.isError).toBe(true);
  });

  it("does not skip an unrelated stage", async () => {
    const ran: string[] = [];
    const runner: StageRunner = async (s) => { ran.push(s.name); return explode(s, ""); };
    await new SubagentPipeline("build", [
      stage({ name: "plan" }),
      stage({ name: "docs" }),
    ], runner).execute();
    expect(ran.sort()).toEqual(["docs", "plan"]);
  });

  it("still detects a genuine cycle", async () => {
    const { runner } = recorder();
    const r = await new SubagentPipeline("t", [
      stage({ name: "a", depends_on: ["b"] }),
      stage({ name: "b", depends_on: ["a"] }),
    ], runner).execute();
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/circular/i);
  });

  it("says so when a stage produces no text at all", async () => {
    // An empty result must not read as a successful answer of "".
    const r = await new SubagentPipeline("build", [stage({ name: "plan" })], async () => "").execute();
    expect(r.content).toMatch(/without producing any text/i);
  });

  it("stops on an abort signal", async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    const { seen, runner } = recorder();
    await new SubagentPipeline("build", [stage({ name: "plan" })], runner).execute(ctrl.signal);
    expect(seen).toHaveLength(0);
  });
});

describe("what each role is allowed to do", () => {
  const base = { permissionMode: "auto", maxTurns: 50 } as any;

  it("gives a planning stage no way to write", async () => {
    // The role prompt already said "do not write the implementation" and a
    // live planner stage created the file regardless. A prompt is not a
    // permission.
    expect(stageConfig(stage({ role: "kiro_planner" }) as any, base, "auto").permissionMode).toBe("plan");
    expect(stageConfig(stage({ role: "kiro_guide" }) as any, base, "auto").permissionMode).toBe("plan");
  });

  it("leaves a working stage able to work", async () => {
    expect(stageConfig(stage({ role: "kiro_default" }) as any, base, "auto").permissionMode).toBe("auto");
  });

  it("caps how many turns one stage can spend", async () => {
    // Otherwise a looping stage runs through the whole interactive budget
    // with nobody watching it.
    expect(stageConfig(stage() as any, base, "auto").maxTurns).toBeLessThanOrEqual(15);
  });

  it("does not raise a lower limit the user set", async () => {
    expect(stageConfig(stage() as any, { ...base, maxTurns: 3 }, "auto").maxTurns).toBe(3);
  });

  it("honours a per-stage model override", async () => {
    expect(stageConfig(stage() as any, base, "haiku").model).toBe("haiku");
  });
});

describe("the single-stage shorthand", () => {
  // Requiring a stages array meant the model had to author a DAG before it
  // could delegate anything. For "write unit tests for auth.ts" that is more
  // work than doing the task, so the tool went unused. One task is now the
  // simple case; a pipeline is what you opt into.
  it("accepts a task with no stages", async () => {
    const r = await run({ task: "write unit tests for auth.ts" });
    expect(r.isError).toBe(false);
  });

  it("no longer demands a stages array", async () => {
    const r = await run({ task: "do a thing" });
    expect(r.content).not.toMatch(/'stages' array is required/);
  });

  it("runs it as one stage", async () => {
    const r = await run({ task: "do a thing" });
    // One stage means one line of stage output.
    expect((r.content.match(/Stage: /g) ?? [])).toHaveLength(1);
  });

  it("passes the task through to the stage", async () => {
    const r = await run({ task: "UNIQUE-TASK-MARKER" });
    expect(r.content).toContain("UNIQUE-TASK-MARKER");
  });

  it("builds exactly one stage from a bare task", () => {
    // Checked on the built stages rather than on pipeline output: executing
    // would spawn a real agent and make live model calls.
    const stages = stagesFor({ task: "do a thing" });
    expect(stages).toHaveLength(1);
    expect(stages[0]!.prompt_template).toContain("{task}");
  });

  it("defaults to the general-purpose role", () => {
    expect(stagesFor({ task: "do a thing" })[0]!.role).toBe("kiro_default");
  });

  it("honours a role when one is given", () => {
    expect(stagesFor({ task: "plan it", role: "kiro_planner" })[0]!.role).toBe("kiro_planner");
  });

  it("keeps explicit stages untouched", () => {
    const given = [stage({ name: "a" }), stage({ name: "b" })];
    expect(stagesFor({ task: "t", stages: given })).toBe(given);
  });

  it("still requires a task", async () => {
    const r = await run({ role: "kiro_default" });
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/'task' is required/);
  });

  it("leaves the pipeline form working", async () => {
    // The shorthand must not cost the capability it is shorthand for.
    const r = await run({
      task: "build",
      stages: [stage({ name: "plan" }), stage({ name: "code", depends_on: ["plan"] })],
    });
    expect(r.isError).toBe(false);
    expect((r.content.match(/Stage: /g) ?? [])).toHaveLength(2);
  });

  it("treats an empty stages array as the shorthand", async () => {
    // [] is not a pipeline; refusing it would be pedantry.
    const r = await run({ task: "do a thing", stages: [] });
    expect(r.isError).toBe(false);
  });
});
