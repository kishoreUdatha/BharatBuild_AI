/**
 * BharatBuild CLI — Shell Tool
 * execute_command with safety checks and timeout
 */

import { execFile } from "child_process";
import { promisify } from "util";
import { SHELL_TIMEOUT_MS, MAX_SHELL_OUTPUT } from "../../config/constants.js";
import { isDangerousInvocation } from "../../permissions/dangerous-command.js";
import { runInBackground } from "./background.js";
import { getShellConfiguration, withUtf8 } from "./shell-config.js";
import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

const execFileAsync = promisify(execFile);

export type { ToolDefinition, ToolResult };

export const executeCommandDefinition: ToolDefinition = {
  name: "execute_command",
  description:
    "Execute a shell command and return its output. " +
    "Use for running build commands, tests, scripts, package managers, etc. " +
    "Set background:true for anything that keeps running instead of finishing " +
    "— dev servers, watchers, `npm run dev`, `npm start`, `flask run`. Without " +
    "it the command is killed at the timeout and the server never stays up. " +
    "Dangerous operations (rm -rf, format, drop table, etc.) are blocked.",
  input_schema: {
    type: "object",
    properties: {
      command: { type: "string", description: "The shell command to execute" },
      working_dir: { type: "string", description: "Working directory (default: current)" },
      timeout_ms: { type: "number", description: `Timeout in ms (default: ${SHELL_TIMEOUT_MS})` },
      env: { type: "object", description: "Additional environment variables" },
      background: {
        type: "boolean",
        description:
          "Start the process and leave it running instead of waiting for it " +
          "to finish. Use for servers and watchers. Returns once it looks " +
          "ready, reporting the address it announced.",
      },
    },
    required: ["command"],
  },
};

/**
 * This matched DANGEROUS_COMMANDS as substrings, so `git add .` was refused
 * because "add" contains "dd", and `npm run format` because "format" contains
 * "rm". The shared checker looks at the program being invoked instead, and
 * carries the destructive-phrase patterns too — one list rather than three.
 */
function isDangerous(command: string): { blocked: boolean; reason?: string } {
  return isDangerousInvocation(command);
}

export interface ShellInput {
  command: string;
  working_dir?: string;
  timeout_ms?: number;
  background?: boolean;
  env?: Record<string, string>;
}

/**
 * Run a command the *model* chose to run.
 *
 * The blocklist is applied here and nowhere below, because that is what it is
 * for: gating a decision the model made on its own.
 */
export async function executeCommand(input: ShellInput, signal?: AbortSignal): Promise<ToolResult> {
  const safety = isDangerous(input.command);
  if (safety.blocked) {
    return {
      content: `Command blocked: ${safety.reason}\nCommand: ${input.command}`,
      isError: true,
    };
  }
  return runShell(input, signal);
}

/**
 * Run a command the *user* typed, via the `!` prefix.
 *
 * Deliberately not subject to the blocklist. Those patterns exist to stop the
 * model from deciding to force-push or wipe a directory; a command the user
 * typed character by character is already an explicit instruction, and
 * refusing it would make this prompt strictly less useful than the shell it is
 * standing in front of. Approval is skipped for the same reason — typing the
 * command *is* the approval, and prompting for it would ask the user to
 * confirm their own keystrokes.
 */
export async function runUserCommand(input: ShellInput, signal?: AbortSignal): Promise<ToolResult> {
  return runShell(input, signal);
}

async function runShell(input: ShellInput, signal?: AbortSignal): Promise<ToolResult> {
  const timeoutMs = Math.min(input.timeout_ms ?? SHELL_TIMEOUT_MS, 300_000);
  // One place decides the shell; see shell-config for why it is PowerShell
  // on Windows and bash elsewhere rather than cmd.exe and /bin/sh.
  const config = getShellConfiguration();
  const shell = config.executable;
  const shellArgs = config.argsPrefix;
  const command = withUtf8(input.command, config);
  const cwd = input.working_dir ?? process.cwd();

  // A server does not finish, so waiting for it is the wrong shape: it
  // blocked for the full timeout, got killed, and reported failure for an
  // app that had started correctly.
  if (input.background) {
    return runInBackground(command, cwd, shell, shellArgs);
  }
  const mergedEnv = { ...process.env, ...(input.env ?? {}) };
  try {
    const { stdout, stderr } = await execFileAsync(shell, [...shellArgs, command], {
      cwd,
      env: mergedEnv,
      timeout: timeoutMs,
      maxBuffer: MAX_SHELL_OUTPUT * 2,
      signal,
    });
    const out = (stdout || "").slice(0, MAX_SHELL_OUTPUT);
    const err = (stderr || "").slice(0, MAX_SHELL_OUTPUT);
    let result = "";
    if (out) result += `STDOUT:\n${out}`;
    if (err) result += `${result ? "\n\n" : ""}STDERR:\n${err}`;
    if (!result) result = "(command completed with no output)";
    return { content: result, isError: false };
  } catch (err: unknown) {
    const e = err as NodeJS.ErrnoException & { stdout?: string; stderr?: string; killed?: boolean };
    const anyErr = e as unknown as Record<string, unknown>;
    if (anyErr["code"] === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
      // More output than we agreed to hold. Report what arrived and say it
      // was cut off: returning only the error code threw away 586 lines of a
      // docker build that was working perfectly well.
      const out = (e.stdout || "").slice(0, MAX_SHELL_OUTPUT);
      const errOut = (e.stderr || "").slice(0, MAX_SHELL_OUTPUT);
      const parts = [
        "Command produced more output than can be captured, and was stopped.",
        "It may well have been succeeding. Re-run with background:true and poll",
        "read_process_output, or redirect to a file and read that.",
      ];
      if (out) parts.push("", "STDOUT (truncated):", out);
      if (errOut) parts.push("", "STDERR (truncated):", errOut);
      return { content: parts.join("\n"), isError: true };
    }
    if (e.killed || anyErr["code"] === "ETIMEDOUT") {
      return { content: `Command timed out after ${timeoutMs}ms`, isError: true };
    }
    if (signal?.aborted) return { content: "Command was cancelled.", isError: false };
    const out = (e.stdout || "").slice(0, MAX_SHELL_OUTPUT);
    const errOut = (e.stderr || "").slice(0, MAX_SHELL_OUTPUT);
    const exitCode = anyErr["code"] ?? "unknown";
    let result = `Exit code: ${exitCode}`;
    if (out) result += `\n\nSTDOUT:\n${out}`;
    if (errOut) result += `\n\nSTDERR:\n${errOut}`;
    return { content: result, isError: true };
  }
}
