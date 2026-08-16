/**
 * BharatBuild CLI — Shell Tool
 * execute_command with safety checks and timeout
 */

import { execFile } from "child_process";
import { promisify } from "util";
import { DANGEROUS_COMMANDS, SHELL_TIMEOUT_MS, MAX_SHELL_OUTPUT } from "../../config/constants.js";
import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

const execFileAsync = promisify(execFile);

export type { ToolDefinition, ToolResult };

export const executeCommandDefinition: ToolDefinition = {
  name: "execute_command",
  description:
    "Execute a shell command and return its output. " +
    "Use for running build commands, tests, scripts, package managers, etc. " +
    "Dangerous operations (rm -rf, format, drop table, etc.) are blocked.",
  input_schema: {
    type: "object",
    properties: {
      command: { type: "string", description: "The shell command to execute" },
      working_dir: { type: "string", description: "Working directory (default: current)" },
      timeout_ms: { type: "number", description: `Timeout in ms (default: ${SHELL_TIMEOUT_MS})` },
      env: { type: "object", description: "Additional environment variables" },
    },
    required: ["command"],
  },
};

function isDangerous(command: string): { blocked: boolean; reason?: string } {
  const lower = command.toLowerCase().trim();
  for (const dangerous of DANGEROUS_COMMANDS) {
    if (lower.includes(dangerous.toLowerCase())) {
      return { blocked: true, reason: `Contains dangerous pattern: '${dangerous}'` };
    }
  }
  const extraPatterns: Array<{ pattern: RegExp; reason: string }> = [
    { pattern: /rm\s+-rf?\s+[/\\]/, reason: "rm -rf on root path" },
    { pattern: /mkfs/, reason: "filesystem format command" },
  ];
  for (const { pattern, reason } of extraPatterns) {
    if (pattern.test(lower)) return { blocked: true, reason };
  }
  return { blocked: false };
}

export async function executeCommand(
  input: {
    command: string;
    working_dir?: string;
    timeout_ms?: number;
    env?: Record<string, string>;
  },
  signal?: AbortSignal
): Promise<ToolResult> {
  const timeoutMs = Math.min(input.timeout_ms ?? SHELL_TIMEOUT_MS, 300_000);
  const safety = isDangerous(input.command);
  if (safety.blocked) {
    return {
      content: `Command blocked: ${safety.reason}\nCommand: ${input.command}`,
      isError: true,
    };
  }
  const isWindows = process.platform === "win32";
  const shell = isWindows ? "cmd.exe" : "/bin/sh";
  const shellArgs = isWindows ? ["/c", input.command] : ["-c", input.command];
  const cwd = input.working_dir ?? process.cwd();
  const mergedEnv = { ...process.env, ...(input.env ?? {}) };
  try {
    const { stdout, stderr } = await execFileAsync(shell, shellArgs, {
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
