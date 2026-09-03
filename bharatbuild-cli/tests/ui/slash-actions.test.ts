import { describe, it, expect, beforeEach } from "vitest";
import { runSlashCommand, inkUnhandled, INK_HANDLED } from "../../src/ui/ink/slash-actions.js";
import { commandsFor } from "../../src/ui/slash-registry.js";
import { makeRuntime } from "../helpers/ink-harness.js";

function ctx(over: Record<string, any> = {}) {
  return {
    runtime: makeRuntime(),
    model: "auto",
    agent: "default",
    compact: false,
    planMode: false,
    tangentMode: false,
    transcript: [],
    ...over,
  } as any;
}

describe("registry coverage", () => {
  it("implements every command the registry claims for the tui surface", () => {
    // The ink surface used to implement zero of them; this guards the regression.
    expect(inkUnhandled()).toEqual([]);
  });

  it("does not claim commands that belong to the repl surface", () => {
    const replOnly = commandsFor("repl")
      .filter((c) => !c.surfaces.includes("tui"))
      .map((c) => c.name);
    for (const name of replOnly) {
      expect(INK_HANDLED.has(name)).toBe(false);
    }
  });
});

describe("help", () => {
  it("lists every tui command", async () => {
    const out = (await runSlashCommand("/help", ctx())).output ?? "";
    for (const c of commandsFor("tui")) {
      expect(out).toContain(`/${c.name}`);
    }
  });

  it("fits a normal terminal", async () => {
    // One line per command overflowed an 80x30 terminal and corrupted the frame.
    const out = (await runSlashCommand("/help", ctx())).output ?? "";
    expect(out.split("\n").length).toBeLessThanOrEqual(30);
  });

  it("treats a bare slash as help", async () => {
    expect((await runSlashCommand("/", ctx())).output).toContain("Commands");
  });
});

describe("state toggles", () => {
  it.each([
    ["/plan", "planMode"],
    ["/tangent", "tangentMode"],
    ["/compact", "compact"],
  ])("%s flips %s", async (cmd, key) => {
    expect((await runSlashCommand(cmd, ctx()))?.patch?.[key]).toBe(true);
    expect((await runSlashCommand(cmd, ctx({ [key]: true })))?.patch?.[key]).toBe(false);
  });
});

describe("model and agent", () => {
  it("reports the active model when given no argument", async () => {
    expect((await runSlashCommand("/model", ctx())).output).toContain("auto");
  });

  it("sets a new model", async () => {
    expect((await runSlashCommand("/model sonnet", ctx())).patch?.model).toBe("sonnet");
  });

  it("rejects an unknown agent instead of silently accepting it", async () => {
    const out = (await runSlashCommand("/agent wizard", ctx())).output ?? "";
    expect(out).toContain("Unknown agent");
  });

  it("accepts a known agent", async () => {
    expect((await runSlashCommand("/agent coder", ctx())).patch?.agent).toBe("coder");
  });

  it("validates effort levels", async () => {
    expect((await runSlashCommand("/effort bogus", ctx())).output).toContain("Unknown effort");
    expect((await runSlashCommand("/effort xhigh", ctx())).output).toContain("xhigh");
  });

  it("validates theme names", async () => {
    expect((await runSlashCommand("/theme neon", ctx())).output).toContain("Unknown theme");
  });
});

describe("runtime inspection", () => {
  it("/usage summarises the cost meter", async () => {
    expect((await runSlashCommand("/usage", ctx())).output).toContain("1,234 tokens");
  });

  it("/context reports live stats", async () => {
    const out = (await runSlashCommand("/context", ctx())).output ?? "";
    expect(out).toContain("Messages:");
    expect(out).toContain("200,000");
  });

  it("/context clear empties the runtime context", async () => {
    const runtime = makeRuntime();
    runtime.context.messages = [{ role: "user", content: "x" }];
    await runSlashCommand("/context clear", ctx({ runtime }));
    expect(runtime.context.messages).toHaveLength(0);
  });

  it("/tools lists registered tools", async () => {
    expect((await runSlashCommand("/tools", ctx())).output).toContain("read_file");
  });

  it("/mcp reports honestly when nothing is connected", async () => {
    expect((await runSlashCommand("/mcp", ctx())).output).toContain("No MCP");
  });

  it("/session-id reports the id", async () => {
    expect((await runSlashCommand("/session-id", ctx())).output).toContain("sess-test");
  });
});

