/**
 * Undo for the files a turn touched.
 *
 * `esc esc` rewound the conversation and left the working tree exactly as the
 * agent had left it — so "go back to before I asked for that" put the words
 * back and none of the edits, which is the half that actually matters.
 *
 * CheckpointManager already existed but copies the whole tree, which is far
 * too heavy to run before every edit: on this repo that is 800-odd files each
 * time. What rewind actually needs is much smaller — the previous contents of
 * the files a turn is about to change. That is one read per edited file, and
 * it is exactly reversible.
 *
 * A file created during the turn is recorded as having not existed, so undoing
 * deletes it rather than leaving an empty husk behind.
 */

import fs from "node:fs";
import path from "node:path";

interface Snapshot {
  /** Absolute path of the file as it was about to be changed. */
  file: string;
  /** Contents before the change, or null when the file did not exist. */
  before: string | null;
}

/** Snapshots taken during one user turn, keyed by absolute path. */
interface TurnSnapshots {
  /** Index of the user message this turn belongs to. */
  turnIndex: number;
  files: Map<string, Snapshot>;
}

const turns: TurnSnapshots[] = [];

/** Begin recording for a new user turn. */
export function beginTurn(turnIndex: number): void {
  turns.push({ turnIndex, files: new Map() });
}

/**
 * Record a file's contents before it is modified.
 *
 * Only the first change in a turn is kept: rewinding goes back to how things
 * were when the turn started, so later edits to the same file are irrelevant.
 */
export function captureBefore(file: string): void {
  const turn = turns[turns.length - 1];
  if (!turn) return;                        // nothing running; nothing to undo
  const abs = path.resolve(file);
  if (turn.files.has(abs)) return;

  let before: string | null = null;
  try {
    before = fs.readFileSync(abs, "utf8");
  } catch {
    before = null;                          // did not exist — undo means delete
  }
  turn.files.set(abs, { file: abs, before });
}

/** How many files would be restored by rewinding to `turnIndex`. */
export function filesChangedSince(turnIndex: number): string[] {
  const seen = new Set<string>();
  for (const turn of turns) {
    if (turn.turnIndex < turnIndex) continue;
    for (const abs of turn.files.keys()) seen.add(abs);
  }
  return [...seen];
}

export interface RestoreResult {
  restored: string[];
  deleted: string[];
  failed: Array<{ file: string; reason: string }>;
}

/**
 * Put the files back as they were before `turnIndex`.
 *
 * Turns are replayed newest first so the oldest snapshot wins — that is the
 * state at the moment the rewind target began.
 */
export function restoreSince(turnIndex: number): RestoreResult {
  const result: RestoreResult = { restored: [], deleted: [], failed: [] };
  const applied = new Set<string>();

  for (let i = turns.length - 1; i >= 0; i--) {
    const turn = turns[i]!;
    if (turn.turnIndex < turnIndex) continue;

    for (const snap of turn.files.values()) {
      if (applied.has(snap.file)) continue;
      applied.add(snap.file);
      try {
        if (snap.before === null) {
          // Created during the turn: undoing means it should not exist.
          if (fs.existsSync(snap.file)) {
            fs.rmSync(snap.file);
            result.deleted.push(snap.file);
          }
        } else {
          fs.mkdirSync(path.dirname(snap.file), { recursive: true });
          fs.writeFileSync(snap.file, snap.before, "utf8");
          result.restored.push(snap.file);
        }
      } catch (err) {
        // Report rather than abort: restoring nine of ten files is better than
        // stopping at the first one that is locked or read-only.
        result.failed.push({
          file: snap.file,
          reason: err instanceof Error ? err.message : String(err),
        });
      }
    }
  }

  // Those turns are undone; their snapshots no longer describe anything.
  for (let i = turns.length - 1; i >= 0; i--) {
    if (turns[i]!.turnIndex >= turnIndex) turns.splice(i, 1);
  }
  return result;
}

/** Forget everything. For tests, and for a session that starts over. */
export function clearSnapshots(): void {
  turns.length = 0;
}

/** Turns recorded so far — used to number the next one. */
export function turnCount(): number {
  return turns.length;
}
