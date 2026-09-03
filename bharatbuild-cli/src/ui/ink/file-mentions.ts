/**
 * `@file` mentions.
 *
 * Pointing the agent at a file meant typing its path into a sentence and
 * hoping the model chose to read it — which it often did not, answering from
 * the name alone. A mention is explicit: the file is attached to the message,
 * so the model has the contents before it decides anything.
 *
 * The parsing lives here rather than in the component because the awkward
 * cases are all textual — an email address is not a mention, a path with a
 * trailing comma should not swallow the comma — and none of them need a
 * terminal to test.
 */

import fs from "node:fs";
import path from "node:path";

/** Characters that can appear in a mentioned path. */
const PATH_CHARS = "A-Za-z0-9_\\-./\\\\~";

/** A mention being typed at the caret. */
export interface ActiveMention {
  /** What has been typed after the `@`. */
  query: string;
  /** Index of the `@` in the input. */
  start: number;
}

/**
 * The mention under the caret, if the user is in the middle of one.
 *
 * Only the trailing token counts: the box is single-line and the caret sits at
 * the end, so an `@` earlier in the sentence is one the user already finished.
 */
export function activeMention(value: string): ActiveMention | null {
  const m = value.match(new RegExp(`(^|\\s)@([${PATH_CHARS}]*)$`));
  if (!m) return null;
  const query = m[2] ?? "";
  return { query, start: value.length - query.length - 1 };
}

/** Replace the mention being typed with a chosen path. */
export function applyMention(value: string, mention: ActiveMention, filePath: string): string {
  // A trailing space so the next word does not run into the path, and so the
  // completed mention stops matching activeMention.
  return `${value.slice(0, mention.start)}@${filePath} `;
}

/**
 * Every mention in a submitted message.
 *
 * Requires a start-of-string or whitespace before the `@` so `user@example.com`
 * is left alone, and trims trailing punctuation so "see @src/app.ts, then…"
 * does not look for a file whose name ends in a comma.
 */
export function parseMentions(text: string): string[] {
  const out: string[] = [];
  const re = new RegExp(`(?:^|\\s)@([${PATH_CHARS}]+)`, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const raw = (m[1] ?? "").replace(/[.,;:!?)\]}]+$/, "");
    if (raw && !out.includes(raw)) out.push(raw);
  }
  return out;
}

/** Lines of a mentioned file to attach before it is cut short. */
const MAX_LINES = 2_000;
/** Bytes above which a file is not worth attaching whole. */
const MAX_BYTES = 256 * 1024;

export interface Attachment {
  path: string;
  content: string;
  /** Set when the file could not be attached, explaining why. */
  error?: string;
}

/** Read one mentioned path, reporting rather than throwing. */
export function readMention(mention: string, cwd: string = process.cwd()): Attachment {
  const resolved = path.resolve(cwd, mention);
  try {
    const stat = fs.statSync(resolved);
    if (stat.isDirectory()) {
      return { path: mention, content: "", error: "is a directory, not a file" };
    }
    if (stat.size > MAX_BYTES) {
      return { path: mention, content: "", error: `is too large to attach (${Math.round(stat.size / 1024)} KB)` };
    }
    const raw = fs.readFileSync(resolved, "utf8");
    const lines = raw.split("\n");
    if (lines.length > MAX_LINES) {
      return {
        path: mention,
        content: `${lines.slice(0, MAX_LINES).join("\n")}\n… ${lines.length - MAX_LINES} more lines not shown`,
      };
    }
    return { path: mention, content: raw };
  } catch {
    // Not an error worth blocking the message for — the user may well be
    // talking about a file that does not exist yet.
    return { path: mention, content: "", error: "could not be read" };
  }
}

/**
 * The message as the model should receive it.
 *
 * The user's own text is left exactly as typed, mentions and all — rewriting
 * it would make the transcript disagree with what was sent. The files follow
 * it in a clearly marked block.
 */
export function expandMentions(text: string, cwd: string = process.cwd()): string {
  const mentions = parseMentions(text);
  if (mentions.length === 0) return text;

  const blocks: string[] = [];
  for (const mention of mentions) {
    const att = readMention(mention, cwd);
    if (att.error) {
      blocks.push(`### ${att.path}\n(${att.error})`);
    } else {
      const ext = path.extname(att.path).replace(/^\./, "");
      blocks.push(`### ${att.path}\n\`\`\`${ext}\n${att.content}\n\`\`\``);
    }
  }

  return [
    text,
    "",
    "--- Files referenced above, attached in full ---",
    "",
    blocks.join("\n\n"),
  ].join("\n");
}
