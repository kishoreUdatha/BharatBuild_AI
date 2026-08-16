/**
 * BharatBuild CLI - read-only (plan mode) tool policy
 *
 * One definition shared by the Plan agent and the TUI's Shift+Tab plan mode,
 * so the two cannot drift into disagreeing about what "read-only" means.
 */

export const READ_ONLY_BLOCKED = new Set([
  "write_file",
  "delete_file",
  "execute_command",
  "git_add",
  "git_commit",
  "subagent",
  "delegate",
]);

/**
 * MCP tools come from third-party servers, so their side effects are unknown
 * to us - an "mcp__jira__create_issue" is a write by any reasonable reading.
 * A blocklist cannot enumerate them, so plan mode excludes the namespace
 * wholesale rather than assuming they are safe.
 */
export function isBlockedInReadOnly(name: string): boolean {
  return READ_ONLY_BLOCKED.has(name) || name.startsWith("mcp__");
}
