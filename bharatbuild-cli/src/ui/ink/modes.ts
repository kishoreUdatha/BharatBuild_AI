/**
 * Permission modes, cycled with shift+tab.
 *
 * Three problems this replaces:
 *
 *  1. The mode was fixed at "ask", so every write and every shell command
 *     stopped the agent and waited for a keypress. A task that touches ten
 *     files needed ten answers, which is not an autonomous agent.
 *
 *  2. shift+tab was bound to plan mode while the status line advertised
 *     "shift+tab modes" — so reaching for auto-accept produced the exact
 *     opposite, a read-only agent that refused to edit anything.
 *
 *  3. Plan mode was cosmetic in this UI. It coloured a badge and changed
 *     nothing about what the agent was allowed to do.
 */

import { setDenyReason } from "../../permissions/deny-reason.js";
// One definition of "mutating", shared with checkPermission - a second copy
// here drifted out of sync the moment either list changed.
import { isMutating, planDenialReason } from "../../permissions/plan-mode.js";

export { isMutating };

export type PermissionMode = "ask" | "auto" | "plan";

/**
 * Map whatever the config file or env says onto the three modes here.
 * `acceptEdits` is the name Claude Code uses and people type it expecting it
 * to work; treat it as auto rather than silently falling back to ask.
 */
export function normalizeMode(value: unknown): PermissionMode | null {
  const v = String(value ?? "").toLowerCase().trim();
  if (v === "auto" || v === "acceptedits" || v === "accept-edits") return "auto";
  if (v === "plan") return "plan";
  if (v === "ask" || v === "default") return "ask";
  return null;
}

export const MODE_ORDER: readonly PermissionMode[] = ["ask", "auto", "plan"];

export function nextMode(current: PermissionMode): PermissionMode {
  const i = MODE_ORDER.indexOf(current);
  return MODE_ORDER[(i + 1) % MODE_ORDER.length]!;
}

export const MODE_LABEL: Record<PermissionMode, string> = {
  ask: "ask each time",
  auto: "auto-accept edits",
  plan: "plan (read-only)",
};


/**
 * What the UI should do with an approval request, before any prompt is shown.
 * `null` means "ask the user".
 */
export function decideForMode(
  mode: PermissionMode,
  toolName: string,
): "allow" | "deny" | null {
  if (mode === "auto") return "allow";
  if (mode === "plan") {
    if (!isMutating(toolName)) return "allow";
    setDenyReason(planDenialReason(toolName));
    return "deny";
  }
  return null;
}
