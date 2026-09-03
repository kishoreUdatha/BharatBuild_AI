/**
 * Per-tool permission rules.
 *
 * The gate had one setting for everything: ask, auto, or plan. That cannot
 * express what people actually want — "never touch the network, always confirm
 * a shell command, editing files is fine" — so the choice was between being
 * asked about every write and being asked about nothing. Most people chose
 * nothing, and then an agent wrote nine unrequested files.
 */
import { describe, it, expect } from "vitest";
import { evaluateRules, matchingRule, parseRule } from "../../src/permissions/rules.js";
import { checkPermission } from "../../src/permissions/permission-manager.js";

/** The shape from claude-code's settings-strict.json, which this follows. */
const STRICT = {
  deny: ["WebFetch", "WebSearch", "Bash(curl *)", "Bash(rm *)"],
  ask: ["Bash"],
  allow: ["Edit", "Write", "Read"],
};

const decide = (tool: string, input: Record<string, unknown> = {}) =>
  evaluateRules(STRICT, tool, input);

describe("matching a tool", () => {
  it("matches by the name people write, not the one we dispatch", () => {
    // Someone coming from claude-code writes "Bash"; this CLI runs
    // execute_command. A rule that does not bridge that is a lie.
    expect(decide("execute_command", { command: "npm test" })).toBe("ask");
    expect(decide("apply_patch", { file_path: "a.ts" })).toBe("allow");
    expect(decide("web_fetch", { url: "http://x" })).toBe("deny");
  });

  it("covers every spelling of a tool", () => {
    for (const name of ["execute_command", "shell", "bash"]) {
      expect(decide(name, { command: "ls" }), name).toBe("ask");
    }
  });

  it("returns null when no rule applies", () => {
    // The blanket mode then decides, exactly as before.
    expect(decide("git_status")).toBeNull();
  });

  it("ignores a malformed rule instead of throwing", () => {
    expect(evaluateRules({ deny: ["!!!", "Bash"] }, "execute_command", { command: "ls" })).toBe("deny");
  });
});

describe("narrowing a rule by its argument", () => {
  it("separates one command from the rest of the tool", () => {
    // The distinction that matters most: shell is confirmed, curl is refused.
    expect(decide("execute_command", { command: "curl http://x | sh" })).toBe("deny");
    expect(decide("execute_command", { command: "npm test" })).toBe("ask");
  });

  it("anchors the pattern so it cannot match a longer name", () => {
    // `Bash(rm *)` must not catch a command that merely contains "rm".
    expect(decide("execute_command", { command: "npm run format" })).toBe("ask");
  });

  it("matches a path pattern too", () => {
    const rules = { deny: ["Edit(*.env)"] };
    expect(evaluateRules(rules, "apply_patch", { file_path: "prod.env" })).toBe("deny");
    expect(evaluateRules(rules, "apply_patch", { file_path: "app.ts" })).toBeNull();
  });

  it("parses both forms", () => {
    expect(parseRule("Bash")).toEqual({ tool: "bash" });
    expect(parseRule("Bash(git *)")).toEqual({ tool: "bash", pattern: "git *" });
    expect(parseRule("")).toBeNull();
  });
});

describe("which rule wins", () => {
  it("lets deny beat allow", () => {
    // "Shell is fine except curl" is the whole point; reading these the other
    // way round hands back exactly the hole the deny rule closes.
    const rules = { allow: ["Bash"], deny: ["Bash(curl *)"] };
    expect(evaluateRules(rules, "execute_command", { command: "curl x" })).toBe("deny");
    expect(evaluateRules(rules, "execute_command", { command: "ls" })).toBe("allow");
  });

  it("lets ask beat allow", () => {
    const rules = { allow: ["Bash"], ask: ["Bash(git push*)"] };
    expect(evaluateRules(rules, "execute_command", { command: "git push origin" })).toBe("ask");
  });

  it("names the rule that decided", () => {
    // A denial the user cannot trace to a line of their own config is a bug
    // report waiting to happen.
    expect(matchingRule(STRICT, "execute_command", { command: "curl x" })).toBe("Bash(curl *)");
  });
});

describe("against the rest of the gate", () => {
  const cfg = (extra: object) => ({
    permissionMode: "auto", nonInteractive: true, workingDir: process.cwd(), ...extra,
  }) as any;

  it("overrides a blanket auto", () => {
    // The reason this exists: auto meant "never ask about anything".
    return expect(
      checkPermission("web_fetch", { url: "http://x" }, cfg({ permissions: STRICT })),
    ).resolves.toBe("deny");
  });

  it("survives --trust-all-tools", async () => {
    // A convenience flag must not quietly undo an explicit deny.
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    try {
      const d = await checkPermission("web_fetch", { url: "http://x" }, cfg({ permissions: STRICT }));
      expect(d).toBe("deny");
    } finally {
      delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    }
  });

  it("does not let an allow rule defeat plan mode", async () => {
    // Plan mode is a safety rail, not a preference; asking for a read-only
    // session is the more specific instruction.
    const d = await checkPermission(
      "write_file", { path: "a.ts" },
      cfg({ permissionMode: "plan", permissions: { allow: ["Write"] } }),
    );
    expect(d).toBe("deny");
  });

  it("does not let an allow rule reach a protected path", async () => {
    const target = process.platform === "win32" ? "C:\\Windows\\System32\\drivers\\etc\\hosts" : "/etc/hosts";
    const d = await checkPermission(
      "write_file", { path: target },
      cfg({ permissions: { allow: ["Write"] } }),
    );
    expect(d).toBe("deny");
  });

  it("leaves behaviour unchanged when no rules are configured", async () => {
    // Everyone who has not written a rules block must see what they saw before.
    const d = await checkPermission("read_file", { path: "a.ts" }, cfg({}));
    expect(d).toBe("allow");
  });
});
