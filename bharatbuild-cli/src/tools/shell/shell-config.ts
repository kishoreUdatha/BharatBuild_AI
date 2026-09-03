/**
 * Which shell a command actually runs in.
 *
 * This used to be cmd.exe on Windows and /bin/sh elsewhere, decided inline in
 * two places. Both choices caused real failures:
 *
 *   - cmd.exe eats the inner quotes of a nested invocation, so
 *     `powershell -Command "Write-Output ok"` came back as the literal text.
 *     The agent could not tell that apart from a command that prints its own
 *     text, so it kept trying variations that all appeared to work and did
 *     nothing — including a 90-second sleep that never elapsed.
 *   - /bin/sh is not bash: no arrays, no [[ ]], no pipefail. Models write bash.
 *
 * gemini-cli reached the same conclusion and documents why (its issue #25859:
 * Windows PowerShell 5.1 strips embedded double quotes when calling native
 * executables, PowerShell 7 does not). So pwsh is preferred, powershell.exe is
 * the fallback, and Unix gets bash.
 */

import { existsSync } from "node:fs";
import path from "node:path";

export type ShellKind = "powershell" | "bash" | "sh";

export interface ShellConfiguration {
  /** Executable to spawn. */
  executable: string;
  /** Arguments that precede the command string. */
  argsPrefix: string[];
  kind: ShellKind;
}

/** First match for `name` on PATH, or null. */
export function resolveExecutable(name: string): string | null {
  const dirs = (process.env["PATH"] ?? "").split(path.delimiter).filter(Boolean);
  for (const dir of dirs) {
    const full = path.join(dir, name);
    try {
      if (existsSync(full)) return full;
    } catch {
      /* unreadable PATH entry */
    }
  }
  return null;
}

export function getShellConfiguration(
  platform: NodeJS.Platform = process.platform,
): ShellConfiguration {
  if (platform === "win32") {
    // -NoProfile so a user's profile cannot prepend output or change the
    // working directory out from under the command.
    const pwsh = resolveExecutable("pwsh.exe");
    if (pwsh) {
      return { executable: pwsh, argsPrefix: ["-NoProfile", "-Command"], kind: "powershell" };
    }
    // Windows PowerShell 5.1. Present on every Windows install, and still a
    // far better host than cmd.exe for the commands a model writes.
    return {
      executable: "powershell.exe",
      argsPrefix: ["-NoProfile", "-NonInteractive", "-Command"],
      kind: "powershell",
    };
  }

  const bash = resolveExecutable("bash");
  if (bash) return { executable: bash, argsPrefix: ["-c"], kind: "bash" };
  return { executable: "/bin/sh", argsPrefix: ["-c"], kind: "sh" };
}

/**
 * Make the shell speak UTF-8 before running anything.
 *
 * Windows consoles default to a legacy codepage (cp1252 here), so a program
 * printing anything outside it dies with UnicodeEncodeError. That happened:
 * a generated Python script crashed on its own ✓/✗ output, and the agent
 * "fixed" it by deleting those characters from the program — changing the
 * deliverable to suit a terminal setting, which is the wrong repair.
 */
export function withUtf8(command: string, config: ShellConfiguration): string {
  if (config.kind !== "powershell") return command;
  return `chcp 65001 > $null; ${command}`;
}

/** A human-readable name for the system prompt, so nothing has to guess. */
export function describeShell(config: ShellConfiguration): string {
  if (config.kind === "powershell") {
    return "PowerShell on Windows (use PowerShell syntax: Get-ChildItem, $env:VAR, ; to chain — not cmd.exe, and not bash)";
  }
  if (config.kind === "bash") return "bash";
  return "/bin/sh";
}
