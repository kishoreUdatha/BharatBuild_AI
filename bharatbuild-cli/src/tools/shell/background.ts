/**
 * Running a process that is meant to stay up.
 *
 * `execute_command` waits for the process to exit, which is right for a build
 * or a test run and wrong for everything you would actually call "running the
 * app". A dev server never exits, so it blocked for the full 120s timeout, was
 * killed, and came back as an error — the app had usually started perfectly
 * well, and was then shut down before anyone could open it. Worse, the output
 * was discarded on timeout, so even "Server running on http://localhost:3000"
 * never reached the model, which would then start "fixing" working code.
 *
 * A background command instead: starts the process, waits only until it looks
 * ready (or briefly fails), reports what it printed, and leaves it running.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";

/** How long to wait for a startup line before reporting it as running. */
const READY_TIMEOUT_MS = 5_000;

/** Output kept per process, so a later check can show what it has printed. */
const MAX_BUFFERED_OUTPUT = 64 * 1024;

/**
 * Lines that mean "this thing is up". Frameworks vary, so this errs towards
 * matching: a false positive costs a slightly early return, while a false
 * negative costs the full wait, which is the worse of the two.
 */
const READY_PATTERNS = [
  /https?:\/\/\S+/i,
  /listening|ready in|started server|running (?:at|on)|compiled successfully/i,
  /server (?:is )?(?:running|started|listening)/i,
  /\bdev server\b/i,
];

export interface BackgroundProcess {
  pid: number;
  command: string;
  cwd: string;
  startedAt: number;
  output: string;
  exited: boolean;
  exitCode: number | null;
  /** Set when we stopped it, so its exit is not reported as a crash. */
  stoppedDeliberately?: boolean;
  /**
   * Set once runInBackground has reported this process as started. A death
   * before that is already in the tool result the caller received.
   */
  announced?: boolean;
  /**
   * How much of `output` has already been read. A poll should return what
   * is new, not the whole buffer again - re-reading a webpack log every
   * few seconds would fill the context with what the model has already seen.
   */
  readOffset: number;
  child: ChildProcess;
}

const running = new Map<number, BackgroundProcess>();

/**
 * Kill the process and everything it started.
 *
 * `child.kill()` signals the shell we spawned, not the program the shell
 * then ran. On Windows that means cmd.exe dies and `node server.js` keeps
 * running, holding its port — verified: the map reported zero processes
 * while the server was still answering requests, which is worse than not
 * cleaning up at all, because it claims to have done it.
 */
