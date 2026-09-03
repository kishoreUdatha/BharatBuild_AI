/**
 * Working-state vocabulary for the status line.
 *
 * A static "coding 47s" gives no sign of life on a long turn — the seconds
 * tick but nothing else moves, and it reads as a hang. A verb that changes
 * every few seconds shows the session is alive without pretending to know
 * more about progress than we do.
 *
 * Selection is derived from elapsed time rather than randomness so a given
 * turn renders identically on every repaint (and in tests).
 */

export const ACTIVITY_VERBS = [
  "Working", "Thinking", "Pondering", "Churning", "Digging", "Weaving",
  "Assembling", "Untangling", "Wrangling", "Puzzling", "Brewing", "Forging",
  "Threading", "Sifting", "Tinkering", "Composing",
] as const;

/** Seconds each verb stays on screen. */
const VERB_HOLD_SECONDS = 6;

export function activityVerb(elapsedSec: number, offset = 0): string {
  const index = Math.floor(Math.max(0, elapsedSec) / VERB_HOLD_SECONDS) + offset;
  return ACTIVITY_VERBS[index % ACTIVITY_VERBS.length]!;
}

/**
 * Hints shown under the status line while a turn runs. Only things the CLI
 * actually does — a tip for a feature that does not exist is worse than none.
 */
export const TIPS = [
  "Keep typing while this runs - your message is queued and sent when it finishes.",
  "Press esc to interrupt without losing what has already been done.",
  "ctrl+o expands truncated tool output.",
  "Type / to search commands; Tab completes the longest match.",
  "/plan switches to read-only mode so the agent proposes instead of edits.",
  "/rewind forks the conversation at an earlier turn.",
  "/context shows how much of the window is in use.",
  "/checkpoint init takes a restore point before a risky change.",
  "/usage breaks down tokens and cost for this session.",
  "/compact hides message headers when the screen gets busy.",
] as const;

/** Seconds each tip stays on screen. */
const TIP_HOLD_SECONDS = 12;

export function activityTip(elapsedSec: number, offset = 0): string {
  const index = Math.floor(Math.max(0, elapsedSec) / TIP_HOLD_SECONDS) + offset;
  return TIPS[index % TIPS.length]!;
}

/** `19.5k` / `1.2M` — the status line has no room for a raw integer. */
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

/** `8m 49s` once a turn passes a minute; plain seconds below that. */
export function formatElapsed(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}
