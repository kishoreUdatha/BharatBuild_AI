/**
 * Rewinding to an earlier turn.
 *
 * `/rewind` could already fork the conversation, but you had to remember the
 * command, run it once to see the numbered list, then run it again with the
 * number. Esc-esc opens the same list directly, which is the only reason this
 * logic is out here: the command and the picker must agree about what a turn
 * is and where the cut falls, and two copies would not stay in agreement.
 */

export interface Message {
  role: string;
  content: unknown;
}

export interface Turn {
  /** Position in the message list — where the cut is made. */
  index: number;
  /** Single-line summary for the list. */
  preview: string;
  /** The full text, so it can be put back in the input box for editing. */
  content: string;
}

/** Text of a message, whether it is a plain string or content blocks. */
function textOf(message: Message): string {
  if (typeof message.content === "string") return message.content;
  if (Array.isArray(message.content)) {
    return message.content
      .map((b) => (b && typeof b === "object" && "text" in b ? String((b as { text?: string }).text ?? "") : ""))
      .join("");
  }
  return "";
}

/**
 * The user's own turns, oldest first.
 *
 * Only user messages: a rewind point is somewhere the conversation could have
 * gone differently, and that is always something the user said.
 */
export function userTurns(messages: Message[], previewChars = 60): Turn[] {
  const turns: Turn[] = [];
  messages.forEach((m, index) => {
    if (m.role !== "user") return;
    const content = textOf(m);
    // A `!command` result and an `@file` attachment are both recorded as user
    // turns but are not things the user asked; offering them as rewind points
    // would fill the list with noise.
    if (content.startsWith("I ran this command myself:")) return;
    const firstLine = content.split("\n--- Files referenced above")[0] ?? content;
    const preview = firstLine.replace(/\s+/g, " ").trim();
    if (!preview) return;
    turns.push({
      index,
      content: firstLine.trim(),
      preview: preview.length > previewChars ? `${preview.slice(0, previewChars - 1)}…` : preview,
    });
  });
  return turns;
}

/** Everything before the chosen turn — the turn itself is being replaced. */
export function keepBefore(messages: Message[], turn: Turn): Message[] {
  return messages.slice(0, turn.index);
}
