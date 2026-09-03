/**
 * The agent registry marked Planner `readOnly: true`, and the only code that
 * read the flag printed a "[read-only]" badge. Running
 * `chat --agent planner "create a file"` created the file.
 *
 * Two neighbouring problems: chat.ts kept its own six-entry prompt map while
 * the registry defines ten agents, so --agent guide/spec/quickspec/bugfix fell
 * through to the default prompt; and an unrecognised name did the same, so a
 * typo silently started an ordinary session.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { applyAgent, resolveAgent, agentNames, isKnownAgent, rolePrompt } from "../../src/agents/apply-agent.js";
import { AGENT_REGISTRY } from "../../src/agents/agent-registry.js";

/** Records what applyAgent did to a runtime. */
function fakeRuntime() {
  const calls = { prompt: "", mode: null as string | null };
  return {
    calls,
    context: { setSystemPrompt: (p: string) => { calls.prompt = p; } },
    setPermissionMode: (m: string) => { calls.mode = m; },
  };
}

describe("resolving a name", () => {
  it("knows every agent the registry defines", () => {
    // The old list had six of the ten.
    expect(agentNames().sort()).toEqual(Object.keys(AGENT_REGISTRY).sort());
    for (const name of Object.keys(AGENT_REGISTRY)) {
      expect(isKnownAgent(name), name).toBe(true);
    }
  });

  it("reaches the agents the old six-entry map omitted", () => {
    for (const name of ["spec", "quickspec", "bugfix", "guide"]) {
      expect(() => resolveAgent(name), name).not.toThrow();
    }
  });

  it("refuses an unknown name instead of quietly using default", () => {
    expect(() => resolveAgent("totally-not-an-agent")).toThrow(/unknown agent/i);
    expect(() => resolveAgent("totally-not-an-agent")).toThrow(/planner/); // lists the options
  });

  it("tolerates case and surrounding space", () => {
    expect(resolveAgent("  Planner ").role).toBe("planner");
  });
});

describe("applying a read-only agent", () => {
  it("puts the runtime in plan mode, so the flag actually restricts", () => {
    const rt = fakeRuntime();
    const applied = applyAgent(rt, "planner", "/tmp/x");
    expect(applied.readOnly).toBe(true);
    expect(rt.calls.mode).toBe("plan");
  });

  it("stops telling it that it can write files", () => {
    // Every agent used to get "You have access to tools for reading/writing
    // files, running commands..." appended — including this one.
    const rt = fakeRuntime();
    applyAgent(rt, "planner", "/tmp/x");
    expect(rt.calls.prompt).not.toMatch(/reading\/writing files/);
    expect(rt.calls.prompt).toMatch(/cannot write/i);
  });

  it("uses the registry's own prompt", () => {
    const rt = fakeRuntime();
    applyAgent(rt, "planner", "/tmp/x");
    expect(rt.calls.prompt).toContain(AGENT_REGISTRY.planner.systemPrompt);
  });

  it("includes the working directory", () => {
    const rt = fakeRuntime();
    applyAgent(rt, "coder", "/some/where");
    expect(rt.calls.prompt).toContain("/some/where");
  });
});

describe("applying a normal agent", () => {
  it("leaves permissions alone", () => {
    // Only a read-only role should narrow what the session may do.
    const rt = fakeRuntime();
    const applied = applyAgent(rt, "coder", "/tmp/x");
    expect(applied.readOnly).toBe(false);
    expect(rt.calls.mode).toBeNull();
  });

  it("still says it can use tools", () => {
    const rt = fakeRuntime();
    applyAgent(rt, "coder", "/tmp/x");
    expect(rt.calls.prompt).toMatch(/reading\/writing files/);
  });
});