function killTree(proc: BackgroundProcess): void {
  proc.stoppedDeliberately = true;
  if (proc.exited) return;
  try {
    if (process.platform === "win32") {
      // /T takes the whole tree, /F does not ask nicely.
      spawnSync("taskkill", ["/pid", String(proc.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      // Spawned into its own process group, so a negative pid signals the
      // group rather than only the shell.
      try {
        process.kill(-proc.pid, "SIGTERM");
      } catch {
        proc.child.kill("SIGTERM");
      }
    }
  } catch {
    /* already gone */
  }
}

/**
 * Stop everything still running.
 *
 * A background server has to outlive the tool call but not the session, or
 * every run leaves another process holding the port.
 */
export function stopAllBackground(): void {
  for (const proc of running.values()) killTree(proc);
  running.clear();
}

let cleanupInstalled = false;
function installCleanup(): void {
  if (cleanupInstalled) return;
  cleanupInstalled = true;
  process.once("exit", stopAllBackground);
  process.once("SIGINT", () => { stopAllBackground(); process.exit(130); });
  process.once("SIGTERM", () => { stopAllBackground(); process.exit(143); });
}

/** Processes started this session, for `/ps`-style reporting. */
export function listBackground(): BackgroundProcess[] {
  return [...running.values()];
}

/** Stop one by pid. Returns false when it was not ours or already gone. */
export function stopBackground(pid: number): boolean {
  const proc = running.get(pid);
  if (!proc) return false;
  killTree(proc);
  running.delete(pid);
  return true;
}

/**
 * Background processes that died on their own, waiting to be reported.
 *
 * The agent only learns about a crash if it decides to poll. It starts a
 * server, is told "still running", moves on to editing files - and a crash
 * forty seconds later goes unseen until something else trips over it.
 * Queueing the death here lets the loop volunteer it on the next turn rather
 * than waiting to be asked.
 */
const pendingNotices: string[] = [];

/**
 * Take the crash notices accumulated since the last call.
 *
 * Drains rather than reads: repeating a notice every turn would be noise, and
 * the model has already been told once.
 */
export function takeBackgroundNotices(): string[] {
  return pendingNotices.splice(0, pendingNotices.length);
}

/**
 * Queue a crash for the loop to volunteer on its next turn.
 *
 * Only for a process that died on its own after having started successfully.
 * A stop we asked for is not news, and a process that never started is
 * already reported by the tool result.
 */
function noteUnexpectedExit(proc: BackgroundProcess): void {
  if (proc.stoppedDeliberately) return;
  // Not yet reported as started: runInBackground returns the failure itself,
  // so queueing it here would say the same thing twice. This was a 1000ms
  // window, which is a guess about timing rather than a fact about state - a
  // server that died at 900ms was silently swallowed.
  if (!proc.announced) return;

  const tail = proc.output.trim().split("\n").slice(-15).join("\n");
  pendingNotices.push(
    `The background process you started (pid ${proc.pid}, "${proc.command}") has ` +
    `stopped on its own with exit code ${proc.exitCode ?? "unknown"}. It is no longer ` +
    `running.` + (tail ? `\n\nIts last output:\n${tail}` : ""),
  );
}

/** How long a process has been up, for a status line. */
function uptime(proc: BackgroundProcess): string {
  const seconds = Math.round((Date.now() - proc.startedAt) / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m${seconds % 60}s`;
}

/** One line describing a process, for listings. */
function describe(proc: BackgroundProcess): string {
  const state = proc.exited
    ? `exited (code ${proc.exitCode ?? "unknown"})`
    : `running ${uptime(proc)}`;
  return `  pid ${proc.pid}  ${state}  ${proc.command}`;
}

/**
 * Output a background process has produced since this was last called.
 *
 * Without this the agent is blind the moment it starts a server: a dev
 * server that compiles for ten seconds and then reports an error announces
 * itself as ready first, and nothing would ever look again.
 */
export function readBackgroundOutput(pid?: number): BackgroundResult {
  if (pid === undefined) {
    const all = [...running.values()];
    if (all.length === 0) {
      return { content: "No background processes have been started.", isError: false };
    }
    return {
      content: `Background processes:\n${all.map(describe).join("\n")}`,
      isError: false,
    };
  }

  const proc = running.get(pid);
  if (!proc) {
    const known = [...running.keys()];
    return {
      content:
        `No background process with pid ${pid}.` +
        (known.length ? ` Known: ${known.join(", ")}.` : " None have been started."),
      isError: true,
    };
  }

  const fresh = proc.output.slice(proc.readOffset);
  proc.readOffset = proc.output.length;

  const header = proc.exited
    ? `pid ${pid} has exited with code ${proc.exitCode ?? "unknown"}.`
    : `pid ${pid} is still running (${uptime(proc)}).`;

  return {
    content: fresh.trim()
      ? `${header}\n\n${fresh.trimEnd()}`
      : `${header}\n\n(no new output since the last check)`,
    // An exited process is reported plainly rather than as an error: the
    // caller asked what happened, and it answered.
    isError: false,
  };
}

/** Stop one process and report what happened. */
export function stopBackgroundProcess(pid: number): BackgroundResult {
  const proc = running.get(pid);
  if (!proc) {
    return { content: `No background process with pid ${pid}.`, isError: true };
  }
  if (proc.exited) {
    running.delete(pid);
    return { content: `pid ${pid} had already exited.`, isError: false };
  }
  killTree(proc);
  running.delete(pid);
  return { content: `Stopped pid ${pid} (${proc.command}).`, isError: false };
}

function looksReady(output: string): boolean {
  return READY_PATTERNS.some((p) => p.test(output));
}

/** The URL a server announced, if it announced one. */
function detectUrl(output: string): string | null {
  const match = output.match(/https?:\/\/[^\s"'<>]+/i);
  return match ? match[0] : null;
}

export interface BackgroundResult {
  content: string;
  isError: boolean;
}

/**
 * Start `command` and leave it running.
 *
 * Returns as soon as the process looks ready, or when it exits early — an
 * immediate failure (a port already in use, a missing dependency) has to be
 * reported as a failure rather than as a healthy start.
 */
export async function runInBackground(
  command: string,
  cwd: string,
  shell: string,
  shellArgs: string[],
  readyTimeoutMs: number = READY_TIMEOUT_MS,
): Promise<BackgroundResult> {
  installCleanup();

  let child: ChildProcess;
  try {
    // No special quoting: the caller picks the shell through shell-config, and
    // PowerShell and bash both take the command as a single argument without
    // re-parsing its quotes the way cmd.exe /c did.
    child = spawn(shell, [...shellArgs, command], {
      cwd,
      // Own process group on POSIX so the whole tree can be signalled at
      // once; on Windows taskkill /T does that job instead. Either way the
      // exit handlers below stop it when the session ends.
      detached: process.platform !== "win32",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (err) {
    return {
      content: `Failed to start: ${err instanceof Error ? err.message : String(err)}`,
      isError: true,
    };
  }

  if (typeof child.pid !== "number") {
    return { content: "Failed to start: no process id", isError: true };
  }

  const proc: BackgroundProcess = {
    pid: child.pid,
    command,
    cwd,
    startedAt: Date.now(),
    output: "",
    exited: false,
    exitCode: null,
    readOffset: 0,
    child,
  };
  running.set(child.pid, proc);

  const append = (chunk: Buffer) => {
    if (proc.output.length < MAX_BUFFERED_OUTPUT) {
      proc.output += chunk.toString();
    }
  };
  child.stdout?.on("data", append);
  child.stderr?.on("data", append);

  const settled = await new Promise<"ready" | "exited" | "timeout">((resolve) => {
    let done = false;
    const finish = (why: "ready" | "exited" | "timeout") => {
      if (done) return;
      done = true;
      clearInterval(poll);
      clearTimeout(timer);
      resolve(why);
    };

    child.once("exit", (code) => {
      proc.exited = true;
      proc.exitCode = code;
      noteUnexpectedExit(proc);
      finish("exited");
    });
    child.once("error", () => {
      proc.exited = true;
      finish("exited");
    });

    // Poll rather than checking on every chunk: a ready line often arrives
    // split across several writes.
    const poll = setInterval(() => {
      if (looksReady(proc.output)) finish("ready");
    }, 100);
    const timer = setTimeout(() => finish("timeout"), readyTimeoutMs);
  });

  const seen = proc.output.trim();
  const tail = seen.length > 2000 ? `…\n${seen.slice(-2000)}` : seen;

  if (settled === "exited") {
    // Deliberately kept in the map: the reason it died is in its output,
    // and dropping the record makes that unreadable a moment later.
    const code = proc.exitCode;
    // Exiting immediately is a failure for something asked to keep running,
    // even with status 0 — nothing is left to connect to.
    return {
      content:
        // The pid is reported even though it has exited. The record is kept so
        // read_process_output can explain why, and without the pid here there
        // is no way to ask for it.
        `Process (pid ${proc.pid}) exited immediately with code ${code ?? "unknown"} — it is NOT running.\n` +
        (tail ? `\n${tail}` : "(no output)"),
      isError: true,
    };
  }

  // From here it is reported as running, so a later death is news.
  proc.announced = true;

  const url = detectUrl(proc.output);
  const lines = [
    `Started in the background and still running (pid ${proc.pid}).`,
    url ? `Address: ${url}` : null,
    settled === "timeout"
      ? `No startup message within ${Math.round(readyTimeoutMs / 1000)}s; it is still running, so it may just be slow to announce itself.`
      : null,
    "",
    tail || "(no output yet)",
    "",
    // The model has to be told not to wait for this: it will not finish.
    "This process keeps running and will not produce a final result. Do not " +
      "re-run it or wait for it to complete. It stops when the session ends.",
  ].filter((l) => l !== null);

  return { content: lines.join("\n"), isError: false };
}
