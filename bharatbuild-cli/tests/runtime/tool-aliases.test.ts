/**
 * The backend substitutes its own toolset instead of using the definitions the
 * CLI sends, so the model calls names this dispatcher never registered. Two of
 * them came back as "Unknown tool", and the built-in approval gate denied the
 * rest whenever --trust-all-tools was set.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { EventStream } from "../../src/runtime/event-stream.js";
import { checkToolApproval } from "../../src/tools/built-in/approval.js";
import { createToolRegistry } from "../../src/tools/built-in/index.js";
import { setPermissionAsker } from "../../src/permissions/permission-manager.js";

let dir: string;
let cwd: string;

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-alias-"));
  cwd = process.cwd();
  process.chdir(dir);
  process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
});

afterEach(() => {
  process.chdir(cwd);
  fs.rmSync(dir, { recursive: true, force: true });
  delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
  setPermissionAsker(null);
});

const dispatcher = () => new ToolDispatcher(new EventStream());

describe("server tool-name aliases", () => {
  it("routes edit_file to apply_patch and renames path → file_path", async () => {
    fs.writeFileSync(path.join(dir, "a.txt"), "alpha beta", "utf8");
    const res = await dispatcher().execute("t1", "edit_file", {
      path: "a.txt", old_string: "alpha", new_string: "gamma",
    });
    expect(res.isError, res.content).toBe(false);
    expect(fs.readFileSync(path.join(dir, "a.txt"), "utf8")).toBe("gamma beta");
  });

  it("routes list_directory to list_files", async () => {
    fs.writeFileSync(path.join(dir, "one.txt"), "x", "utf8");
    const res = await dispatcher().execute("t2", "list_directory", { path: "." });
    expect(res.isError, res.content).toBe(false);
    expect(res.content).toContain("one.txt");
  });

  it("reports the resolved name on the event, so the transcript matches what ran", async () => {
    fs.writeFileSync(path.join(dir, "b.txt"), "x", "utf8");
    const events = new EventStream();
    const seen: string[] = [];
    events.on("tool_call", (e: any) => { seen.push(e.toolName); });
    await new ToolDispatcher(events).execute("t3", "list_directory", { path: "." });
    expect(seen).toContain("list_files");
  });

  it("leaves unaliased names untouched", async () => {
    fs.writeFileSync(path.join(dir, "c.txt"), "hello", "utf8");
    const res = await dispatcher().execute("t4", "read_file", { path: "c.txt" });
    expect(res.isError, res.content).toBe(false);
    expect(res.content).toContain("hello");
  });

  it("still reports genuinely unknown tools as errors", async () => {
    const res = await dispatcher().execute("t5", "teleport", {});
    expect(res.isError).toBe(true);
    expect(res.content).toContain("Unknown tool");
  });
});

describe("built-in tool approval", () => {
  const registry = () => createToolRegistry();

  it("allows when --trust-all-tools is set", async () => {
    // The dispatcher passed `nonInteractive: !!TRUST_ALL`, and this gate denies
    // when nonInteractive is true — so the flag blocked every built-in tool.
    process.env["BHARATBUILD_TRUST_ALL_TOOLS"] = "1";
    expect(await checkToolApproval(registry(), "grep", { pattern: "x" })).toBe("allow");
  });

  it("denies without a TTY and without the trust flag", async () => {
    delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    const d = await checkToolApproval(registry(), "grep", { pattern: "x" }, { nonInteractive: true });
    expect(d).toBe("deny");
  });

  it("defers to the UI's asker rather than the readline prompt", async () => {
    // ink owns stdin; the readline prompt was invisible and unanswerable.
    delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    const ask = vi.fn(async () => "allow" as const);
    setPermissionAsker(ask);
    const d = await checkToolApproval(registry(), "shell", { command: "ls" }, { nonInteractive: true });
    expect(ask).toHaveBeenCalledWith("shell", { command: "ls" });
    expect(d).toBe("allow");
  });

  it("honours a denial from the UI", async () => {
    delete process.env["BHARATBUILD_TRUST_ALL_TOOLS"];
    setPermissionAsker(async () => "deny");
    expect(await checkToolApproval(registry(), "shell", { command: "ls" })).toBe("deny");
  });
});
