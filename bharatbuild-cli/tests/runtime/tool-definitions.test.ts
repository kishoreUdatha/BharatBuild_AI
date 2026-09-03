import { describe, it, expect } from "vitest";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { EventStream } from "../../src/runtime/event-stream.js";

const defs = () => new ToolDispatcher(new EventStream()).getDefinitions() as Array<{ name: string }>;

describe("tool definitions sent to the model", () => {
  it("contains no duplicate names", () => {
    // Six tools were registered by both the built-in registry and the legacy
    // list. Providers reject a tools array with repeated names.
    const names = defs().map((d) => d.name);
    expect(names).toHaveLength(new Set(names).size);
  });

  it("keeps the built-in definition when a name is registered twice", () => {
    // execute() checks the built-in registry first, so the advertised schema
    // has to be the one that will actually handle the call.
    const registry = new ToolDispatcher(new EventStream()).getBuiltInRegistry();
    const builtIn = registry.getModelToolDefinitions() as Array<{ name: string; description?: string }>;
    const shipped = defs() as Array<{ name: string; description?: string }>;

    for (const name of ["web_fetch", "web_search", "knowledge", "subagent", "todo_list", "goal"]) {
      const fromRegistry = builtIn.find((d) => d.name === name);
      const fromShipped = shipped.find((d) => d.name === name);
      expect(fromRegistry, `${name} missing from registry`).toBeDefined();
      expect(fromShipped, `${name} missing from shipped defs`).toBeDefined();
      expect(fromShipped!.description).toBe(fromRegistry!.description);
    }
  });

  it("every definition has a name and an input schema", () => {
    for (const d of defs() as Array<Record<string, unknown>>) {
      expect(typeof d["name"]).toBe("string");
      expect(d["input_schema"] ?? d["inputSchema"], `${String(d["name"])} has no schema`).toBeDefined();
    }
  });

  it("still advertises the core filesystem and shell tools", () => {
    // `shell` used to be in this list. It was retired in favour of
    // execute_command when the six duplicate pairs were collapsed — the point
    // is that the *capability* is advertised, not that a particular spelling
    // survives, so assert the survivors by name and the pairs by count below.
    const names = defs().map((d) => d.name);
    for (const expected of ["read_file", "write_file", "execute_command", "grep", "glob"]) {
      expect(names, `${expected} missing`).toContain(expected);
    }
  });

  it("advertises exactly one tool per capability", () => {
    // Two tools doing the same job cost tokens on every turn and, worse, force
    // the model to choose between indistinguishable options. They were also
    // where the alias bugs came from: the backend advertised one spelling
    // while the CLI registered the other.
    const names = new Set(defs().map((d) => d.name));
    const pairs: Array<[string, string]> = [
      ["read", "read_file"],
      ["write", "write_file"],
      ["glob", "find_files"],
      ["grep", "search_code"],
      ["shell", "execute_command"],
    ];
    for (const [a, b] of pairs) {
      const present = [a, b].filter((n) => names.has(n));
      expect(present, `${a}/${b} should advertise exactly one`).toHaveLength(1);
    }
  });

  it("still executes the retired names", async () => {
    // Hidden from the model, not removed: a resumed session or a backend
    // advertising the other spelling must keep working.
    //
    // Permissions are pinned here rather than inherited. This first passed
    // only because it was run with BHARATBUILD_TRUST_ALL_TOOLS already set on
    // the command line, then failed in the full suite where it was not — the
    // same ambient-environment dependency that made the approval tests break
    // when the developer's config.json changed.
    const previous = process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    try {
      const { ToolDispatcher } = await import("../../src/runtime/tool-dispatcher.js");
      const { EventStream } = await import("../../src/runtime/event-stream.js");
      const d = new ToolDispatcher(new EventStream());
      const r = await d.execute("t1", "shell", { command: "echo retired-name-works" }, undefined);
      expect(r.isError, r.content).toBe(false);
      expect(r.content).toContain("retired-name-works");
    } finally {
      if (previous === undefined) delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
      else process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = previous;
    }
  });
});
