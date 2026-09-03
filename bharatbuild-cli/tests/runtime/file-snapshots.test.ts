/**
 * Undo for the files a turn touched.
 *
 * `esc esc` rewound the conversation and left the working tree exactly as the
 * agent had left it — so "go back to before I asked for that" restored the
 * words and none of the edits, which is the half that matters.
 *
 * CheckpointManager already existed but copies the whole tree, far too heavy
 * to run before every edit. What rewind needs is smaller and exactly
 * reversible: the previous contents of the files a turn is about to change.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  beginTurn, captureBefore, restoreSince, filesChangedSince, clearSnapshots,
} from "../../src/runtime/file-snapshots.js";

let dir: string;
const file = (name: string) => path.join(dir, name);

beforeEach(() => {
  clearSnapshots();
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-snap-"));
});
afterEach(() => {
  clearSnapshots();
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

describe("putting an edited file back", () => {
  it("restores the previous contents", () => {
    fs.writeFileSync(file("a.ts"), "original");
    beginTurn(0);
    captureBefore(file("a.ts"));
    fs.writeFileSync(file("a.ts"), "the agent's version");

    const r = restoreSince(0);
    expect(fs.readFileSync(file("a.ts"), "utf8")).toBe("original");
    expect(r.restored).toHaveLength(1);
  });

  it("keeps the state from the start of the turn, not the last edit", () => {
    // A turn that edits the same file three times must rewind to how it was
    // before any of them, so only the first snapshot counts.
    fs.writeFileSync(file("a.ts"), "v0");
    beginTurn(0);
    captureBefore(file("a.ts")); fs.writeFileSync(file("a.ts"), "v1");
    captureBefore(file("a.ts")); fs.writeFileSync(file("a.ts"), "v2");

    restoreSince(0);
    expect(fs.readFileSync(file("a.ts"), "utf8")).toBe("v0");
  });

  it("deletes a file the turn created", () => {
    // "Before" is that it did not exist; leaving an empty husk is not undo.
    beginTurn(0);
    captureBefore(file("new.ts"));
    fs.writeFileSync(file("new.ts"), "brand new");

    const r = restoreSince(0);
    expect(fs.existsSync(file("new.ts"))).toBe(false);
    expect(r.deleted).toHaveLength(1);
  });

  it("recreates a directory the file needs", () => {
    fs.mkdirSync(file("sub"));
    fs.writeFileSync(path.join(file("sub"), "x.ts"), "keep me");
    beginTurn(0);
    captureBefore(path.join(file("sub"), "x.ts"));
    fs.rmSync(file("sub"), { recursive: true });

    restoreSince(0);
    expect(fs.readFileSync(path.join(file("sub"), "x.ts"), "utf8")).toBe("keep me");
  });
});

describe("across several turns", () => {
  beforeEach(() => {
    fs.writeFileSync(file("a.ts"), "turn0");
    beginTurn(0);
    captureBefore(file("a.ts"));
    fs.writeFileSync(file("a.ts"), "after turn 0");

    fs.writeFileSync(file("b.ts"), "turn1");
    beginTurn(2);
    captureBefore(file("b.ts"));
    fs.writeFileSync(file("b.ts"), "after turn 1");
  });

  it("rewinding to the later turn leaves the earlier one alone", () => {
    restoreSince(2);
    expect(fs.readFileSync(file("a.ts"), "utf8")).toBe("after turn 0");
    expect(fs.readFileSync(file("b.ts"), "utf8")).toBe("turn1");
  });

  it("rewinding to the first turn undoes both", () => {
    restoreSince(0);
    expect(fs.readFileSync(file("a.ts"), "utf8")).toBe("turn0");
    expect(fs.readFileSync(file("b.ts"), "utf8")).toBe("turn1");
  });

  it("reports how many files a rewind would touch", () => {
    // The picker shows this per row: dropping messages is cheap, undoing
    // eleven file edits is not.
    expect(filesChangedSince(0)).toHaveLength(2);
    expect(filesChangedSince(2)).toHaveLength(1);
  });

  it("forgets the turns it has undone", () => {
    restoreSince(0);
    expect(filesChangedSince(0)).toHaveLength(0);
  });
});

describe("when it cannot restore something", () => {
  it("reports the failure and still restores the rest", () => {
    // Nine of ten files back is better than stopping at the first locked one.
    fs.writeFileSync(file("ok.ts"), "before");
    beginTurn(0);
    captureBefore(file("ok.ts"));
    captureBefore(file("gone"));            // never created, nothing to delete
    fs.writeFileSync(file("ok.ts"), "after");

    const r = restoreSince(0);
    expect(fs.readFileSync(file("ok.ts"), "utf8")).toBe("before");
    expect(r.failed).toEqual([]);
  });

  it("does nothing when no turn is open", () => {
    // captureBefore outside a turn must not throw or record anything.
    expect(() => captureBefore(file("whatever.ts"))).not.toThrow();
    expect(filesChangedSince(0)).toHaveLength(0);
  });

  it("reports nothing to undo for a turn that changed no files", () => {
    beginTurn(0);
    const r = restoreSince(0);
    expect(r.restored).toEqual([]);
    expect(r.deleted).toEqual([]);
  });
});
