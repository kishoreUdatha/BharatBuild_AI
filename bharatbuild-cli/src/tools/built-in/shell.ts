/**
 * BharatBuild CLI — Built-in Tool: shell
 * A tool for executing shell commands with safety checks.
 */

import { execFile } from "child_process";
import { promisify } from "util";
import type { BuiltInTool, ToolResult } from "./types.js";

const execFileAsync = promisify(execFile);

const SHELL_TIMEOUT_MS = 120_000;
const MAX_OUTPUT = 50_000;

const DANGEROUS_PATTERNS = [
  "rm -rf /", "rm -rf ~", "rm -rf .",
  "mkfs", "format", "dd if=",
  "> /dev/sda", "shred",
  ":(){ :|:& };:", // fork bomb
];

export const shellTool: BuiltInTool = {
  definition: {
    name: "shell",
    source: "built-in",
    status: "approval_required",
    description: "A tool for executing shell commands. Use only as a last-resort when no other available tool can accomplish the task.",
    parameters: {
      type: "object",
      properties: {
        command: { type: "string", description: "Command to execute." },
        working_dir: {
          type: "string",
          description: "Optional working directory for command execution. If not specified, uses the current working directory.",
        },
      },
      required: ["command"],
    },
  },

  async execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult> {
    const command = params["command"] as string;
    const workingDir = params["working_dir"] as string | undefined;

    if (!command?.trim()) {
      return { content: "Error: 'command' is required.", isError: true };
    }

    // Safety check
    const lower = command.toLowerCase().trim();
    for (const dangerous of DANGEROUS_PATTERNS) {
      if (lower.includes(dangerous.toLowerCase())) {
        return {
          content: `Command blocked: Contains dangerous pattern '${dangerous}'.\nCommand: ${command}`,
          isError: true,
        };
      }
    }

    const isWindows = process.platform === "win32";
    const shell = isWindows ? "cmd.exe" : "/bin/sh";
    const shellArgs = isWindows ? ["/c", command] : ["-c", command];
    const cwd = workingDir ?? process.cwd();

    try {
      const { stdout, stderr } = await execFileAsync(shell, shellArgs, {
        cwd,
        env: process.env,
        timeout: SHELL_TIMEOUT_MS,
        maxBuffer: MAX_OUTPUT * 2,
        signal,
      });

      const out = (stdout || "").slice(0, MAX_OUTPUT);
      const err = (stderr || "").slice(0, MAX_OUTPUT);
      let result = "";
      if (out) result += out;
      if (err) result += `${result ? "\n\n" : ""}STDERR:\n${err}`;
      if (!result) result = "(command completed with no output)";
      return { content: result, isError: false };
    } catch (err: unknown) {
      const e = err as NodeJS.ErrnoException & { stdout?: string; stderr?: string; killed?: boolean };
      if (e.killed || (e as unknown as Record<string, unknown>)["code"] === "ETIMEDOUT") {
        return { content: `Command timed out after ${SHELL_TIMEOUT_MS}ms.`, isError: true };
      }
      if (signal?.aborted) {
        return { content: "Command was cancelled.", isError: false };
      }
      const out = (e.stdout || "").slice(0, MAX_OUTPUT);
      const errOut = (e.stderr || "").slice(0, MAX_OUTPUT);
      const exitCode = (e as unknown as Record<string, unknown>)["code"] ?? "unknown";
      let result = `Exit code: ${exitCode}`;
      if (out) result += `\n\nSTDOUT:\n${out}`;
      if (errOut) result += `\n\nSTDERR:\n${errOut}`;
      return { content: result, isError: true };
    }
  },
};