describe("rewind", () => {
  const withTurns = () => {
    const runtime = makeRuntime();
    runtime.context.messages = [
      { role: "user", content: "first request" },
      { role: "assistant", content: "first answer" },
      { role: "user", content: "second request" },
      { role: "assistant", content: "second answer" },
    ];
    return runtime;
  };

  it("lists forkable turns", async () => {
    const out = (await runSlashCommand("/rewind", ctx({ runtime: withTurns() }))).output ?? "";
    expect(out).toContain("first request");
    expect(out).toContain("second request");
  });

  it("rejects an out-of-range turn", async () => {
    const out = (await runSlashCommand("/rewind 99", ctx({ runtime: withTurns() }))).output ?? "";
    expect(out).toContain("between 1 and");
  });

  it("truncates context at the chosen turn", async () => {
    const runtime = withTurns();
    await runSlashCommand("/rewind 2", ctx({ runtime }));
    expect(runtime.context.messages).toHaveLength(2);
    expect(runtime.context.messages.at(-1)?.content).toBe("first answer");
  });

  it("reports when there is nothing to rewind", async () => {
    expect((await runSlashCommand("/rewind", ctx())).output).toContain("No conversation");
  });
});

describe("clipboard-backed commands", () => {
  it("/copy reports when there is nothing to copy", async () => {
    expect((await runSlashCommand("/copy", ctx())).output).toContain("No assistant response");
  });

  it("/reply quotes the last assistant message into the input", async () => {
    const res = await runSlashCommand("/reply", ctx({
      transcript: [{ role: "assistant", content: "line one\nline two", timestamp: new Date(0) }],
    }));
    expect(res.inputValue).toBe("> line one\n> line two\n\n");
  });

  it("/reply reports when there is nothing to quote", async () => {
    expect((await runSlashCommand("/reply", ctx())).output).toContain("No assistant response");
  });
});

describe("session control", () => {
  it("/clear signals a transcript wipe", async () => {
    expect((await runSlashCommand("/clear", ctx())).clear).toBe(true);
  });

  it.each(["/exit", "/quit", "/q"])("%s signals exit", async (cmd) => {
    expect((await runSlashCommand(cmd, ctx())).exit).toBe(true);
  });
});

describe("unknown input", () => {
  it("explains an unknown command", async () => {
    expect((await runSlashCommand("/nonsense", ctx())).output).toContain("Unknown command");
  });

  it("suggests the nearest command for a typo", async () => {
    expect((await runSlashCommand("/comapct", ctx())).output).toContain("Did you mean");
  });

  it("points repl-only commands at the other surface", async () => {
    expect((await runSlashCommand("/projects", ctx())).output).toContain("not available here");
  });
});

describe("honesty about unimplemented paths", () => {
  it("/spec run points at the standalone command rather than faking output", async () => {
    // The classic TUI printed invented progress here ("85% coverage").
    const out = (await runSlashCommand("/spec run", ctx())).output ?? "";
    expect(out).toContain("bharatbuild spec");
    expect(out).not.toMatch(/\d+% coverage/);
  });

  it("/editor explains why it cannot open over the rich UI", async () => {
    expect((await runSlashCommand("/editor", ctx())).output).toContain("CLASSIC_UI");
  });
});

describe("every command is safe to invoke", () => {
  // Guards against a handler throwing on its no-argument form, which would
  // surface to the user as "Command failed".
  const skip = new Set(["exit", "quit", "q", "guide", "spawn", "upgrade-agent", "checkpoint"]);
  const names = commandsFor("tui").map((c) => c.name).filter((n) => !skip.has(n));

  it.each(names)("/%s returns a result without throwing", async (name) => {
    const res = await runSlashCommand(`/${name}`, ctx());
    expect(res).toBeTruthy();
    expect(typeof res).toBe("object");
  });
});