describe("every registered agent is usable", () => {
  it("applies without throwing and gets a non-empty prompt", () => {
    // A registry entry with no systemPrompt would silently produce an agent
    // with no instructions at all.
    for (const name of agentNames()) {
      const rt = fakeRuntime();
      expect(() => applyAgent(rt, name, "/tmp/x"), name).not.toThrow();
      expect(rt.calls.prompt.trim().length, name).toBeGreaterThan(20);
    }
  });

  it("restricts exactly the agents the registry marks read-only", () => {
    for (const name of agentNames()) {
      const rt = fakeRuntime();
      applyAgent(rt, name, "/tmp/x");
      const expected = AGENT_REGISTRY[name].readOnly ? "plan" : null;
      expect(rt.calls.mode, name).toBe(expected);
    }
  });

  it("refuses a read-only agent it cannot actually restrict", () => {
    // The original version of this test asserted the opposite — that a missing
    // setter was tolerated. That is the exact shape of the bug being fixed: an
    // agent labelled read-only, free to write. Fail loudly instead.
    const rt = { context: { setSystemPrompt: () => {} } };
    expect(() => applyAgent(rt, "planner", "/tmp/x")).toThrow(/cannot restrict tools/i);
  });

  it("still switches a normal agent on a bare runtime", () => {
    // Losing the system prompt degrades the agent; it does not make it unsafe,
    // so it must not abort the switch.
    const rt = {};
    expect(() => applyAgent(rt, "coder", "/tmp/x")).not.toThrow();
    expect(applyAgent(rt, "coder", "/tmp/x").role).toBe("coder");
  });
});

describe("one prompt table, not four", () => {
  // chat.ts, the crew DAG executor, the subagent tool and the hooks runtime
  // each carried their own copy, and the wording had already drifted: the same
  // "planner" was told to "break tasks into clear implementation plans" in one
  // and to "create clear, ordered implementation plans" in another.
  const SRC = path.resolve(__dirname, "../../src");

  it("leaves no local prompt table behind", () => {
    const files = [
      "commands/chat.ts",
      "crew/dag-executor.ts",
      "tools/agent/subagent.ts",
      "hooks/hooks-runtime.ts",
    ];
    for (const f of files) {
      const src = fs.readFileSync(path.join(SRC, f), "utf8");
      expect(src, f).not.toMatch(/const (?:HOOK_)?AGENT_PROMPTS/);
    }
  });

  it("serves the registry's own wording to every caller", () => {
    for (const role of agentNames()) {
      expect(rolePrompt(role), role).toBe(AGENT_REGISTRY[role].systemPrompt);
    }
  });

  it("falls back rather than throwing, since callers pass unvalidated roles", () => {
    // A DAG stage or hook config supplies these; an exception would abort the
    // whole run over a typo in a config file.
    expect(rolePrompt("nonsense")).toBe(AGENT_REGISTRY.default.systemPrompt);
    expect(rolePrompt("")).toBe(AGENT_REGISTRY.default.systemPrompt);
  });

  it("reaches roles the old six-entry copies never had", () => {
    for (const role of ["spec", "quickspec", "bugfix", "guide"]) {
      expect(rolePrompt(role), role).not.toBe(AGENT_REGISTRY.default.systemPrompt);
    }
  });
});

describe("selecting an agent keeps the standard guidance", () => {
  // context.setSystemPrompt *replaces* the prompt, so applying an agent through
  // it deleted the lines naming todo_list, subagent, delegate and thinking —
  // along with "think step by step" and "show the root cause before the fix".
  // The agent then behaved as though those tools did not exist, which is a
  // plausible reason they were never used.
  function runtimeWithRole() {
    const calls = { role: "", replaced: "" };
    return {
      calls,
      context: { setSystemPrompt: (p: string) => { calls.replaced = p; } },
      setPermissionMode: () => {},
      setAgentRole: (r: string) => { calls.role = r; },
    };
  }

  it("uses the additive path when the runtime offers one", () => {
    const rt = runtimeWithRole();
    applyAgent(rt, "coder", "/tmp/x");
    expect(rt.calls.role).toContain(AGENT_REGISTRY.coder.systemPrompt);
    // The replacing path must not be taken when the additive one exists.
    expect(rt.calls.replaced).toBe("");
  });

  it("falls back to replacing only when there is no alternative", () => {
    const rt = {
      calls: { replaced: "" },
      context: { setSystemPrompt(p: string) { rt.calls.replaced = p; } },
      setPermissionMode: () => {},
    };
    applyAgent(rt, "coder", "/tmp/x");
    expect(rt.calls.replaced).toContain(AGENT_REGISTRY.coder.systemPrompt);
  });

  it("passes the role for a read-only agent too", () => {
    const rt = runtimeWithRole();
    applyAgent(rt, "planner", "/tmp/x");
    expect(rt.calls.role).toMatch(/cannot write/i);
  });
});
