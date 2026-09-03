/**
 * `execute_command` waited for the process to exit, which is right for a build
 * and wrong for anything you would call "running the app". A dev server never
 * exits, so it blocked for the full 120s timeout, was killed, and reported
 * failure — for an app that had started perfectly well. The startup output was
 * discarded too, so even "Server running on http://localhost:3000" never
 * reached the model, which would then go and "fix" working code.
 *
 * Nothing here binds a port. Readiness is detected from the output, so a
 * process that merely prints the line and stays alive exercises the same path
 * without leaving a listener on the machine running the tests.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { executeCommand } from "../../src/tools/shell/index.js";
import {
  readBackgroundOutput,
  stopBackgroundProcess,
  stopAllBackground,
  listBackground,
  takeBackgroundNotices,
} from "../../src/tools/shell/background.js";
import { readProcessOutput, stopProcess } from "../../src/tools/shell/process-tools.js";

let dir: string;

beforeAll(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-bgtest-"));

  // Announces itself the way a dev server does, then stays up.
  fs.writeFileSync(path.join(dir, "ready.js"), [
    'console.log("Server running on http://localhost:9999");',
    "setInterval(() => {}, 1000);",
  ].join("\n"));

  // Ready, then fails later — the case the agent was blind to.
  fs.writeFileSync(path.join(dir, "late.js"), [
    'console.log("Server running on http://localhost:9999");',
    'setTimeout(() => console.error("ERROR: failed to compile"), 400);',
    "setInterval(() => {}, 1000);",
  ].join("\n"));

  // Dies at once, like a missing dependency or a taken port.
  fs.writeFileSync(path.join(dir, "broken.js"), [
    `console.error("Error: Cannot find module 'express'");`,
    "process.exit(1);",
  ].join("\n"));

  // Reports ready, then dies on its own — the crash a poll would miss.
  fs.writeFileSync(path.join(dir, "dies.js"), [
    'console.log("Server running on http://localhost:9933");',
    'setTimeout(() => { console.error("FATAL: lost database connection"); process.exit(1); }, 900);',
    "setInterval(() => {}, 1000);",
  ].join("\n"));

  // Stays up but never says anything.
  fs.writeFileSync(path.join(dir, "quiet.js"), "setInterval(() => {}, 1000);");
});

afterEach(() => { stopAllBackground(); });
afterAll(() => {
  stopAllBackground();
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

const start = (file: string) =>
  executeCommand({ command: `node ${file}`, working_dir: dir, background: true });

const pidOf = (content: string): number =>
  Number(content.match(/pid (\d+)/)?.[1]);

describe("starting something that keeps running", () => {
  it("returns instead of blocking until the timeout", async () => {
    const began = Date.now();
    const r = await start("ready.js");
    // The blocking path would have sat here for the full shell timeout.
    expect(Date.now() - began).toBeLessThan(5_000);
    expect(r.isError).toBe(false);
  });

  it("reports the address the process announced", async () => {
    const r = await start("ready.js");
    expect(r.content).toContain("http://localhost:9999");
  });

  it("tells the model the process will not finish", async () => {
    // Without this the model waits for a result that never comes, or re-runs it.
    const r = await start("ready.js");
    expect(r.content).toMatch(/still running/i);
    expect(r.content).toMatch(/not.*(complete|finish)/i);
  });

  it("reports a pid that can be used later", async () => {
    const r = await start("ready.js");
    expect(Number.isFinite(pidOf(r.content))).toBe(true);
  });

  it("returns even when the process never announces itself", async () => {
    // A silent process is still running; waiting forever would be worse.
    const r = await executeCommand({
      command: "node quiet.js", working_dir: dir, background: true,
    });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/still running/i);
  }, 20_000);
});

describe("something that fails immediately", () => {
  it("is reported as an error, not as a healthy start", async () => {
    const r = await start("broken.js");
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/NOT running/i);
  });

  it("includes what it printed, so the cause is visible", async () => {
    const r = await start("broken.js");
    expect(r.content).toContain("Cannot find module");
  });
});

describe("checking on it afterwards", () => {
  it("returns the startup output on the first read", async () => {
    const r = await start("ready.js");
    const out = readBackgroundOutput(pidOf(r.content));
    expect(out.content).toContain("Server running");
    expect(out.isError).toBe(false);
  });

  it("returns only what is new on the next read", async () => {
    // Re-sending the whole buffer every poll would fill the context with what
    // the model has already seen.
    const r = await start("ready.js");
    const pid = pidOf(r.content);
    readBackgroundOutput(pid);
    const second = readBackgroundOutput(pid);
    expect(second.content).not.toContain("Server running");
    expect(second.content).toMatch(/no new output/i);
  });

  it("surfaces a failure that appears after startup", async () => {
    // The whole reason this tool exists: the process announced itself ready,
    // and the error arrived afterwards.
    const r = await start("late.js");
    const pid = pidOf(r.content);
    readBackgroundOutput(pid);
    await new Promise((res) => setTimeout(res, 900));
    expect(readBackgroundOutput(pid).content).toContain("failed to compile");
  });

  it("still reports on a process that has exited", async () => {
    // Why it died is in its output; dropping the record loses that.
    const r = await start("broken.js");
    const out = readBackgroundOutput(pidOf(r.content));
    expect(out.content).toMatch(/exited/i);
    expect(out.content).toContain("Cannot find module");
  });

  it("treats reading a dead process as a successful read", async () => {
    // "your server crashed" is an answer, not a malformed tool call.
    const r = await start("broken.js");
    expect(readBackgroundOutput(pidOf(r.content)).isError).toBe(false);
  });

  it("lists every process when no pid is given", async () => {
    await start("ready.js");
    const listed = readBackgroundOutput();
    expect(listed.content).toMatch(/pid \d+/);
    expect(listed.isError).toBe(false);
  });

  it("errors on a pid it does not know", async () => {
    expect(readBackgroundOutput(999_999).isError).toBe(true);
  });
});

describe("stopping it", () => {
  it("removes it from the registry", async () => {
    const r = await start("ready.js");
    const pid = pidOf(r.content);
    expect(listBackground().some((p) => p.pid === pid)).toBe(true);
    stopBackgroundProcess(pid);
    expect(listBackground().some((p) => p.pid === pid)).toBe(false);
  });

  it("reports what it stopped", async () => {
    const r = await start("ready.js");
    const stopped = stopBackgroundProcess(pidOf(r.content));
    expect(stopped.isError).toBe(false);
    expect(stopped.content).toMatch(/stopped/i);
  });

  it("errors on an unknown pid rather than claiming success", async () => {
    // Reporting a stop that did not happen is how a process is left running
    // while the registry says otherwise.
    const stopped = stopBackgroundProcess(999_999);
    expect(stopped.isError).toBe(true);
  });

  it("clears everything on session cleanup", async () => {
    await start("ready.js");
    await start("quiet.js");
    stopAllBackground();
    expect(listBackground()).toHaveLength(0);
  }, 20_000);
});

describe("the tools the model calls", () => {
  it("read_process_output reaches the same output", async () => {
    const r = await start("ready.js");
    const out = await readProcessOutput({ pid: pidOf(r.content) });
    expect(out.content).toContain("Server running");
  });

  it("read_process_output with no pid lists them", async () => {
    await start("ready.js");
    expect((await readProcessOutput({})).content).toMatch(/pid \d+/);
  });

  it("stop_process refuses a non-numeric pid", async () => {
    const r = await stopProcess({ pid: "not-a-number" as unknown as number });
    expect(r.isError).toBe(true);
  });

  it("stop_process stops a real one", async () => {
    const r = await start("ready.js");
    expect((await stopProcess({ pid: pidOf(r.content) })).isError).toBe(false);
  });
});

describe("a command that finishes is unaffected", () => {
  it("still runs in the foreground and returns its output", async () => {
    const r = await executeCommand({ command: "node -v", working_dir: dir });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/v\d+/);
  });
});

describe("a crash reports itself without being asked", () => {
  // The agent only polls when it decides to. It starts a server, is told
  // "still running", moves on to editing files — and a crash forty seconds
  // later goes unseen until something else trips over it. The loop drains
  // these at the top of every turn, so the death is volunteered instead.

  it("queues a notice when a process dies on its own", async () => {
    takeBackgroundNotices();                       // clear anything pending
    const r = await start("dies.js");
    expect(r.isError).toBe(false);
    expect(takeBackgroundNotices(), "reported before it died").toHaveLength(0);

    await new Promise((res) => setTimeout(res, 1400));
    const notices = takeBackgroundNotices();
    expect(notices).toHaveLength(1);
    expect(notices[0]).toMatch(/stopped on its own/i);
    expect(notices[0]).toMatch(/no longer running/i);
  }, 20_000);

  it("includes the output that explains why", async () => {
    takeBackgroundNotices();
    await start("dies.js");
    await new Promise((res) => setTimeout(res, 1400));
    expect(takeBackgroundNotices()[0]).toContain("FATAL");
  }, 20_000);

  it("reports each death once", async () => {
    // A notice repeated every turn is noise, and the model has already been
    // told.
    takeBackgroundNotices();
    await start("dies.js");
    await new Promise((res) => setTimeout(res, 1400));
    expect(takeBackgroundNotices()).toHaveLength(1);
    expect(takeBackgroundNotices()).toHaveLength(0);
  }, 20_000);

  it("says nothing when we stopped it ourselves", async () => {
    // A stop we asked for is not news.
    takeBackgroundNotices();
    const r = await start("ready.js");
    await new Promise((res) => setTimeout(res, 1100));
    stopBackgroundProcess(pidOf(r.content));
    await new Promise((res) => setTimeout(res, 400));
    expect(takeBackgroundNotices()).toHaveLength(0);
  }, 20_000);

  it("says nothing for a process that never started", async () => {
    // runInBackground already reports that in the tool result itself.
    takeBackgroundNotices();
    await start("broken.js");
    await new Promise((res) => setTimeout(res, 300));
    expect(takeBackgroundNotices()).toHaveLength(0);
  }, 20_000);
});
