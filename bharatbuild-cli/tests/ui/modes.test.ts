/**
 * The agent stopped on every write because the mode was fixed at "ask", and
 * shift+tab — advertised as "modes" — toggled a read-only plan mode that
 * gated nothing. These cover the cycle and the gating it now performs.
 */
import { describe, it, expect } from "vitest";
import { nextMode, decideForMode, isMutating, normalizeMode, MODE_ORDER } from "../../src/ui/ink/modes.js";
import { takeDenyReason, setDenyReason } from "../../src/permissions/deny-reason.js";

describe("cycling", () => {
  it("goes ask -> auto -> plan -> ask", () => {
    expect(nextMode("ask")).toBe("auto");
    expect(nextMode("auto")).toBe("plan");
    expect(nextMode("plan")).toBe("ask");
  });

  it("returns to the start after one full cycle", () => {
    let m = MODE_ORDER[0]!;
    for (const _ of MODE_ORDER) m = nextMode(m);
    expect(m).toBe(MODE_ORDER[0]);
  });

  it("reaches auto before plan", () => {
    // The old binding jumped straight to read-only, which is the opposite of
    // what someone pressing "modes" to stop the prompting wants.
    expect(nextMode("ask")).not.toBe("plan");
  });
});

describe("auto mode", () => {
  it("approves without asking, which is the whole point", () => {
    for (const tool of ["write_file", "apply_patch", "shell", "read_file"]) {
      expect(decideForMode("auto", tool), tool).toBe("allow");
    }
  });
});

describe("ask mode", () => {
  it("defers to the user rather than deciding", () => {
    expect(decideForMode("ask", "write_file")).toBeNull();
    expect(decideForMode("ask", "read_file")).toBeNull();
  });
});

describe("plan mode", () => {
  it("refuses anything that changes the filesystem or runs a shell", () => {
    for (const tool of ["write_file", "apply_patch", "delete_file", "shell", "execute_command"]) {
      expect(decideForMode("plan", tool), tool).toBe("deny");
    }
  });

  it("still allows reading and searching so it can investigate", () => {
    for (const tool of ["read_file", "list_files", "grep", "find_files"]) {
      expect(decideForMode("plan", tool), tool).toBe("allow");
    }
  });

  it("classifies both names of each aliased tool", () => {
    // edit_file/apply_patch and shell/execute_command are the same capability
    // under two names; missing one leaves a hole in plan mode.
    for (const pair of [["write", "write_file"], ["edit_file", "apply_patch"], ["shell", "execute_command"]]) {
      expect(isMutating(pair[0]!), pair[0]).toBe(true);
      expect(isMutating(pair[1]!), pair[1]).toBe(true);
    }
  });
});

describe("explaining a refusal", () => {
  it("tells the model why plan mode refused, so it stops retrying", () => {
    setDenyReason(null);
    decideForMode("plan", "write_file");
    const reason = takeDenyReason();
    expect(reason).toContain("Plan mode");
    expect(reason).toContain("write_file");
    expect(reason).toMatch(/do not retry/i);
  });

  it("leaves no reason behind for an allowed call", () => {
    setDenyReason(null);
    decideForMode("plan", "read_file");
    decideForMode("auto", "write_file");
    expect(takeDenyReason()).toBeNull();
  });

  it("clears on read, so it cannot leak onto a later denial", () => {
    setDenyReason(null);
    decideForMode("plan", "shell");
    expect(takeDenyReason()).not.toBeNull();
    // A user-driven "no" in ask mode must not inherit the plan-mode text.
    expect(takeDenyReason()).toBeNull();
  });
});

describe("reading a configured mode", () => {
  it("accepts the name Claude Code uses", () => {
    // People type acceptEdits expecting it to work; silently falling back to
    // ask is how you end up prompted on every write despite setting it.
    expect(normalizeMode("acceptEdits")).toBe("auto");
    expect(normalizeMode("accept-edits")).toBe("auto");
  });

  it("is case and whitespace tolerant", () => {
    expect(normalizeMode("  AUTO ")).toBe("auto");
    expect(normalizeMode("Plan")).toBe("plan");
  });

  it("reports an unknown value rather than guessing", () => {
    // null lets the caller fall through to the next source; defaulting here
    // would mask a typo in config.json as a working setting.
    expect(normalizeMode("yolo")).toBeNull();
    expect(normalizeMode(undefined)).toBeNull();
    expect(normalizeMode("")).toBeNull();
  });
});
