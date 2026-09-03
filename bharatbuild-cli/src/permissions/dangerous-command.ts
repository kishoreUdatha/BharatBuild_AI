/**
 * Commands that must not run unattended.
 *
 * The bar here is not "could this be bad" — a permission prompt on every `rm`
 * trains people to hit `y` without reading. It is "does this destroy work that
 * cannot be recovered". `rm -rf node_modules` is noise; `git reset --hard`
 * throws away everything uncommitted with no undo.
 *
 * The git entries were missing entirely, so an agent in auto mode could
 * discard the user's uncommitted work without asking.
 */
export const DANGEROUS_PATTERNS = [
  // Filesystem destruction at or near a root.
  /rm\s+-rf?\s+[/\\]/i,
  /rm\s+-rf?\s+~/i,
  /format\s+[a-z]:/i,
  /mkfs/i,
  /dd\s+if=/i,
  /:\(\)\s*\{\s*:\|:&\s*\}\s*;:/,          // fork bomb

  // Database destruction.
  /DROP\s+(TABLE|DATABASE)/i,
  /DELETE\s+FROM/i,
  /TRUNCATE\s+TABLE/i,

  // Git operations that discard committed or uncommitted work. `--force-with-lease`
  // is deliberately excluded: it refuses when it would overwrite someone else's
  // work, which is the safe form people are told to use.
  /git\s+push\s+.*--force(?!-with-lease)/i,
  /git\s+reset\s+--hard/i,
  /git\s+clean\s+-[a-z]*f/i,               // -f, -fd, -fdx: deletes untracked files
  /git\s+checkout\s+--\s+\./i,             // discards all working-tree changes
  /git\s+restore\s+(--\w+\s+)*\./i,
  /git\s+branch\s+-D\b/i,                  // force-delete an unmerged branch
];

export function isDangerousCommand(cmd: string): boolean {
  return DANGEROUS_PATTERNS.some((p) => p.test(cmd));
}

/**
 * Programs that are dangerous *to invoke*, matched as the command word rather
 * than as a substring.
 *
 * The shell tool used `command.toLowerCase().includes(word)` over this list,
 * which blocked 7 of 16 ordinary commands in a quick sample: "dd" matched
 * `git add .`, "rm" matched `npm run format`, "su" matched `echo result` and
 * `pytest tests/suite`, "del" matches `model`. A guard that stops `git add` is
 * not a guard — it gets switched off.
 */
const DANGEROUS_PROGRAMS = new Set([
  "rm", "rmdir", "del", "format", "mkfs", "dd", "shred", "truncate",
  "chmod", "chown", "sudo", "su",
  "curl", "wget", "nc", "netcat",
]);

/** Split a command line into the individual programs it invokes. */
function invokedPrograms(cmd: string): string[] {
  return cmd
    .split(/\|\||&&|[;|&]/)              // pipeline and sequencing separators
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      // Skip leading VAR=value assignments, then take the program itself.
      const tokens = segment.split(/\s+/).filter((t) => !/^\w+=/.test(t));
      const program = tokens[0] ?? "";
      // Compare on the basename: /bin/rm and rm are the same program.
      return program.split(/[/\\]/).pop()!.toLowerCase();
    });
}

/**
 * True when the command invokes a dangerous program or contains a destructive
 * phrase. This is the check the shell tools should use.
 */
export function isDangerousInvocation(cmd: string): { blocked: boolean; reason?: string } {
  for (const program of invokedPrograms(cmd)) {
    if (DANGEROUS_PROGRAMS.has(program)) {
      return { blocked: true, reason: `invokes '${program}'` };
    }
  }
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(cmd)) {
      return { blocked: true, reason: `matches ${pattern}` };
    }
  }
  return { blocked: false };
}
