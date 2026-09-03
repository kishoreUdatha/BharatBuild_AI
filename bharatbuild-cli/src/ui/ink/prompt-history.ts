/**
 * Prompt history — what the up arrow recalls.
 *
 * The readline UI declared a `history` array and a `historyIndex`, but nothing
 * ever read them: no key was bound, and the index was reset to -1 on every
 * prompt. So the reflex every REPL user has — press up, get the last thing you
 * typed — did nothing at all, and a long prompt had to be retyped in full.
 *
 * Navigation is kept separate from storage here. The cursor is pure, so its
 * behaviour at the ends of the list can be tested without touching disk, and
 * the disk half can fail (read-only home, corrupt file) without the arrow keys
 * breaking.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";

/** Entries kept per project. Beyond this the oldest are dropped. */
const MAX_ENTRIES = 500;

/* ------------------------------------------------------------------ *
 * Navigation
 * ------------------------------------------------------------------ */

export interface HistoryCursor {
  /** Oldest first, so the newest entry is the one the first press recalls. */
  entries: string[];
  /**
   * Position in `entries`, or -1 when not navigating. -1 is not "before the
   * first entry": it means the box is showing the user's own draft.
   */
  index: number;
  /** What was typed before navigating started, restored on the way back down. */
  draft: string;
}

export function newCursor(entries: string[]): HistoryCursor {
  return { entries, index: -1, draft: "" };
}

export interface Move {
  /** What the input box should now show. */
  value: string;
  cursor: HistoryCursor;
  /** False when the press should fall through to whatever else wants it. */
  handled: boolean;
}

/** Older. The first press stashes the draft so it can be recovered. */
export function historyUp(cursor: HistoryCursor, current: string): Move {
  if (cursor.entries.length === 0) return { value: current, cursor, handled: false };

  // Already at the oldest: stay put rather than wrapping. Wrapping would drop
  // the user at the newest entry, which reads as the list having been lost.
  if (cursor.index === 0) return { value: cursor.entries[0]!, cursor, handled: true };

  const draft = cursor.index === -1 ? current : cursor.draft;
  const index = cursor.index === -1 ? cursor.entries.length - 1 : cursor.index - 1;
  return { value: cursor.entries[index]!, cursor: { ...cursor, index, draft }, handled: true };
}

/** Newer, and past the newest entry back to the draft. */
export function historyDown(cursor: HistoryCursor, current: string): Move {
  if (cursor.index === -1) return { value: current, cursor, handled: false };

  const index = cursor.index + 1;
  if (index >= cursor.entries.length) {
    // Back to what the user was typing before they started looking.
    return { value: cursor.draft, cursor: { ...cursor, index: -1, draft: "" }, handled: true };
  }
  return { value: cursor.entries[index]!, cursor: { ...cursor, index }, handled: true };
}

/**
 * Add an entry and return the new list.
 *
 * Blank input and an immediate repeat are dropped: holding enter on the same
 * command should not push everything else out of reach.
 */
export function pushEntry(entries: string[], entry: string): string[] {
  const trimmed = entry.trim();
  if (!trimmed) return entries;
  if (entries[entries.length - 1] === trimmed) return entries;
  const next = [...entries, trimmed];
  return next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next;
}

/* ------------------------------------------------------------------ *
 * Storage
 * ------------------------------------------------------------------ */

function homeDir(): string {
  return process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild");
}

/**
 * One file per project.
 *
 * History is only useful next to the code it was typed against — recalling a
 * different repo's commands is noise. The directory is hashed rather than
 * spelled out because a path is not a legal filename on any platform.
 */
export function historyFile(cwd: string = process.cwd()): string {
  const key = createHash("sha1").update(path.resolve(cwd)).digest("hex").slice(0, 16);
  return path.join(homeDir(), "history", `${key}.json`);
}

/** Everything typed in this project before, oldest first. */
export function loadHistory(cwd: string = process.cwd()): string[] {
  try {
    const raw = fs.readFileSync(historyFile(cwd), "utf8");
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((e): e is string => typeof e === "string" && e.trim() !== "");
  } catch {
    // Missing, unreadable or corrupt — an empty history is a working input box,
    // which is the point. Never let this break typing.
    return [];
  }
}

/** Persist, ignoring any failure. */
export function saveHistory(entries: string[], cwd: string = process.cwd()): void {
  try {
    const file = historyFile(cwd);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(entries), "utf8");
  } catch {
    /* read-only home, full disk — not worth interrupting the session for */
  }
}

/* ------------------------------------------------------------------ *
 * Reverse search
 * ------------------------------------------------------------------ */

/**
 * Incremental search back through history, as ctrl+r does in a shell.
 *
 * Arrow-key history only walks one step at a time, which is fine for the last
 * thing you typed and useless for something forty prompts ago. Search is how
 * anyone actually finds an earlier command, and the history is already stored
 * per project — it just had no way in.
 */
export interface SearchState {
  /** What has been typed into the search so far. */
  query: string;
  /** Index into `entries` of the current match, or -1 for none. */
  match: number;
  /** The input's contents before searching began, restored on cancel. */
  draft: string;
}

export function beginSearch(draft: string): SearchState {
  return { query: "", match: -1, draft };
}

/**
 * Best match at or before `from`, newest first.
 *
 * Case-insensitive substring: the point is to find a half-remembered command,
 * not to write a pattern.
 */
function findBackwards(entries: string[], query: string, from: number): number {
  if (!query) return -1;
  const q = query.toLowerCase();
  for (let i = Math.min(from, entries.length - 1); i >= 0; i--) {
    if (entries[i]!.toLowerCase().includes(q)) return i;
  }
  return -1;
}

/** Extend the query by one character and re-match from the newest entry. */
export function searchType(state: SearchState, entries: string[], ch: string): SearchState {
  const query = state.query + ch;
  return { ...state, query, match: findBackwards(entries, query, entries.length - 1) };
}

/** Remove the last character; an empty query matches nothing again. */
export function searchBackspace(state: SearchState, entries: string[]): SearchState {
  const query = state.query.slice(0, -1);
  return { ...state, query, match: findBackwards(entries, query, entries.length - 1) };
}

/** Step to the next older match, leaving the position alone when there is none. */
export function searchOlder(state: SearchState, entries: string[]): SearchState {
  if (state.match <= 0) return state;
  const next = findBackwards(entries, state.query, state.match - 1);
  return next === -1 ? state : { ...state, match: next };
}

/** The text a search should put in the box: the match, or the original draft. */
export function searchValue(state: SearchState, entries: string[]): string {
  return state.match >= 0 ? entries[state.match]! : state.draft;
}

/** The prompt shown while searching, in the shape shells have used for decades. */
export function searchLabel(state: SearchState, entries: string[]): string {
  if (state.query && state.match === -1) return `(failed reverse-i-search)\`${state.query}'`;
  return `(reverse-i-search)\`${state.query}'`;
}
