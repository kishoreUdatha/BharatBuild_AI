/**
 * Nested quotes on Windows, and what happens when output overruns the buffer.
 *
 * With a bare `cmd.exe /c`, an inner invocation lost its quotes:
 *
 *     powershell -Command "Write-Output ok"   ->   "Write-Output ok"
 *
 * The command was echoed, never executed — and the agent could not tell that
 * apart from a command that legitimately prints its own text, so it kept
 * trying variations that all "worked" and did nothing.
 */
import { describe, it, expect } from "vitest";
import { executeCommand } from "../../src/tools/shell/index.js";

const onWindows = process.platform === "win32";

describe("nested quoting", () => {
  it.runIf(onWindows)("runs a nested PowerShell command instead of echoing it", async () => {
    const r = await executeCommand({ command: `powershell -NoProfile -Command "Write-Output ok"` });
    expect(r.content).toContain("ok");
    expect(r.content, "the command text itself must not come back").not.toContain("Write-Output ok");
  });

  it.runIf(onWindows)("keeps quoted arguments intact", async () => {
    const r = await executeCommand({ command: `node -e "console.log('quoted arg works')"` });
    expect(r.content).toContain("quoted arg works");
  });

  it("still runs an ordinary command", async () => {
    const r = await executeCommand({ command: "node -v" });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/v\d+/);
  });

  it("still reports a failing command as an error", async () => {
    const r = await executeCommand({ command: "node -e \"process.exit(3)\"" });
    expect(r.isError).toBe(true);
  });

  it("honours working_dir rather than needing a cd", async () => {
    const os = await import("node:os");
    const r = await executeCommand({
      command: "node -e \"console.log(process.cwd())\"",
      working_dir: os.tmpdir(),
    });
    expect(r.content.toLowerCase()).toContain("temp");
  });
});

describe("a command that floods the buffer", () => {
  it("returns what it captured instead of only an error code", async () => {
    // A docker build produced 586 usable lines and came back as
    // "Exit code: ERR_CHILD_PROCESS_STDIO_MAXBUFFER" with the rest discarded.
    const r = await executeCommand({
      command: `node -e "for(let i=0;i<400000;i++)console.log('flood line '+i)"`,
      timeout_ms: 60_000,
    });
    expect(r.isError).toBe(true);
    expect(r.content, "says it was truncated").toMatch(/more output than can be captured/i);
    expect(r.content, "keeps the output it did get").toContain("flood line");
  }, 90_000);

  it("suggests a way to get the whole thing", async () => {
    const r = await executeCommand({
      command: `node -e "for(let i=0;i<400000;i++)console.log('x'+i)"`,
      timeout_ms: 60_000,
    });
    expect(r.content).toMatch(/background:true|read_process_output/);
  }, 90_000);
});
