/**
 * The permission gate decided every tool call the agent tried to make, and two
 * of its behaviours stopped the agent working at all:
 *   - --trust-all-tools never reached it, so the flag looked like a no-op
 *   - "ask" fell back to a readline prompt that the ink TUI painted over
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { checkPermission, setPermissionAsker } from "../../src/permissions/permission-manager.js";

const cfg = (over: Record<string, unknown> = {}) =>
  ({ permissionMode: "ask", nonInteractive: true, ...over }) as any;

afterEach(() => {
  setPermissionAsker(null);
  delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
});

describe("non-interactive default", () => {
  it("denies rather than silently escalating when nobody can answer", async () => {
    const d = await checkPermission("write_file", { path: "a.txt" }, cfg());
    expect(d).toBe("deny");
  });
});

describe("--trust-all-tools", () => {
  it("allows a tool that would otherwise be denied", async () => {
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    expect(await checkPermission("write_file", { path: "a.txt" }, cfg())).toBe("allow");
  });

  it("allows shell commands", async () => {
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    expect(await checkPermission("execute_command", { command: "echo hi" }, cfg())).toBe("allow");
  });

  it("still refuses to write a protected path", async () => {
    // Trusting tools is not the same as disabling the safety rail.
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    const d = await checkPermission("write_file", { path: "/etc/passwd" }, cfg());
    expect(d).toBe("deny");
  });
});

describe("external asker", () => {
  it("is used instead of the readline prompt", async () => {
    // The ink TUI holds stdin in raw mode; the readline prompt was invisible
    // and unanswerable, so everything ended up denied.
    const ask = vi.fn(async () => "allow" as const);
    setPermissionAsker(ask);
    const d = await checkPermission("write_file", { path: "a.txt" }, cfg({ nonInteractive: false }));
    expect(ask).toHaveBeenCalledWith("write_file", { path: "a.txt" });
    expect(d).toBe("allow");
  });

  it("is consulted even when no TTY is present", async () => {
    setPermissionAsker(async () => "allow");
    expect(await checkPermission("write_file", { path: "a.txt" }, cfg())).toBe("allow");
  });

  it("can deny", async () => {
    setPermissionAsker(async () => "deny");
    expect(await checkPermission("write_file", { path: "a.txt" }, cfg())).toBe("deny");
  });

  it("does not get asked about protected paths", async () => {
    const ask = vi.fn(async () => "allow" as const);
    setPermissionAsker(ask);
    expect(await checkPermission("delete_file", { path: "/etc/hosts" }, cfg())).toBe("deny");
    expect(ask).not.toHaveBeenCalled();
  });

  it("is removed when unset", async () => {
    setPermissionAsker(async () => "allow");
    setPermissionAsker(null);
    expect(await checkPermission("write_file", { path: "a.txt" }, cfg())).toBe("deny");
  });
});

describe("acceptEdits / bypass modes", () => {
  it("allows without asking when the mode is not 'ask'", async () => {
    const ask = vi.fn(async () => "deny" as const);
    setPermissionAsker(ask);
    expect(await checkPermission("write_file", { path: "a.txt" }, cfg({ permissionMode: "acceptEdits" }))).toBe("allow");
    expect(ask).not.toHaveBeenCalled();
  });
});
