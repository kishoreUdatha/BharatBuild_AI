/**
 * `<thinking>` blocks in a reply.
 *
 * Models emit their reasoning wrapped in these tags, and nothing handled them,
 * so a single answer printed 190 lines of internal monologue into the
 * transcript — XML tags and all — and buried the actual conclusion below it.
 *
 * Reasoning is worth keeping: it is how you tell a considered answer from a
 * guess, and this session found a wrong answer precisely by reading it. But it
 * is not the reply, so it is set apart and folded down rather than shown at
 * full length.
 */

export type ReplySegment =
  | { kind: "thinking"; content: string }
  | { kind: "text"; content: string };

/** Matches a whole block, or an unclosed one running to the end of the text. */
const THINKING = /<thinking>([\s\S]*?)(?:<\/thinking>|$)/gi;

/**
 * Split a reply into reasoning and answer.
 *
 * The closing tag is optional on purpose. While a reply streams in, the
 * opening tag arrives long before the closing one — requiring both would show
 * the raw `<thinking>` tag and the monologue as ordinary prose until the block
 * finished, then snap it into place.
 */
export function parseThinking(text: string): ReplySegment[] {
  const out: ReplySegment[] = [];
  let last = 0;
  let m: RegExpExecArray | null;

  THINKING.lastIndex = 0;
  while ((m = THINKING.exec(text)) !== null) {
    if (m.index > last) {
      const before = text.slice(last, m.index);
      if (before.trim()) out.push({ kind: "text", content: before.trim() });
    }
    const body = (m[1] ?? "").trim();
    if (body) out.push({ kind: "thinking", content: body });
    last = m.index + m[0].length;
    // An unclosed tag matches to end-of-text; without this a zero-width match
    // at the end would spin here forever.
    if (m[0].length === 0) break;
  }

  const rest = text.slice(last);
  if (rest.trim()) out.push({ kind: "text", content: rest.trim() });

  // No tags at all: hand back the original, untrimmed, so ordinary replies are
  // untouched by having passed through here.
  if (out.length === 0) return text ? [{ kind: "text", content: text }] : [];
  return out;
}

/** True when the reply contains reasoning worth setting apart. */
export function hasThinking(text: string): boolean {
  return /<thinking>/i.test(text);
}
