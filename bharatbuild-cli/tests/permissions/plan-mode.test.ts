/**
 * Plan mode used to live only in the ink TUI, so `checkPermission` fell
 * through its final `return "allow"` for every mode that wasn't "ask".
 * A headless run under BHARATBUILD_MODE=plan created the file it was told to
 * refuse - confirmed against the real CLI before this was fixed.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { checkPermission } from "../../src/permissions/permission-manager.js";
import { evaluateCommandPolicy } from "../../src/permissions/command-policy.js";
import { takeDenyReason } from "../../src/permissions/deny-reason.js";
import { isMutating } from "../../src/permissions/plan-mode.js";

const plan = { permissionMode: "plan", nonInteractive: true } as any;

beforeEach(() => { takeDenyReason(); });

describe("plan mode outside the TUI", () => {
  it("refuses a write", async () => {
    await expect(checkPermission("write_file", { path: "a.txt" }, plan)).resolves.toBe("deny");
  });

  it("refuses a shell command", async () => {
    await expect(checkPermission("execute_command", { command: "ls" }, plan)).resolves.toBe("deny");
  });

  it("refuses every alias of a mutating tool", async () => {
    // The model reaches for whichever name the backend advertised; gating one
    // spelling and not the other leaves a hole it walks straight through.
    for (const t of ["write", "write_file", "edit_file", "apply_patch", "delete_file", "shell", "execute_command"]) {
      await expect(checkPermission(t, { path: "a.txt", command: "ls" }, plan), t).resolves.toBe("deny");
    }
  });

  it("still allows reads so the agent can investigate", async () => {
    for (const t of ["read_file", "list_files", "grep", "search_code"]) {
      await expect(checkPermission(t, { path: "a.txt" }, plan), t).resolves.toBe("allow");
    }
  });

  it("explains itself instead of looking like a random failure", async () => {
    // Given a bare denial the model guessed at filename restrictions and
    // directory permissions, none of which were true.
    await checkPermission("write_file", { path: "a.txt" }, plan);
    const reason = takeDenyReason();
    expect(reason).toMatch(/plan mode/i);
    expect(reason).toMatch(/do not retry/i);
  });

  it("is not undone by --trust-all-tools", async () => {
    // Asking for a read-only session is the more specific instruction.
    const prev = process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    try {
      await expect(checkPermission("write_file", { path: "a.txt" }, plan)).resolves.toBe("deny");
    } finally {
      if (prev === undefined) delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
      else process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = prev;
    }
  });
});

describe("auto mode outside the TUI", () => {
  const auto = { permissionMode: "auto", nonInteractive: true } as any;

  it("runs writes and safe commands without asking", async () => {
    await expect(checkPermission("write_file", { path: "a.txt" }, auto)).resolves.toBe("allow");
    await expect(checkPermission("execute_command", { command: "node index.js" }, auto)).resolves.toBe("allow");
  });

  it("still refuses a protected path", async () => {
    // Auto-accept is not a licence to write outside the project.
    const target = process.platform === "win32" ? "C:\\Windows\\System32\\drivers\\etc\\hosts" : "/etc/hosts";
    await expect(checkPermission("write_file", { path: target }, auto)).resolves.toBe("deny");
  });
});

describe("command policy", () => {
  it("denies any command in plan mode, whatever it is", () => {
    // Defence in depth: checkPermission refuses first, but if that order ever
    // changes the policy must not quietly allow shell access.
    expect(evaluateCommandPolicy("ls", "plan")).toBe("deny");
    expect(evaluateCommandPolicy("rm -rf /", "plan")).toBe("deny");
  });
});

describe("the mutating list", () => {
  it("has one definition shared by the TUI and the gate", async () => {
    // Two copies drifted the moment either list changed.
    const fromUi = await import("../../src/ui/ink/modes.js");
    expect(fromUi.isMutating).toBe(isMutating);
  });
});
