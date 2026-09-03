/**
 * Bounding the live streaming region.
 *
 * The whole in-flight reply was rendered live, so the region grew with the
 * answer — a 25-line reply made a 25-line live region. Ink erases a frame by
 * moving the cursor up by that frame's height, so once the region approaches
 * the viewport the erase no longer reaches the top: the terminal scrolls, the
 * next erase lands short, and a stale copy of the reply is left on screen. A
 * real session ended with its closing message shown twice, the second copy
 * truncated with a border character embedded in it.
 *
 * App.tsx already carries a long comment about this hazard for the prompt.
 * The same reasoning was never applied to the message above it.
 *
 * Only the display is trimmed. The committed message keeps the full text — it
 * goes to <Static>, which prints once and never repaints, so its height costs
 * nothing.
 */

/**
 * Lines of in-flight reply kept on screen.
 *
 * This has to leave room for a running tool card inside LIVE_ROWS, or the
 * pane overflows and the prompt is pushed down again - which is the whole
 * thing the fixed height exists to prevent.
 */
export const LIVE_TAIL_LINES = 7;

/**
 * The tail of a streaming reply, for display only.
 *
 * Returns the last `maxLines` lines, with a marker when anything was dropped
 * so the reader knows they are looking at a window rather than the whole
 * answer. The full text arrives in the transcript a moment later.
 */
export function liveTail(content: string, maxLines: number = LIVE_TAIL_LINES): string {
  if (maxLines <= 0) return "";
  const lines = content.split("\n");
  if (lines.length <= maxLines) return content;

  const hidden = lines.length - maxLines;
  return [
    `… ${hidden} earlier line${hidden === 1 ? "" : "s"}`,
    ...lines.slice(-maxLines),
  ].join("\n");
}
